import asyncio
import sys
import time
from contextlib import asynccontextmanager, suppress
from os.path import abspath, dirname
from typing import Any, AsyncGenerator

import grpc
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from google.protobuf.json_format import MessageToDict
from grpc import aio
from loguru import logger

from services.user.config import GATEWAY_PORT, GATEWAY_SERVICE_NAME, GRPC_SERVICE_COUNT, GRPC_SERVICE_NAME
from services.user.protocols import user_pb2, user_pb2_grpc
from services.user.schemas import Login, RefreshToken
from services.user.utils.consul import ConsulRegistry, local_address
from services.user.utils.token_handler import TokenExpiredException, TokenHandler

base_dir = dirname(dirname(dirname(abspath(__file__))))
ready_timeout = 60
invoke_timeout = 10
refresh_interval = 30
address = local_address()
registry = ConsulRegistry()
bearer = HTTPBearer(auto_error=False)
token_handler = TokenHandler()
http_statuses = {
    grpc.StatusCode.INVALID_ARGUMENT: status.HTTP_422_UNPROCESSABLE_CONTENT,
    grpc.StatusCode.NOT_FOUND: status.HTTP_404_NOT_FOUND,
    grpc.StatusCode.UNAUTHENTICATED: status.HTTP_401_UNAUTHORIZED,
    grpc.StatusCode.PERMISSION_DENIED: status.HTTP_403_FORBIDDEN,
    grpc.StatusCode.RESOURCE_EXHAUSTED: status.HTTP_429_TOO_MANY_REQUESTS,
    grpc.StatusCode.UNAVAILABLE: status.HTTP_503_SERVICE_UNAVAILABLE,
    grpc.StatusCode.DEADLINE_EXCEEDED: status.HTTP_504_GATEWAY_TIMEOUT
}


async def authorize(auth: HTTPAuthorizationCredentials | None = Depends(bearer)) -> int:
    if not auth or not auth.credentials:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "请先登录")
    try:
        return token_handler.decode_access_token(auth.credentials)
    except TokenExpiredException as error:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(error))
    except ValueError as error:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(error))


in_flight_weight = 2.0
latency_weight = 1.0
count_weight = 1.0
latency_alpha = 0.3


class Backend:
    def __init__(self, channel: aio.Channel, host: str, port: int) -> None:
        self.channel = channel
        self.host = host
        self.port = port
        self.stub = user_pb2_grpc.UserServiceStub(channel)
        self.count = 0
        self.in_flight = 0
        self.latency = 0.0

    @property
    def endpoint(self) -> tuple[str, int]:
        return self.host, self.port


def weigh(backends: list[Backend]) -> int:
    """在途请求、平均耗时、累计请求数归一化后加权，取分数最低的后端"""
    in_flight_max = max(backend.in_flight for backend in backends) or 1
    latency_max = max(backend.latency for backend in backends) or 1.0
    count_max = max(backend.count for backend in backends) or 1
    scores = [
        backend.in_flight / in_flight_max * in_flight_weight +
        backend.latency / latency_max * latency_weight +
        backend.count / count_max * count_weight
        for backend in backends
    ]
    return scores.index(min(scores))


class UserServicePool:
    def __init__(self) -> None:
        self.backends: list[Backend] = []
        self.lock = asyncio.Lock()

    @property
    def endpoints(self) -> list[tuple[str, int]]:
        return sorted(backend.endpoint for backend in self.backends)

    async def update(self, endpoints: list[tuple[str, int]]) -> None:
        known = {backend.endpoint: backend for backend in self.backends}
        backends = []
        for host, port in endpoints:
            backend = known.pop((host, port), None)
            if backend:
                backends.append(backend)
                continue
            channel = aio.insecure_channel(f"{host}:{port}")
            try:
                await asyncio.wait_for(channel.channel_ready(), timeout=ready_timeout)
            except Exception as error:
                await channel.close()
                logger.warning(f"gRPC service {host}:{port} is unreachable: {error}")
                continue
            backends.append(Backend(channel, host, port))

        if not backends:
            logger.warning(f"no available gRPC service in {endpoints}")
            return None

        async with self.lock:
            self.backends = backends
        for backend in known.values():
            await backend.channel.close()
        logger.info(f"gateway connected to gRPC services: {self.endpoints}")
        return None

    async def refresh(self) -> None:
        endpoints = await registry.resolve(GRPC_SERVICE_NAME)
        if not endpoints or endpoints == self.endpoints:
            return None
        await self.update(endpoints)
        return None

    async def close(self) -> None:
        for backend in self.backends:
            await backend.channel.close()
        self.backends.clear()

    async def acquire(self) -> Backend:
        async with self.lock:
            backend = self.backends[weigh(self.backends)]
            backend.in_flight += 1
            backend.count += 1
            logger.debug(
                f"dispatch request to {backend.endpoint}, in_flight={backend.in_flight}, "
                f"latency={backend.latency:.2f}ms, count={backend.count}"
            )
            return backend

    async def release(self, backend: Backend, latency: float) -> None:
        async with self.lock:
            backend.in_flight -= 1
            backend.latency = backend.latency * (1 - latency_alpha) + latency * latency_alpha
        return None


pool = UserServicePool()


async def register(name: str, port: int) -> str | None:
    try:
        return await registry.register(name, address, port)
    except Exception as error:
        logger.warning(f"failed to register {name} at {address}:{port}: {error}")
        return None


async def deregister(service_id: str | None) -> None:
    if not service_id:
        return None
    try:
        await registry.deregister(service_id)
    except Exception as error:
        logger.warning(f"failed to deregister {service_id}: {error}")
    return None


async def start_services() -> list[asyncio.subprocess.Process]:
    processes = []
    for _ in range(GRPC_SERVICE_COUNT):
        process = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "services.user", "0",
            cwd=base_dir
        )
        processes.append(process)
        logger.info(f"gRPC service started with dynamic port, pid={process.pid}")
    return processes


async def stop_services(processes: list[asyncio.subprocess.Process]) -> None:
    for process in processes:
        if process.returncode is None:
            process.terminate()
    await asyncio.gather(*(process.wait() for process in processes))
    logger.info(f"{len(processes)} gRPC services stopped")


async def wait_services() -> list[tuple[str, int]]:
    endpoints = []
    for _ in range(ready_timeout):
        try:
            endpoints = await registry.resolve(GRPC_SERVICE_NAME)
        except Exception as error:
            logger.warning(f"failed to resolve {GRPC_SERVICE_NAME}: {error}")
        if len(endpoints) >= GRPC_SERVICE_COUNT:
            return endpoints
        await asyncio.sleep(1)
    if endpoints:
        logger.warning(f"only {len(endpoints)} of {GRPC_SERVICE_COUNT} {GRPC_SERVICE_NAME} instances are healthy")
    else:
        logger.warning(f"no available {GRPC_SERVICE_NAME} found in {ready_timeout}s")
    return endpoints


async def refresh_loop() -> None:
    while True:
        await asyncio.sleep(refresh_interval)
        try:
            await pool.refresh()
        except Exception as error:
            logger.warning(f"failed to refresh gRPC services: {error}")


async def invoke(method_name: str, request: Any) -> Any:
    if not pool.backends:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "没有可用的 gRPC 服务")
    backend = await pool.acquire()
    method = getattr(backend.stub, method_name)
    started = time.perf_counter()
    try:
        return await method(request, timeout=invoke_timeout)
    except aio.AioRpcError as error:
        raise HTTPException(http_statuses.get(error.code(), status.HTTP_502_BAD_GATEWAY), error.details())
    finally:
        await pool.release(backend, (time.perf_counter() - started) * 1000)


@asynccontextmanager
async def lifespan(_application: FastAPI) -> AsyncGenerator[None, Any]:
    processes = await start_services()
    gateway_id = await register(GATEWAY_SERVICE_NAME, GATEWAY_PORT)
    await pool.update(await wait_services())
    task = asyncio.create_task(refresh_loop())
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
        await pool.close()
        await stop_services(processes)
        await deregister(gateway_id)


app = FastAPI(lifespan=lifespan, debug=True)


@app.post("/user/login")
async def login(account: Login) -> dict[str, Any]:
    request = user_pb2.LoginRequest(telephone=account.telephone)
    reply = await invoke("login", request)
    return MessageToDict(reply, preserving_proto_field_name=True)


@app.post("/user/access-token")
async def update_access_token(refresh_token: RefreshToken) -> dict[str, Any]:
    request = user_pb2.RefreshTokenRequest(refresh_token=refresh_token.value)
    reply = await invoke("update_access_token", request)
    return MessageToDict(reply, preserving_proto_field_name=True)


@app.get("/user/me")
async def get_current_user(user_id: int = Depends(authorize)) -> dict[str, Any]:
    reply = await invoke("get_user", user_pb2.GetUserRequest(user_id=user_id))
    return MessageToDict(reply, preserving_proto_field_name=True)


if __name__ == "__main__":
    uvicorn.run(app, port=GATEWAY_PORT)

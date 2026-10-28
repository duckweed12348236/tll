import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from grpc import aio
from loguru import logger
from tortoise import Tortoise

from services.user.config import GRPC_SERVICE_NAME, LOG_FILE, TORTOISE_ORM_CONFIG
from services.user.protocols import user_pb2_grpc
from services.user.service import UserService
from services.user.utils.cache import migrate
from services.user.utils.consul import ConsulRegistry, local_address

registry = ConsulRegistry()


@asynccontextmanager
async def register_plugins() -> AsyncGenerator[None, Any]:
    logger.add(LOG_FILE, rotation="500 MB", level="INFO", enqueue=True)
    await Tortoise.init(config=TORTOISE_ORM_CONFIG)
    await migrate()
    yield
    await Tortoise.close_connections()


async def register(address: str, port: int) -> str | None:
    try:
        return await registry.register(GRPC_SERVICE_NAME, address, port)
    except Exception as error:
        logger.warning(f"failed to register {GRPC_SERVICE_NAME} at {address}:{port}: {error}")
        return None


async def deregister(service_id: str | None) -> None:
    if not service_id:
        return None
    try:
        await registry.deregister(service_id)
    except Exception as error:
        logger.warning(f"failed to deregister {service_id}: {error}")
    return None


async def serve(port: int) -> None:
    async with register_plugins():
        address = local_address()
        server = aio.server()
        user_pb2_grpc.add_UserServiceServicer_to_server(UserService(), server)
        port = server.add_insecure_port(f"{address}:{port}")
        await server.start()
        logger.info(f"gRPC server is listening on {address}:{port}")
        service_id = await register(address, port)
        try:
            await server.wait_for_termination()
        except asyncio.CancelledError:
            logger.info("gRPC server is shutting down")
        finally:
            await server.stop(grace=0)
            await deregister(service_id)

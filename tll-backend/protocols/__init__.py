from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from grpc import aio
from loguru import logger
from tortoise import Tortoise

from config import GRPC_SERVICE_NAME, TORTOISE_ORM_CONFIG
from plugins import close_plugins, init_plugins
from plugins.consul import ConsulRegistry, local_address
from plugins.redis import migrate
from protocols import user_pb2_grpc
from services.user import UserService

registry = ConsulRegistry()


@asynccontextmanager
async def register_plugins() -> AsyncGenerator[None, Any]:
    logger.add("logs/log.log", rotation="500 MB", level="INFO", enqueue=True)
    await Tortoise.init(config=TORTOISE_ORM_CONFIG)
    await init_plugins()
    await migrate()
    yield
    await Tortoise.close_connections()
    await close_plugins()


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
        finally:
            await deregister(service_id)

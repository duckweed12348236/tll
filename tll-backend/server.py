import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from grpc import aio
from loguru import logger
from tortoise import Tortoise

from config import GRPC_PORT, TORTOISE_ORM_CONFIG
from plugins import close_plugins, init_plugins
from plugins.redis import migrate
from services.protocols import user_pb2_grpc
from services.user import UserService


@asynccontextmanager
async def register_plugins() -> AsyncGenerator[None, Any]:
    logger.add("logs/log.log", rotation="500 MB", level="INFO", enqueue=True)
    await Tortoise.init(config=TORTOISE_ORM_CONFIG)
    await init_plugins()
    await migrate()
    yield
    await Tortoise.close_connections()
    await close_plugins()


async def serve() -> None:
    async with register_plugins():
        server = aio.server()
        user_pb2_grpc.add_UserServiceServicer_to_server(UserService(), server)
        server.add_insecure_port(f"[::]:{GRPC_PORT}")
        await server.start()
        logger.info(f"gRPC server is listening on {GRPC_PORT}")
        await server.wait_for_termination()


if __name__ == "__main__":
    asyncio.run(serve())

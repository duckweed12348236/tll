import asyncio
import subprocess
import sys
from contextlib import asynccontextmanager
from os.path import abspath, dirname
from typing import AsyncGenerator, Any, Callable, Coroutine

import uvicorn
from fastapi import FastAPI, Depends, Request, Response
from starlette.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles
from loguru import logger
from tortoise import Tortoise

from config import TORTOISE_ORM_CONFIG, CORS_ALLOW_ORIGINS, CORS_ALLOW_CREDENTIALS, CORS_ALLOW_METHODS, \
    CORS_ALLOW_HEADERS, CORS_EXPOSE_HEADERS, STORAGE_DIR_NAME, GATEWAY_PORT
from dependencies import authenticate
from plugins import init_plugins, close_plugins
from plugins.celery import CeleryProcess
from plugins.kafka.consumer import KafkaConsumer
from plugins.redis import migrate
from controllers import auth, shopping, admin

base_dir = dirname(abspath(__file__))
kafka_consumer = KafkaConsumer()
celery_worker = CeleryProcess()
gateway_creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0


def spawn_gateway() -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, "-m", "services.user.gateway"],
        cwd=base_dir,
        creationflags=gateway_creation_flags
    )


def kill_process_tree(pid: int) -> None:
    subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True)
    return None


async def start_gateway() -> subprocess.Popen:
    process = await asyncio.to_thread(spawn_gateway)
    logger.info(f"gateway is starting on {GATEWAY_PORT}, pid={process.pid}")
    return process


async def stop_gateway(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return None
    if sys.platform == "win32":
        await asyncio.to_thread(kill_process_tree, process.pid)
    else:
        process.terminate()
    await asyncio.to_thread(process.wait)
    logger.info(f"gateway stopped, pid={process.pid}")
    return None


@asynccontextmanager
async def register_plugins(_application: FastAPI) -> AsyncGenerator[None, Any]:
    logger.add("logs/log.log", rotation="500 MB", level="INFO", enqueue=True)
    await Tortoise.init(config=TORTOISE_ORM_CONFIG)
    await init_plugins()
    await migrate()
    await kafka_consumer.start()
    await celery_worker.start()
    gateway = await start_gateway()
    yield
    await stop_gateway(gateway)
    await celery_worker.close()
    await kafka_consumer.close()
    await Tortoise.close_connections()
    await close_plugins()


app = FastAPI(lifespan=register_plugins, debug=True, dependencies=[Depends(authenticate)])

app.include_router(auth.router)
app.include_router(shopping.router)
app.include_router(admin.router)
app.mount(f"/{STORAGE_DIR_NAME}", StaticFiles(directory=STORAGE_DIR_NAME), name=STORAGE_DIR_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_credentials=CORS_ALLOW_CREDENTIALS,
    allow_methods=CORS_ALLOW_METHODS,
    allow_headers=CORS_ALLOW_HEADERS,
    expose_headers=CORS_EXPOSE_HEADERS
)


@app.middleware("http")
async def log(request: Request,
              call_next: Callable[[Request], Coroutine[None, None, Response]]) -> Response:
    response = await call_next(request)
    await logger.complete()
    return response


if __name__ == "__main__":
    uvicorn.run("app:app", reload=True)

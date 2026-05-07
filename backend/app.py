import multiprocessing
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Any

import uvicorn
from fastapi import FastAPI, Depends
from loguru import logger
from starlette.staticfiles import StaticFiles
from tortoise import Tortoise

from config import TORTOISE_ORM_CONFIG
from dependencies import authenticate
from plugins import PluginManager
from plugins.redis import migrate
import controllers.user, controllers.shopping, controllers.admin
import middlewares


@asynccontextmanager
async def register_plugins(app: FastAPI) -> AsyncGenerator[None, Any]:
    logger.add("logs/log.log", rotation="500 MB", level="INFO", enqueue=True)
    await Tortoise.init(config=TORTOISE_ORM_CONFIG)
    await PluginManager.init()
    await migrate()
    yield
    await Tortoise.close_connections()
    await PluginManager.close()


app = FastAPI(lifespan=register_plugins, debug=True, dependencies=[Depends(authenticate)])

app.include_router(controllers.user.router)
app.include_router(controllers.shopping.router)
app.include_router(controllers.admin.router)
app.mount("/storage", StaticFiles(directory="storage"), name="storage")


@app.get("/check")
async def check_health() -> str:
    return "ok"


@app.get("/test")
async def test() -> str:
    return "test"


if __name__ == "__main__":
    uvicorn.run(host="127.0.0.1",
                port=8000,
                reload=True,
                app="app:app",
                workers=multiprocessing.cpu_count())

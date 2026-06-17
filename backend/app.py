from contextlib import asynccontextmanager
from typing import AsyncGenerator, Any, Callable, Coroutine

import uvicorn
from fastapi import FastAPI, Depends, Request, Response
from starlette.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles
from loguru import logger
from tortoise import Tortoise

from config import TORTOISE_ORM_CONFIG, CORS_ALLOW_ORIGINS, CORS_ALLOW_CREDENTIALS, CORS_ALLOW_METHODS, \
    CORS_ALLOW_HEADERS, CORS_EXPOSE_HEADERS
from dependencies import authenticate
from plugins import init_plugins, close_plugins
from plugins.redis import migrate
from controllers import user, shopping, admin


@asynccontextmanager
async def register_plugins(app: FastAPI) -> AsyncGenerator[None, Any]:
    logger.add("logs/log.log", rotation="500 MB", level="INFO", enqueue=True)
    await Tortoise.init(config=TORTOISE_ORM_CONFIG)
    await init_plugins()
    await migrate()
    yield
    await Tortoise.close_connections()
    await close_plugins()


app = FastAPI(lifespan=register_plugins, debug=True, dependencies=[Depends(authenticate)])

app.include_router(user.router)
app.include_router(shopping.router)
app.include_router(admin.router)
app.mount("/storage", StaticFiles(directory="storage"), name="storage")

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

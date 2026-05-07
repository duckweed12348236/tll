from typing import Callable, Coroutine

from loguru import logger
from fastapi.requests import Request
from fastapi.responses import Response
from starlette.middleware.cors import CORSMiddleware

from app import app
from config import CORS_ALLOW_ORIGINS, CORS_ALLOW_CREDENTIALS, CORS_ALLOW_METHODS, CORS_ALLOW_HEADERS, CORS_EXPOSE_HEADERS, CORS_MAX_AGE

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_credentials=CORS_ALLOW_CREDENTIALS,
    allow_methods=CORS_ALLOW_METHODS,
    allow_headers=CORS_ALLOW_HEADERS,
    expose_headers=CORS_EXPOSE_HEADERS,
    max_age=CORS_MAX_AGE
)


@app.middleware("http")
async def log(request: Request,
              call_next: Callable[[Request], Coroutine[None, None, Response]]) -> Response:
    response = await call_next(request)
    await logger.complete()
    return response

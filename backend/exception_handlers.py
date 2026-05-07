from loguru import logger
from fastapi import status, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app import app


@app.exception_handler(RequestValidationError)
async def process_request_validation_error(request: Request, exc: RequestValidationError):
    logger.exception(str({
        "message": str(exc),
        "method": request.method,
        "user_id": request.state.user.id if hasattr(request.state, "user") else None
    }))
    return JSONResponse("校验失败", status.HTTP_422_UNPROCESSABLE_ENTITY)

@app.exception_handler(Exception)
async def process_exception(request: Request, exc: Exception):
    logger.exception(str({
        "message": str(exc),
        "method": request.method,
        "user_id": request.state.user.id if hasattr(request.state, "user") else None
    }))
    return JSONResponse("服务器内部错误", status.HTTP_500_INTERNAL_SERVER_ERROR)
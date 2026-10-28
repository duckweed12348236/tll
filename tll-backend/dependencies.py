from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from models.auth import Identity
from plugins.gateway import authenticate as authenticate_token

bearer = HTTPBearer(auto_error=False)


def get_token(auth: HTTPAuthorizationCredentials | None = Depends(bearer)) -> str:
    if not auth or not auth.credentials:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "请先登录")
    return auth.credentials


async def authenticate(request: Request,
                       auth: HTTPAuthorizationCredentials | None = Depends(bearer)) -> None:
    if request.url.path.startswith(
            ("/user/login",
             "/user/verification-code",
             "/user/access-token",
             "/admin",
             "/shopping/order/notify",
             "/check",
             "/docs",
             "/openapi.json",
             "/test")):
        return None

    value = await authenticate_token(get_token(auth))
    identity, _ = await Identity.get_or_create(user_id=value["id"])
    request.state.identity = identity
    return None


def get_identity(request: Request) -> Identity:
    return request.state.identity


def get_now() -> datetime:
    return datetime.now(ZoneInfo("Asia/Shanghai"))

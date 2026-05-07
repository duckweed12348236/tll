from datetime import datetime
from zoneinfo import ZoneInfo

from aredis_om import NotFoundError
from fastapi import Request, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from plugins.token_handler import TokenHandler, TokenExpiredException
from plugins.redis import UserCache
from models.user import User

bearer = HTTPBearer(auto_error=False)
token_handler = TokenHandler()


async def authenticate(request: Request,
                       auth: HTTPAuthorizationCredentials | None = Depends(bearer)) -> None:
    if request.url.path.startswith(
            ("/user/login",
             "/user/verification-code",
             "/user/access-token",
             "/admin",
             "/check",
             "/docs",
             "/openapi.json",
             "/test")):
        return None
    if not auth or not auth.credentials:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "请先登录")

    try:
        user_id = token_handler.decode_access_token(auth.credentials)
    except ValueError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, e)
    except TokenExpiredException as e:
        raise HTTPException(status.HTTP_403_FORBIDDEN, e)

    try:
        value = await UserCache.find(UserCache.id == user_id).values().first()
        user = User(**value)
    except NotFoundError:
        user = await User.filter(id=user_id).first()
        if not user:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "请先登录")
        value = user.serialize()
        await UserCache.save_user(**value)
    request.state.user = user
    return None


def get_user(request: Request) -> User:
    return request.state.user


def get_now() -> datetime:
    return datetime.now(ZoneInfo("Asia/Shanghai"))

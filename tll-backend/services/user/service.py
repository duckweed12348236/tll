from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import grpc
from google.protobuf import timestamp_pb2
from grpc import aio
from tortoise.transactions import in_transaction

from services.user.models import User
from services.user.protocols import user_pb2, user_pb2_grpc
from services.user.utils.cache import UserInfo
from services.user.utils.token_handler import TokenHandler

token_handler = TokenHandler()


def get_now() -> datetime:
    return datetime.now(ZoneInfo("Asia/Shanghai"))


def to_timestamp(value: datetime) -> timestamp_pb2.Timestamp:
    timestamp = timestamp_pb2.Timestamp()
    timestamp.FromDatetime(value if value.tzinfo else value.replace(tzinfo=UTC))
    return timestamp


def serialize_user(user: User) -> user_pb2.User:
    kwargs = dict(
        id=user.id,
        telephone=user.telephone,
        active=user.active
    )
    if user.last_login:
        kwargs.update(last_login=to_timestamp(user.last_login))
    return user_pb2.User(**kwargs)


class UserService(user_pb2_grpc.UserServiceServicer):
    async def login(self,
                    request: user_pb2.LoginRequest,
                    context: aio.ServicerContext) -> user_pb2.LoginReply:
        if not request.telephone:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "手机号不能为空")

        async with in_transaction():
            user, _ = await User.get_or_create(telephone=request.telephone)
            user.last_login = get_now()
            await user.save(update_fields=["last_login"])
        await UserInfo.save_user(**user.serialize())
        tokens = token_handler.make_tokens(user.id)
        return user_pb2.LoginReply(
            user=serialize_user(user),
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"]
        )

    async def update_access_token(self,
                                  request: user_pb2.RefreshTokenRequest,
                                  context: aio.ServicerContext) -> user_pb2.AccessTokenReply:
        try:
            user_id = token_handler.decode_refresh_token(request.refresh_token)
        except ValueError as error:
            await context.abort(grpc.StatusCode.UNAUTHENTICATED, str(error))
        return user_pb2.AccessTokenReply(access_token=token_handler.update_token(user_id))

    async def get_user(self,
                       request: user_pb2.GetUserRequest,
                       context: aio.ServicerContext) -> user_pb2.User:
        user = await User.filter(id=request.user_id).first()
        if not user:
            await context.abort(grpc.StatusCode.NOT_FOUND, "用户不存在")
        return serialize_user(user)

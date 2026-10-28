import os
import random
import string
import uuid
from datetime import UTC, datetime
from os.path import join
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

import aiofiles
import grpc
from aredis_om import NotFoundError
from google.protobuf import timestamp_pb2
from google.protobuf.empty_pb2 import Empty
from grpc import aio
from loguru import logger
from magic import magic
from tortoise.transactions import in_transaction

from config import SERVER_URL, STORAGE_DIR_NAME
from models.user import User
from plugins.aliyun_smscode import AliyunSmsCodeSender
from plugins.redis import Code, UserInfo
from plugins.token_handler import TokenHandler
from services.protocols import user_pb2, user_pb2_grpc

allowed_extensions = {'.jpg', '.jpeg', '.png', '.webp'}
allowed_mime_types = {
    'image/jpg',
    'image/jpeg',
    'image/png',
    'image/webp'
}
verification_code_sender = AliyunSmsCodeSender()
token_handler = TokenHandler()


def get_now() -> datetime:
    return datetime.now(ZoneInfo("Asia/Shanghai"))


def to_timestamp(value: datetime) -> timestamp_pb2.Timestamp:
    timestamp = timestamp_pb2.Timestamp()
    timestamp.FromDatetime(value if value.tzinfo else value.replace(tzinfo=UTC))
    return timestamp


def serialize_user(user: User) -> user_pb2.user:
    kwargs = dict(
        id=user.id,
        telephone=user.telephone,
        username=user.username,
        active=user.active
    )
    if user.avatar:
        kwargs.update(avatar=user.avatar)
    if user.last_login:
        kwargs.update(last_login=to_timestamp(user.last_login))
    if user.default_address_id:
        kwargs.update(default_address_id=user.default_address_id)
    return user_pb2.user(**kwargs)


class UserService(user_pb2_grpc.UserServiceServicer):
    async def get_verification_code(self,
                                    request: user_pb2.get_verification_code_request,
                                    context: aio.ServicerContext) -> Empty:
        if not request.telephone:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "手机号不能为空")
        value = "".join(random.sample(string.digits, 4))
        logger.info(f"verification code of {request.telephone}: {value}")
        # await verification_code_sender.send(request.telephone, value)
        await Code.create(telephone=request.telephone, value=value)
        return Empty()

    async def login(self,
                    request: user_pb2.login_request,
                    context: aio.ServicerContext) -> user_pb2.login_reply:
        try:
            code = await Code.find(Code.telephone == request.telephone).first()
            await Code.delete(code.pk)
        except NotFoundError:
            await context.abort(grpc.StatusCode.NOT_FOUND, "请先获取验证码")

        if request.code != code.value:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "验证码错误")

        async with in_transaction():
            user, _ = await User.get_or_create(telephone=request.telephone)
            user.last_login = get_now()
            await user.save(update_fields=["last_login"])
        kwargs = user.serialize()
        await UserInfo.save_user(**kwargs)
        tokens = token_handler.make_tokens(user.id)
        return user_pb2.login_reply(
            user=serialize_user(user),
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"]
        )

    async def update_access_token(self,
                                  request: user_pb2.refresh_token_request,
                                  context: aio.ServicerContext) -> user_pb2.access_token_reply:
        try:
            user_id = token_handler.decode_refresh_token(request.refresh_token)
        except ValueError as error:
            await context.abort(grpc.StatusCode.UNAUTHENTICATED, str(error))
        return user_pb2.access_token_reply(access_token=token_handler.update_token(user_id))

    async def get_user(self,
                       request: user_pb2.get_user_request,
                       context: aio.ServicerContext) -> user_pb2.user:
        user = await User.filter(id=request.user_id).first()
        if not user:
            await context.abort(grpc.StatusCode.NOT_FOUND, "用户不存在")
        return serialize_user(user)

    async def update_username(self,
                              request: user_pb2.update_username_request,
                              context: aio.ServicerContext) -> Empty:
        if not request.username:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "用户名不能为空")
        valid = await User.filter(id=request.user_id).update(username=request.username)
        if valid:
            await UserInfo.save_user(request.user_id, username=request.username)
        return Empty()

    async def update_avatar(self,
                            request: user_pb2.update_avatar_request,
                            context: aio.ServicerContext) -> user_pb2.avatar_reply:
        extension = os.path.splitext(request.filename)[-1].lower()
        if extension not in allowed_extensions:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, f"不支持的图片格式{extension}")

        if request.content_type not in allowed_mime_types:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, f"不支持的图片类型{request.content_type}")

        mime_type = magic.from_buffer(request.content, mime=True)
        if mime_type not in allowed_mime_types:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, f"不支持的图片类型{mime_type}")

        filename = f"avatar_{uuid.uuid4().hex}{extension}"
        path = join(STORAGE_DIR_NAME, filename)
        async with aiofiles.open(path, "wb") as destination:
            await destination.write(request.content)
        url = urljoin(SERVER_URL, path)
        valid = await User.filter(id=request.user_id).update(avatar=url)
        if valid:
            await UserInfo.save_user(request.user_id, avatar=url)
        return user_pb2.avatar_reply(url=url)

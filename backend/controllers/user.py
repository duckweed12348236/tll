import os
import random
import string
from datetime import datetime
import uuid
from os.path import join
from urllib.parse import urljoin

from aredis_om import NotFoundError
from fastapi import APIRouter, Path, Query, Body, UploadFile, File, Request, HTTPException, status, Depends
from magic import magic
from tortoise.transactions import in_transaction
from aiofiles import open

from config import STORAGE_DIR, SERVER_URL
from dependencies import get_now, get_user
from models.user import User, Address
from schemas.user import AddressIn, Account
from plugins.aliyun_smscode import AliyunSmsCodeSender
from plugins.token_handler import TokenHandler
from plugins.redis import UserCache, AddressCache, VerificationCode

router = APIRouter(prefix="/user")
allowed_extensions = {'.jpg', '.jpeg', '.png', '.webp'}
allowed_mime_types = {
    'image/jpg',
    'image/jpeg',
    'image/png',
    'image/webp'
}
verification_code_sender = AliyunSmsCodeSender()
token_handler = TokenHandler()


@router.get("/verification-code")
async def get_verification_code(telephone: str = Query(min_length=1)):
    code = "".join(random.sample(string.digits, 4))
    print(code)
    # await verification_code_sender.send(telephone, code)
    await VerificationCode.save_code(telephone, code)
    return None


@router.post("/login")
async def login(account: Account, now: datetime = Depends(get_now)):
    telephone = account.telephone

    try:
        code = await VerificationCode.find(VerificationCode.telephone == telephone).first()
        await VerificationCode.delete(code.pk)
    except NotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "请先获取验证码")

    if account.code != code.value:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "验证码错误")
    async with in_transaction():
        user, _ = await User.get_or_create(telephone=telephone)
        user.last_login = now
        await user.save(update_fields=["last_login"])
    kwargs = user.serialize()
    await UserCache.save_user(**kwargs)
    kwargs.pop("password")
    tokens = token_handler.make_tokens(user.id)
    return {"user": kwargs, **tokens}


@router.post("/access-token")
async def update_access_token(refresh_token: str = Body(min_length=1)):
    try:
        user_id = token_handler.decode_refresh_token(refresh_token)
    except ValueError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(e))
    return token_handler.update_token(user_id)


@router.post("/username")
async def update_username(username: str = Body(min_length=1), user: User = Depends(get_user)):
    result = await User.filter(id=user.id).update(username=username)
    if result:
        await UserCache.save_user(user.id, username=username)
    return None


@router.post("/avatar")
async def update_avatar(avatar: UploadFile = File(), user: User = Depends(get_user)):
    extension = os.path.splitext(avatar.filename)[-1].lower()
    if extension not in allowed_extensions:
        raise HTTPException(status.HTTP_406_NOT_ACCEPTABLE, f"不支持的图片格式{extension}")
    mime_type = avatar.content_type
    if mime_type not in allowed_mime_types:
        raise HTTPException(status.HTTP_406_NOT_ACCEPTABLE, f"不支持的图片类型{mime_type}")
    head_buffer = await avatar.read(1024)
    mime_type = magic.from_buffer(head_buffer, mime=True)
    if mime_type not in allowed_mime_types:
        raise HTTPException(status.HTTP_406_NOT_ACCEPTABLE, f"不支持的图片类型{mime_type}")
    await avatar.seek(0)
    filename = f"avatar_{uuid.uuid4().hex}{extension}"
    path = join(STORAGE_DIR, filename)
    async with open(path, "wb") as destination:
        while buffer := await avatar.read(1024):
            await destination.write(buffer)
    url = urljoin(SERVER_URL, filename)
    result = await User.filter(id=user.id).update(avatar=url)
    if result:
        await UserCache.save_user(user.id, avatar=url)
    return {"url": url}


@router.post("/address")
async def create_address(address_in: AddressIn, user: User = Depends(get_user)):
    address = await Address.create(user_id=user.id, **address_in.model_dump())
    await AddressCache.save_address(**address.serialize())
    return None


@router.delete("/address/{aid}")
async def delete_address(aid: int = Path(gt=0), user: User = Depends(get_user)):
    result = await Address.filter(id=aid, user_id=user.id).delete()
    if result:
        await AddressCache.find(AddressCache.id == aid, AddressCache.user_id == user.id).delete()
    return None


@router.get("/address")
async def list_addresses(user: User = Depends(get_user)):
    return await AddressCache.find(AddressCache.user_id == user.id).values().all()


@router.put("/address/{aid}")
async def update_address(address_in: AddressIn, aid: int = Path(gt=0), user: User = Depends(get_user)):
    kwargs = address_in.model_dump()
    result = await Address.filter(id=aid, user_id=user.id).update(**kwargs)
    if result:
        await AddressCache.save_address(aid, user.id, **kwargs)
    return None


@router.post("/address/{aid}")
async def set_default_address(aid: int = Path(gt=0), user: User = Depends(get_user)):
    async with in_transaction():
        address = await AddressCache.get_address(aid, user.id)
        if not address:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "不存在该地址")
        user.default_address_id = address.id
        await user.save(update_fields=["default_address_id"])
    await UserCache.save_user(user.id, default_address_id=address.id)
    return None

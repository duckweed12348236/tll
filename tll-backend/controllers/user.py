import os
import random
import string
import uuid
from os.path import join
from urllib.parse import urljoin

import magic
from aiofiles import open as aio_open
from aredis_om import NotFoundError
from fastapi import APIRouter, Depends, File, HTTPException, Path, Query, UploadFile, status
from loguru import logger

from config import SERVER_URL, STORAGE_DIR_NAME
from dependencies import get_identity
from models.auth import Identity
from models.shopping import Address
from plugins.aliyun_smscode import AliyunSmsCodeSender
from plugins.gateway import send
from plugins.redis import Code
from schemas.user import Account, AddressIn, RefreshToken, Username

router = APIRouter(prefix="/user")
verification_code_sender = AliyunSmsCodeSender()
allowed_extensions = {'.jpg', '.jpeg', '.png', '.webp'}
allowed_mime_types = {
    'image/jpg',
    'image/jpeg',
    'image/png',
    'image/webp'
}


@router.get("/verification-code")
async def get_verification_code(telephone: str = Query(min_length=1)):
    value = "".join(random.sample(string.digits, 4))
    logger.info(f"verification code of {telephone}: {value}")
    await verification_code_sender.send(telephone, value)
    await Code.create(telephone=telephone, value=value)
    return None


@router.post("/login")
async def login(account: Account):
    try:
        code = await Code.find(Code.telephone == account.telephone).first()
        await Code.delete(code.pk)
    except NotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "请先获取验证码")

    if account.code != code.value:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "验证码错误")

    return await send("POST", "/user/login", json={"telephone": account.telephone})


@router.post("/access-token")
async def update_access_token(refresh_token: RefreshToken):
    return await send("POST", "/user/access-token", json=refresh_token.model_dump())


@router.post("/username")
async def update_username(username: Username, identity: Identity = Depends(get_identity)):
    await Identity.filter(id=identity.id).update(username=username.value)
    identity.username = username.value
    return None


@router.post("/avatar")
async def update_avatar(avatar: UploadFile = File(), identity: Identity = Depends(get_identity)):
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
    path = join(STORAGE_DIR_NAME, filename)
    async with aio_open(path, "wb") as destination:
        while buffer := await avatar.read(1024):
            await destination.write(buffer)
    url = urljoin(SERVER_URL, path)
    await Identity.filter(id=identity.id).update(avatar=url)
    identity.avatar = url
    return {"url": url}


@router.post("/address")
async def create_address(address_in: AddressIn, identity: Identity = Depends(get_identity)):
    await Address.create(identity_id=identity.id, **address_in.model_dump())
    return None


@router.delete("/address/{aid}")
async def delete_address(aid: int = Path(gt=0), identity: Identity = Depends(get_identity)):
    await Address.filter(id=aid, identity_id=identity.id).delete()
    return None


@router.get("/address")
async def list_addresses(identity: Identity = Depends(get_identity)):
    return await Address.filter(identity_id=identity.id).values()


@router.put("/address/{aid}")
async def update_address(address_in: AddressIn, aid: int = Path(gt=0), identity: Identity = Depends(get_identity)):
    await Address.filter(id=aid, identity_id=identity.id).update(**address_in.model_dump())
    return None


@router.post("/address/{aid}")
async def set_default_address(aid: int = Path(gt=0), identity: Identity = Depends(get_identity)):
    address = await Address.filter(id=aid, identity_id=identity.id).first()
    if not address:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "不存在该地址")

    await Identity.filter(id=identity.id).update(default_address_id=address.id)
    identity.default_address_id = address.id
    return None

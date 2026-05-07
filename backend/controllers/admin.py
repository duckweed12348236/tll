import os
import uuid
from os.path import join
from urllib.parse import urljoin
from datetime import datetime, timedelta, time

import magic
from aiofiles import open
from fastapi import Depends, HTTPException, status, APIRouter, UploadFile, File, Path, Query
from loguru import logger
from tortoise.transactions import in_transaction

from config import STORAGE_DIR, SERVER_URL
from dependencies import get_now
from plugins.redis import ProductCache, OrderCache
from schemas.admin import ProductIn, ProductQuery, SalesStatusOption, OrderQuery, OrderStatusOption, DayOption
from models.shopping import Product, OrderStatus

router = APIRouter(prefix="/admin")
allowed_extensions = {'.jpg', '.jpeg', '.png', '.webp'}
allowed_mime_types = {
    'image/jpg',
    'image/jpeg',
    'image/png',
    'image/webp'
}


@router.post("/image")
async def upload_images(images: list[UploadFile] = File()):
    urls = []
    for image in images:
        extension = os.path.splitext(image.filename)[-1].lower()
        if extension not in allowed_extensions:
            logger.info(f"不支持的图片格式{extension}")
            continue
        mime_type = image.content_type
        if mime_type not in allowed_mime_types:
            logger.info(f"不支持的图片类型{mime_type}")
            continue
        head_buffer = await image.read(1024)
        mime_type = magic.from_buffer(head_buffer, mime=True)
        if mime_type not in allowed_mime_types:
            logger.info(f"不支持的图片类型{mime_type}")
            continue
        await image.seek(0)
        filename = f"image_{uuid.uuid4().hex}{extension}"
        path = join(STORAGE_DIR, filename)
        async with open(path, "wb") as destination:
            while buffer := await image.read(1024):
                await destination.write(buffer)
        urls.append(urljoin(SERVER_URL, path))
    return urls


@router.post("/product")
async def create_product(product_in: ProductIn):
    product = await Product.create(**product_in.model_dump())
    await ProductCache.save_product(**product.serialize())
    return None


@router.get("/product")
async def list_products(query: ProductQuery = Query()):
    exprs = []
    if query.name:
        exprs.append(ProductCache.name % query.name)
    if query.price_max >= 0:
        exprs.append(ProductCache.price <= query.price_max)
    if query.price_min >= 0:
        exprs.append(ProductCache.price >= query.price_min)
    if query.stock_max >= 0:
        exprs.append(ProductCache.stock <= query.stock_max)
    if query.stock_min >= 0:
        exprs.append(ProductCache.stock >= query.stock_min)
    if query.discontinued != SalesStatusOption.ALL:
        exprs.append(ProductCache.discontinued == query.discontinued)
    return await ProductCache.find(*exprs).sort_by("-creation_time").page(
        (query.page - 1) * query.size, query.size)


@router.put("/product/{product_id}")
async def update_product(product_in: ProductIn, product_id: int = Path(gt=0)):
    result = await Product.filter(id=product_id).update(**product_in.model_dump())
    if result:
        await ProductCache.save_product(product_id, **product_in.model_dump())
    return None


@router.patch("/product/{product_id}")
async def update_product_status(product_id: int = Path(gt=0)):
    async with in_transaction():
        product = await Product.filter(id=product_id).first().only("id", "discontinued")
        if not product:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "商品不存在")
        product.discontinued = not product.discontinued
        await product.save(update_fields=["discontinued"])
    await ProductCache.save_product(product_id, discontinued=product.discontinued)
    return None


@router.delete("/product/{product_id}")
async def delete_product(product_id: int = Path(gt=0)):
    result = await Product.filter(id=product_id, discontinued=True).delete()
    if not result:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "该商品正在售卖，请先下架")
    async with ProductCache.lock(product_id):
        await ProductCache.find(ProductCache.id == product_id).delete()
    return None


@router.get("/order")
async def list_orders(query: OrderQuery = Query()):
    exprs = []
    if query.status != OrderStatusOption.ALL:
        exprs.append(OrderCache.status == query.status)
    if query.amount_min:
        exprs.append(OrderCache.amount >= query.amount_min)
    if query.amount_max:
        exprs.append(OrderCache.amount <= query.amount_max)
    if query.creation_time_min:
        exprs.append(OrderCache.creation_time >= query.creation_time_min)
    if query.creation_time_max:
        exprs.append(OrderCache.creation_time <= query.creation_time_max)
    return await OrderCache.find(*exprs).sort_by("-creation_time").page(
        (query.page - 1) * query.size, query.size)


@router.get("/order/summary")
async def get_order_summary(days: DayOption = Query()):
    today = datetime.combine(datetime.today(), time.min)
    orders = await OrderCache.find(
        OrderCache.status != OrderStatus.UNPAID,
        OrderCache.creation_time <= today,
        OrderCache.creation_time >= (today - timedelta(days=days.value))
    ).sort_by("-creation_time").only("id", "amount", "quantity", "creation_time").all()
    summary = {}
    for order in orders:
        date = order.creation_time.replace(hour=0, minute=0, second=0, microsecond=0)
        item = summary.get(date, None)
        if not item:
            summary[date] = {"amount": order.amount, "quantity": order.quantity, "count": 1}
            continue
        item["amount"] += order.amount
        item["quantity"] += order.quantity
        item["count"] += 1
    return summary

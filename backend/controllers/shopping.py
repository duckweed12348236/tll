from datetime import datetime
from decimal import Decimal
from typing import Any

from aredis_om import NotFoundError
from fastapi import APIRouter, Path, Query, Form, HTTPException, status, Depends
from redis.exceptions import LockError

from models.user import User
from plugins.alipay import Alipay
from plugins.kafka import KafkaProducer
from plugins.snowflake import Snowflake
from models.shopping import OrderStatus
from plugins.redis import ProductInfo, OrderInfo, AddressInfo, AddressEmbedded, ProductEmbedded
from schemas.shopping import OrderIn, OrderOption
from dependencies import get_now, get_user

router = APIRouter(prefix="/shopping")
alipay = Alipay()
kafka_producer = KafkaProducer()
snowflake = Snowflake()


@router.get("/product")
async def list_products(keyword: str | None = Query(None, min_length=1)):
    exprs = [ProductInfo.stock > 0, ProductInfo.discontinued == False]
    if keyword:
        exprs.append(ProductInfo.name % keyword)
    return await ProductInfo.find(*exprs).sort_by("-creation_time").values().all()


@router.get("/product/{product_id}")
async def get_product(user: User = Depends(get_user), product_id: int = Path(gt=0)):
    try:
        product = await ProductInfo.find(
            ProductInfo.id == product_id,
            ProductInfo.stock > 0,
            ProductInfo.discontinued == False).values().first()
    except NotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "商品已下架或已售罄")

    if not user.default_address_id:
        return [product, None]
    address = await AddressInfo.get_address(user.default_address_id)
    return [product, address]


@router.post("/order")
async def place_order(order_in: OrderIn, user: User = Depends(get_user), now: datetime = Depends(get_now)):
    address = await AddressInfo.get_address(order_in.address_id, user.id)
    if not address:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "不存在该地址")

    quantity = order_in.quantity
    product_id = order_in.product_id
    try:
        async with ProductInfo.lock(product_id, 30):
            product = await ProductInfo.find(
                ProductInfo.id == product_id,
                ProductInfo.per_max_quantity >= quantity,
                ProductInfo.stock >= quantity
            ).first()
            await product.update_stock(-quantity)
    except NotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "商品已下架或已售罄")
    except LockError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "请稍后重新下单")

    order_id = snowflake.get_id()
    price = product.price.quantize(Decimal("0.00"))
    amount = (price * quantity).quantize(Decimal("0.00"))
    print(amount)
    url = alipay.pay(str(order_id), format(amount, ".2f"), product.name)
    order = await OrderInfo.create(
        id=order_id,
        quantity=quantity,
        amount=amount,
        creation_time=now,
        address=AddressEmbedded(
            name=address.name,
            telephone=address.telephone,
            region=address.region,
            detail=address.detail
        ),
        product=ProductEmbedded(
            name=product.name,
            price=price,
            covers=product.covers,
            details=product.details
        ),
        url=url,
        user_id=user.id
    )
    value = {**order.model_dump(exclude={"pk"}), "product_id": product_id}
    await kafka_producer.send("create_orders", value)
    return url


@router.post("/order/{order_id}")
async def pay_order(order_id: int = Path(gt=0),
                    order_info: dict[str, Any] = Form(),
                    user: User = Depends(get_user)):
    if not alipay.verify(order_info, order_info.pop("sign")):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "非法订单")

    try:
        order = await OrderInfo.find(OrderInfo.id == order_id,
                                     OrderInfo.user_id == user.id,
                                     OrderInfo.is_deleted == False).first()
    except NotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "订单不存在")

    trade_status = order_info["trade_status"]
    trade_number = order_info["trade_no"]
    match trade_status:
        case "TRADE_SUCCESS":
            new_status = OrderStatus.PAID
        case "TRADE_CLOSED":
            new_status = OrderStatus.REFUNDED
        case _:
            return None
    await order.update(status=new_status, trade_number=trade_number)
    value = {**order.model_dump(exclude={"pk"}), "product_id": None}
    if new_status == OrderStatus.REFUNDED:
        value["product_id"] = order_info["product_id"]
    await kafka_producer.send("update_orders", value)
    return None


@router.get("/order")
async def list_orders(user: User = Depends(get_user), option: OrderOption = Query(OrderOption.ALL)):
    exprs = [
        OrderInfo.user_id == user.id,
        OrderInfo.is_deleted == False
    ]
    if option != OrderOption.ALL:
        exprs.append(OrderInfo.is_deleted == False)
    return await OrderInfo.find(*exprs).sort_by("-creation_time").values().all()


@router.delete("/order/{order_id}")
async def delete_order(user: User = Depends(get_user), order_id: int = Path(gt=0)):
    order = await OrderInfo.find(OrderInfo.id == order_id,
                                 OrderInfo.user_id == user.id,
                                 OrderInfo.is_deleted == False).first()
    await order.remove()
    value = {**order.model_dump(exclude={"pk"}), "is_deleted": True}
    await kafka_producer.send("delete_orders", value)
    return None

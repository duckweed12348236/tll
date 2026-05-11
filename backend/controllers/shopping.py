from datetime import datetime
from decimal import Decimal
from typing import Any

from aredis_om import NotFoundError
from fastapi import APIRouter, Path, Query, Form, HTTPException, status, Depends
from redis.exceptions import LockError

from models.user import User
from plugins.alipay import Alipay
from plugins.kafka import KafkaProducer
from plugins.snowflake.snowflake import Snowflake
from models.shopping import OrderStatus
from plugins.redis import ProductCache, OrderCache, AddressCache, AddressInfo, ProductInfo
from schemas.shopping import OrderIn, OrderOption
from dependencies import get_now, get_user

router = APIRouter(prefix="/shopping")
alipay = Alipay()
kafka_producer = KafkaProducer()
snowflake = Snowflake()


@router.get("/product")
async def list_products(keyword: str | None = Query(None, min_length=1)):
    exprs = [ProductCache.stock > 0, ProductCache.discontinued == False]
    if keyword:
        exprs.append(ProductCache.name % keyword)
    return await ProductCache.find(*exprs).sort_by("-creation_time").values().all()


@router.get("/product/{product_id}")
async def get_product(user: User = Depends(get_user), product_id: int = Path(gt=0)):
    try:
        product = await ProductCache.find(
            ProductCache.id == product_id,
            ProductCache.stock > 0,
            ProductCache.discontinued == False).values().first()
    except NotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "商品已下架或已售罄")

    if not user.default_address_id:
        return [product, None]
    address = await AddressCache.get_address(user.default_address_id)
    return [product, address]


@router.post("/order")
async def place_order(order_in: OrderIn, user: User = Depends(get_user), now: datetime = Depends(get_now)):
    address = await AddressCache.get_address(order_in.address_id, user.id)
    if not address:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "不存在该地址")

    quantity = order_in.quantity
    product_id = order_in.product_id
    try:
        async with ProductCache.lock(product_id, 30):
            product = await ProductCache.find(
                ProductCache.id == product_id,
                ProductCache.per_max_quantity >= quantity,
                ProductCache.stock >= quantity).first()
            await ProductCache.update_stock(product_id, -quantity)
    except LockError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "请稍后重新下单")
    except NotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "商品已下架或已售罄")

    order_id = snowflake.get_id()
    price = Decimal(product.price)
    amount = format(price * quantity, ".2f")
    print(amount)
    url = alipay.pay(str(order_id), amount, product.name)
    order = await OrderCache.create(
        id=order_id,
        quantity=quantity,
        amount=amount,
        creation_time=now,
        address=AddressInfo(name=address.name,
                            telephone=address.telephone,
                            region=address.region,
                            detail=address.detail),
        product=ProductInfo(name=product.name,
                            price=product.price,
                            covers=product.covers,
                            details=product.details),
        url=url,
        user_id=user.id)
    await kafka_producer.send("decrease_stocks", {"id": product_id, "quantity": quantity})
    await kafka_producer.send("create_orders", order.model_dump(exclude={"pk"}))
    return url


@router.post("/order/{order_id}")
async def pay_order(order_id: int = Path(gt=0),
                    order_info: dict[str, Any] = Form(),
                    user: User = Depends(get_user)):
    if not alipay.verify(order_info, order_info.pop("sign")):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "非法订单")

    try:
        order = await OrderCache.find(OrderCache.id == order_id,
                                      OrderCache.user_id == user.id,
                                      OrderCache.is_deleted == False).first()
    except NotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "订单不存在")

    trade_status = order_info["trade_status"]
    trade_number = order_info["trade_no"]
    match trade_status:
        case "TRADE_SUCCESS":
            new_status = OrderStatus.PAID
        case "TRADE_CLOSED":
            async with ProductCache.lock(order.product_id):
                await ProductCache.update_stock(order.product_id, order.quantity)
            await kafka_producer.send("increase_stocks",
                                      {"id": order.product_id, "quantity": order.quantity})
            new_status = OrderStatus.REFUNDED
        case _:
            return None
    await kafka_producer.send("update_orders",
                              {"id": order_id, "status": new_status, "trade_number": trade_number})
    await order.update(status=new_status, trade_number=trade_number)
    return None


@router.get("/order")
async def list_orders(user: User = Depends(get_user), option: OrderOption = Query(OrderOption.ALL)):
    if option == OrderOption.ALL:
        return await OrderCache.find(OrderCache.user_id == user.id,
                                     OrderCache.is_deleted == False).sort_by("-creation_time").values().all()
    return await OrderCache.find(OrderCache.user_id == user.id,
                                 OrderCache.status == option,
                                 OrderCache.is_deleted == False).sort_by("-creation_time").values().all()


@router.delete("/order/{order_id}")
async def delete_order(user: User = Depends(get_user), order_id: int = Path(gt=0)):
    await kafka_producer.send("delete_orders", order_id)
    await OrderCache.find(OrderCache.id == order_id,
                          OrderCache.user_id == user.id,
                          OrderCache.is_deleted == False).delete()
    return None

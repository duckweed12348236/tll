import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Path, Query, Form, HTTPException, status, Depends

from models.auth import Identity
from models.shopping import Address, Order, OrderStatus, Product
from plugins.alipay import Alipay
from plugins.kafka import KafkaProducer
from plugins.redis import OrderToken, Stock, stock_not_cached
from plugins.snowflake import Snowflake
from schemas.shopping import AddressIn, OrderIn, OrderOption
from dependencies import get_identity, get_now

router = APIRouter(prefix="/shopping")
alipay = Alipay()
kafka_producer = KafkaProducer()
snowflake = Snowflake()
pay_statuses = {
    "TRADE_SUCCESS": OrderStatus.PAID,
    "TRADE_CLOSED": OrderStatus.REFUNDED,
    "TRADE_FINISHED": OrderStatus.FINISHED
}


@router.get("/product")
async def list_products(keyword: str | None = Query(None, min_length=1)):
    query = Product.filter(stock__gt=0, discontinued=False)
    if keyword:
        query = query.filter(name__icontains=keyword)
    return await query.order_by("-creation_time").values()


@router.get("/product/{product_id}")
async def get_product(identity: Identity = Depends(get_identity), product_id: int = Path(gt=0)):
    product = await Product.filter(id=product_id, stock__gt=0, discontinued=False).first()
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "商品已下架或已售罄")

    if not identity.default_address_id:
        return [product.serialize(), None]
    address = await Address.filter(id=identity.default_address_id).first()
    return [product.serialize(), address.serialize() if address else None]


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


notify_url = "https://1263cm65sc709.vicp.fun:12586/shopping/order/notify"


@router.get("/order/token")
async def get_order_token(identity: Identity = Depends(get_identity)):
    token = uuid.uuid4().hex
    await OrderToken.claim(identity.id, token)
    return {"token": token}


@router.post("/order")
async def place_order(order_in: OrderIn, identity: Identity = Depends(get_identity), now: datetime = Depends(get_now)):
    if not await OrderToken.claim(identity.id, order_in.token):
        value = await OrderToken.get(identity.id, order_in.token)
        if value and value != OrderToken.pending:
            return value
        raise HTTPException(status.HTTP_409_CONFLICT, "订单正在处理中，请勿重复提交")

    quantity = order_in.quantity
    product_id = order_in.product_id
    stock_reduced = False
    try:
        address = await Address.filter(id=order_in.address_id, identity_id=identity.id).first()
        if not address:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "不存在该地址")

        product = await Product.filter(id=product_id, discontinued=False).first()
        if not product or product.per_max_quantity < quantity:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "商品已下架或已售罄")

        remaining = await Stock.decrease(product_id, quantity)
        if remaining == stock_not_cached:
            await Stock.set(product_id, product.stock, nx=True)
            remaining = await Stock.decrease(product_id, quantity)
        if remaining < 0:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "商品已下架或已售罄")
        stock_reduced = True

        order_id = snowflake.get_id()
        price = product.price.quantize(Decimal("0.00"))
        amount = (price * quantity).quantize(Decimal("0.00"))
        url = alipay.pay(
            order_id,
            format(amount, ".2f"),
            product.name,
            f"{notify_url}?order_id={order_id}&product_id={product_id}&identity_id={identity.id}"
        )
        order = await Order.create(
            id=order_id,
            quantity=quantity,
            amount=amount,
            creation_time=now,
            address=dict(
                name=address.name,
                telephone=address.telephone,
                region=address.region,
                detail=address.detail
            ),
            product=dict(
                name=product.name,
                price=format(price, ".2f"),
                covers=product.covers,
                details=product.details
            ),
            url=url,
            identity_id=identity.id
        )
        value = {**order.serialize(), "product_id": product_id}
        value.pop("identity", None)
        await kafka_producer.send("create_orders", value)
    except Exception:
        if stock_reduced:
            await Stock.increase(product_id, quantity)
        await OrderToken.release(identity.id, order_in.token)
        raise

    await OrderToken.complete(identity.id, order_in.token, url)
    return url


@router.post("/order/notification")
async def pay_order(order_id: int = Query(gt=0),
                    product_id: int = Query(gt=0),
                    identity_id: int = Query(gt=0),
                    order_info: dict[str, Any] = Form()):
    if not alipay.verify(order_info, order_info.pop("sign")):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "非法订单")

    new_status = pay_statuses.get(order_info["trade_status"])
    if new_status is None:
        return None

    value = dict(
        id=order_id,
        identity_id=identity_id,
        product_id=product_id,
        status=int(new_status),
        trade_number=int(order_info["trade_no"])
    )
    topic = "refund_orders" if new_status == OrderStatus.REFUNDED else "pay_orders"
    await kafka_producer.send(topic, value)
    return None


@router.get("/order")
async def list_orders(identity: Identity = Depends(get_identity), option: OrderOption = Query(OrderOption.ALL)):
    query = Order.filter(identity_id=identity.id, is_deleted=False)
    if option != OrderOption.ALL:
        query = query.filter(status=option)
    return await query.order_by("-creation_time").values()


@router.delete("/order/{order_id}")
async def delete_order(identity: Identity = Depends(get_identity), order_id: int = Path(gt=0)):
    order = await Order.filter(id=order_id, identity_id=identity.id, is_deleted=False).first()
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "订单不存在")

    await Order.filter(id=order_id).update(is_deleted=True)
    value = {**order.serialize(), "is_deleted": True}
    value.pop("identity", None)
    await kafka_producer.send("delete_orders", value)
    return None

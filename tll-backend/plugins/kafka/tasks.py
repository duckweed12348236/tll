import asyncio
from typing import Any, Awaitable, Callable

from celery import group
from loguru import logger
from tortoise.transactions import in_transaction

from models.shopping import Order, OrderStatus, Product
from plugins.celery.tasks import pay_order
from plugins.redis import PendingPayment, Stock

Task = Callable[[list[dict[str, Any]]], Awaitable[None]]
handlers: dict[str, Task] = {}


class task:
    """消费任务装饰器，按主题把处理逻辑注册到 handlers"""

    def __init__(self, topic: str) -> None:
        self.topic = topic

    def __call__(self, handler: Task) -> Task:
        handlers[self.topic] = handler
        return handler


def dispatch_payments(values: list[dict[str, Any]]) -> None:
    """把待处理支付打包成一个 group 一次性投递"""
    signatures = [
        pay_order.s(value["order_id"], value["identity_id"], value["status"], value["trade_number"])
        for value in values
    ]
    group(*signatures).apply_async()
    return None


async def retry_later(by_id: dict[int, dict[str, Any]], missing: set[int], reason: str) -> None:
    """订单尚未创建时批量缓存支付结果，并交给 Celery 阶梯重试"""
    pending = [
        dict(
            order_id=order_id,
            identity_id=by_id[order_id]["identity_id"],
            status=by_id[order_id]["status"],
            trade_number=by_id[order_id]["trade_number"]
        )
        for order_id in missing
    ]
    if not pending:
        return None
    logger.warning(f"{len(pending)} 个订单{reason}，批量缓存支付结果并等待重试")
    await PendingPayment.save_many(pending)
    await asyncio.to_thread(dispatch_payments, pending)
    return None


@task("create_orders")
async def create_orders(values: list[dict[str, Any]]) -> None:
    """幂等创建订单：已存在的订单跳过，库存先在循环中算好再批量写入"""
    by_id = {value["id"]: value for value in values if value}
    if not by_id:
        return None

    existing = set(await Order.filter(id__in=by_id).values_list("id", flat=True))
    created = [value for order_id, value in by_id.items() if order_id not in existing]
    if not created:
        return None

    product_ids = {value["product_id"] for value in created}
    products = {product.id: product for product in await Product.filter(id__in=product_ids).only("id", "stock")}
    changes = []
    for value in created:
        product = products.get(value.pop("product_id"))
        if not product or product.stock < value["quantity"]:
            continue
        product.stock -= value["quantity"]
        changes.append(product)

    async with in_transaction():
        if changes:
            await Product.bulk_update(changes, ["stock"])
        await Order.bulk_create([Order(**value) for value in created])
    return None


@task("pay_orders")
async def pay_orders(values: list[dict[str, Any]]) -> None:
    """批量更新已存在的订单，未创建的订单缓存到 Redis 并交给 Celery 重试"""
    by_id = {value["id"]: value for value in values if value}
    if not by_id:
        return None

    batch = await Order.filter(id__in=by_id).all()
    for order in batch:
        value = by_id[order.id]
        order.status = OrderStatus(value["status"])
        order.trade_number = value["trade_number"]

    if batch:
        async with in_transaction():
            await Order.bulk_update(batch, ["status", "trade_number"])

    await retry_later(by_id, by_id.keys() - {order.id for order in batch}, "尚未创建")
    return None


@task("refund_orders")
async def refund_orders(values: list[dict[str, Any]]) -> None:
    """批量处理退款：库存先算好再批量回补，已退款的订单不重复回补"""
    by_id = {value["id"]: value for value in values if value}
    if not by_id:
        return None

    batch = await Order.filter(id__in=by_id).all()
    refunded = [order for order in batch if order.status != OrderStatus.REFUNDED]
    product_ids = {by_id[order.id].get("product_id") for order in refunded} - {None}
    products = {product.id: product for product in await Product.filter(id__in=product_ids).only("id", "stock")}

    changes = []
    stocks = []
    for order in refunded:
        product = products.get(by_id[order.id].get("product_id"))
        if not product:
            continue
        product.stock += order.quantity
        changes.append(product)
        stocks.append((product.id, order.quantity))

    for order in batch:
        value = by_id[order.id]
        order.status = OrderStatus(value["status"])
        order.trade_number = value["trade_number"]

    async with in_transaction():
        if changes:
            await Product.bulk_update(changes, ["stock"])
        if batch:
            await Order.bulk_update(batch, ["status", "trade_number"])

    if stocks:
        await Stock.increase_many(stocks)

    await retry_later(by_id, by_id.keys() - {order.id for order in batch}, "的退款尚未创建")
    return None


@task("delete_orders")
async def delete_orders(values: list[dict[str, Any]]) -> None:
    """只标记已存在的订单，不再为未创建的订单补数据"""
    by_id = {value["id"]: value for value in values if value}
    if not by_id:
        return None

    orders = await Order.filter(id__in=by_id).all()
    if not orders:
        return None

    for order in orders:
        order.is_deleted = True

    async with in_transaction():
        await Order.bulk_update(orders, ["is_deleted"])
    return None

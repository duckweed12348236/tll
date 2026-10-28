import asyncio
from typing import Any, Coroutine

from celery import shared_task
from loguru import logger
from tortoise import Tortoise

from config import TORTOISE_ORM_CONFIG
from models.shopping import Order, OrderStatus
from plugins.redis import PendingPayment

max_retries = 100
max_countdown = 10

worker_loop: asyncio.AbstractEventLoop | None = None
initialized = False


def get_loop() -> asyncio.AbstractEventLoop:
    global worker_loop
    if worker_loop is None or worker_loop.is_closed():
        worker_loop = asyncio.new_event_loop()
    return worker_loop


def run(coro: Coroutine[Any, Any, Any]) -> Any:
    return get_loop().run_until_complete(coro)


async def prepare() -> None:
    global initialized
    if initialized:
        return None
    await Tortoise.init(config=TORTOISE_ORM_CONFIG, _enable_global_fallback=True)
    initialized = True
    return None


def close_worker() -> None:
    global initialized
    if not initialized:
        return None
    run(Tortoise.close_connections())
    initialized = False
    return None


async def apply_payment(order_id: int, identity_id: int, status: int, trade_number: int) -> bool:
    """订单已创建则更新状态与交易凭证号，未创建返回 False 交由任务重试"""
    order = await Order.filter(id=order_id, identity_id=identity_id, is_deleted=False).first()
    if not order:
        return False

    await Order.filter(id=order_id).update(status=OrderStatus(status), trade_number=trade_number)
    await PendingPayment.remove(order_id)
    return True


@shared_task(bind=True, max_retries=None)
def pay_order(self, order_id: int, identity_id: int, status: int, trade_number: int) -> None:
    run(prepare())
    if run(apply_payment(order_id, identity_id, status, trade_number)):
        return None

    attempts = self.request.retries
    if attempts >= max_retries:
        logger.error(
            f"支付订单重试达到上限 {max_retries}: order_id={order_id}, identity_id={identity_id}, "
            f"status={status}, trade_number={trade_number}"
        )
        return None

    run(PendingPayment.save(order_id, identity_id, status, trade_number))
    raise self.retry(countdown=min(2 ** attempts, max_countdown))

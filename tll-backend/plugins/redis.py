from abc import ABC
from datetime import datetime
from typing import Any, Self

from aredis_om import Field, JsonModel, Migrator, NotFoundError, get_redis_connection
from redis.asyncio.client import Pipeline

from config import REDIS_URL
from models.shopping import Product
from plugins.json import dump, load

db = get_redis_connection(url=REDIS_URL)

stock_not_cached = -2
stock_insufficient = -1
decrease_stock_script = """
local value = redis.call('get', KEYS[1])
if not value then
    return -2
end
local stock = tonumber(value)
local quantity = tonumber(ARGV[1])
if stock < quantity then
    return -1
end
redis.call('decrby', KEYS[1], quantity)
return stock - quantity
"""
increase_stock_script = """
local value = redis.call('get', KEYS[1])
if not value then
    return -2
end
local stock = tonumber(value)
local quantity = tonumber(ARGV[1])
redis.call('incrby', KEYS[1], quantity)
return stock + quantity
"""


class Cache(JsonModel, ABC):
    @classmethod
    def create_pipeline(cls) -> Pipeline:
        return cls.db().pipeline()

    @classmethod
    async def create(cls,
                     pipeline: Pipeline | None = None,
                     **kwargs: Any) -> Self:
        instance = cls(**kwargs)
        await instance.save(pipeline)
        return instance

    async def remove(self, pipeline: Pipeline | None = None) -> None:
        await self.delete(self.pk, pipeline)


class Code(Cache, index=True):
    telephone: str = Field(index=True, primary_key=True)
    value: str

    class Meta:
        model_key_prefix = "code"

    @classmethod
    async def create(cls,
                     pipeline: Pipeline | None = None,
                     **kwargs: Any) -> Self:
        if not pipeline:
            pipeline = cls.create_pipeline()
        instance = cls(**kwargs)
        await instance.save(pipeline)
        await instance.expire(300, pipeline)
        await pipeline.execute()
        return instance


class Stock:
    """商品库存缓存，读写与增减均通过 Lua 脚本保证原子性"""

    prefix = "stock"

    @classmethod
    def key(cls, product_id: int) -> str:
        return f"{cls.prefix}:{product_id}"

    @classmethod
    async def get(cls, product_id: int) -> int | None:
        value = await db.get(cls.key(product_id))
        if isinstance(value, (bytes, str, int)):
            return int(value)
        return None

    @classmethod
    async def set(cls, product_id: int, quantity: int, nx: bool = False) -> None:
        await db.set(cls.key(product_id), quantity, nx=nx)
        return None

    @classmethod
    async def remove(cls, product_id: int) -> None:
        await db.delete(cls.key(product_id))
        return None

    @classmethod
    async def decrease(cls, product_id: int, quantity: int) -> int:
        result = await db.eval(decrease_stock_script, 1, cls.key(product_id), quantity)
        if result is None:
            return stock_not_cached
        return int(result)

    @classmethod
    async def increase(cls, product_id: int, quantity: int) -> int:
        result = await db.eval(increase_stock_script, 1, cls.key(product_id), quantity)
        if result is None:
            return stock_not_cached
        return int(result)

    @classmethod
    async def decrease_many(cls, items: list[tuple[int, int]]) -> list[int]:
        """批量扣减库存，一次 pipeline 提交，返回各商品扣减后的库存"""
        if not items:
            return []
        pipeline = db.pipeline(transaction=False)
        for product_id, quantity in items:
            pipeline.eval(decrease_stock_script, 1, cls.key(product_id), quantity)
        results = await pipeline.execute()
        return [stock_not_cached if result is None else int(result) for result in results]

    @classmethod
    async def increase_many(cls, items: list[tuple[int, int]]) -> list[int]:
        """批量回补库存，一次 pipeline 提交，返回各商品回补后的库存"""
        if not items:
            return []
        pipeline = db.pipeline(transaction=False)
        for product_id, quantity in items:
            pipeline.eval(increase_stock_script, 1, cls.key(product_id), quantity)
        results = await pipeline.execute()
        return [stock_not_cached if result is None else int(result) for result in results]

    @classmethod
    async def init(cls) -> None:
        for product in await Product.all().only("id", "stock"):
            await cls.set(product.id, product.stock, nx=True)
        return None


class OrderToken:
    """下单幂等令牌：先领取占位，成功后写入结果，重复提交直接复用结果"""

    prefix = "order:token"
    pending = "pending"
    ttl = 300

    @classmethod
    def key(cls, identity_id: int, token: str) -> str:
        return f"{cls.prefix}:{identity_id}:{token}"

    @classmethod
    async def claim(cls, identity_id: int, token: str) -> bool:
        claimed = await db.set(cls.key(identity_id, token), cls.pending, nx=True, ex=cls.ttl)
        return bool(claimed)

    @classmethod
    async def get(cls, identity_id: int, token: str) -> str | None:
        value = await db.get(cls.key(identity_id, token))
        if isinstance(value, bytes):
            return value.decode()
        return value

    @classmethod
    async def complete(cls, identity_id: int, token: str, value: str) -> None:
        await db.set(cls.key(identity_id, token), value, ex=cls.ttl)
        return None

    @classmethod
    async def release(cls, identity_id: int, token: str) -> None:
        await db.delete(cls.key(identity_id, token))
        return None


class PendingPayment:
    """订单尚未落库时的支付回调缓存，供 Celery 重试时读取"""

    prefix = "payment:pending"
    ttl = 3600

    @classmethod
    def key(cls, order_id: int) -> str:
        return f"{cls.prefix}:{order_id}"

    @classmethod
    def payload(cls, order_id: int, identity_id: int, status: int, trade_number: int) -> dict[str, int]:
        return dict(
            order_id=order_id,
            identity_id=identity_id,
            status=status,
            trade_number=trade_number
        )

    @classmethod
    async def save(cls,
                   order_id: int,
                   identity_id: int,
                   status: int,
                   trade_number: int) -> None:
        await db.set(cls.key(order_id), dump(cls.payload(order_id, identity_id, status, trade_number)), ex=cls.ttl)
        return None

    @classmethod
    async def save_many(cls, values: list[dict[str, Any]]) -> None:
        """一次 pipeline 写入多条待处理支付"""
        if not values:
            return None
        pipeline = db.pipeline(transaction=False)
        for value in values:
            payload = cls.payload(value["order_id"], value["identity_id"], value["status"], value["trade_number"])
            pipeline.set(cls.key(value["order_id"]), dump(payload), ex=cls.ttl)
        await pipeline.execute()
        return None

    @classmethod
    async def get(cls, order_id: int) -> dict[str, Any] | None:
        value = await db.get(cls.key(order_id))
        if value is None:
            return None
        return load(value)

    @classmethod
    async def remove(cls, order_id: int) -> None:
        await db.delete(cls.key(order_id))
        return None


async def migrate() -> None:
    migrator = Migrator()
    await migrator.run()
    await Stock.init()

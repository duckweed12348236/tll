from datetime import datetime
from decimal import Decimal
from typing import Any, Self
from abc import ABC

from aredis_om import JsonModel, EmbeddedJsonModel, Field, Migrator, NotFoundError
from redis.asyncio.lock import Lock
from redis.asyncio.client import Pipeline

from models.shopping import OrderStatus, Order, Product
from models.user import Address


class Cache(JsonModel, ABC):
    @classmethod
    def lock(cls, name: str | int, blocking_timeout: int | None = None) -> Lock:
        return cls.db().lock(f":{cls.Meta.model_key_prefix}_lock:{name}", blocking_timeout=blocking_timeout)

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


class AddressInfo(Cache, index=True):
    id: int = Field(index=True, primary_key=True)
    name: str
    telephone: str
    region: str
    detail: str
    user_id: int = Field(index=True)

    class Meta:
        model_key_prefix = "address"

    @classmethod
    async def get_address(cls, key1: int, key2: int | None = None) -> Self | None:
        try:
            if not key2:
                return await cls.find(cls.id == key1).first()
            return await cls.find(cls.id == key1, cls.user_id == key2).first()
        except NotFoundError:
            return None

    @classmethod
    async def save_address(cls, key1: int | None = None, key2: int | None = None, **kwargs: Any) -> Self | None:
        if not key1 or not key2:
            instance = cls(**kwargs)
            await instance.save()
            return instance
        try:
            instance = await cls.find(cls.id == key1, cls.user_id == key2).first()
        except NotFoundError:
            return None
        await instance.update(**kwargs)
        return instance

    @classmethod
    async def init(cls):
        instances = [cls(**x) for x in await Address.all().values()]
        await cls.add(instances)


class UserInfo(Cache, index=True):
    id: int = Field(index=True, primary_key=True)
    telephone: str
    username: str
    avatar: str | None = None
    password: str | None = None
    active: bool = True
    last_login: datetime | None = None
    default_address_id: int | None = None

    class Meta:
        model_key_prefix = "user"

    @classmethod
    async def save_user(cls, key: int | None = None, **kwargs: Any) -> Self | None:
        if not key:
            instance = cls(**kwargs)
            pipeline = cls.create_pipeline()
            await instance.save(pipeline)
            await instance.expire(7 * 24 * 60 * 60, pipeline)
            await pipeline.execute()
            return instance
        try:
            instance = await cls.find(cls.id == key).first()
        except NotFoundError:
            return None
        await instance.update(**kwargs)
        return instance


class ProductInfo(Cache, index=True):
    id: int = Field(index=True, primary_key=True)
    name: str = Field(index=True, full_text_search=True)
    price: Decimal = Field(index=True)
    covers: list[str]
    details: list[str]
    stock: int = Field(index=True)
    per_max_quantity: int = Field(index=True)
    discontinued: bool = Field(False, index=True)
    creation_time: datetime = Field(index=True, sortable=True)

    class Meta:
        model_key_prefix = "product"

    async def update_stock(self, quantity: int) -> None:
        await self.db().json().numincrby(self.key(), ".stock", quantity)

    @classmethod
    async def init(cls):
        instances = [cls(**x) for x in await Product.all().values()]
        await cls.add(instances)


class AddressEmbedded(EmbeddedJsonModel):
    """
    地址信息模型

    用于存储和序列化地址相关信息的嵌入式JSON模型。

    Attributes:
        name (str): 收货人姓名
        telephone (str): 联系电话
        region (str): 所在地区
        detail (str): 详细地址
    """
    name: str
    telephone: str
    region: str
    detail: str


class ProductEmbedded(EmbeddedJsonModel):
    """
    商品信息嵌入模型

    Attributes:
        name (str): 商品名称
        price (Decimal): 商品价格
        covers (list[str]): 商品封面图片列表
        details (list[str]): 商品详情描述列表
    """
    name: str
    price: Decimal
    covers: list[str]
    details: list[str]


class OrderInfo(Cache, index=True):
    """
    订单缓存模型，用于在 Redis 中缓存订单数据

    Attributes:
        id (int): 订单唯一标识，主键
        status (OrderStatus): 订单状态，默认为未支付
        quantity (int): 订单商品数量
        amount (Decimal): 订单金额
        creation_time (datetime): 订单创建时间
        address (AddressEmbedded): 收货地址信息
        product (ProductEmbedded): 商品信息
        url (str): 订单相关链接
        trade_number (int | None): 交易编号
        is_deleted (bool): 是否已删除，默认为 False
        user_id (int): 用户ID
    """
    id: int = Field(index=True, primary_key=True)
    status: OrderStatus = Field(OrderStatus.UNPAID, index=True)
    quantity: int
    amount: Decimal
    creation_time: datetime = Field(index=True, sortable=True)
    address: AddressEmbedded
    product: ProductEmbedded
    url: str
    trade_number: int | None = None
    is_deleted: bool = Field(False, index=True)
    user_id: int = Field(index=True)

    class Meta:
        model_key_prefix = "order"

    @classmethod
    async def save_order(cls, key: int | None = None, **kwargs: Any) -> Self | None:
        address = kwargs.pop("address", None)
        product = kwargs.pop("product", None)
        if address:
            kwargs.update(address=AddressEmbedded(**address))
        if product:
            kwargs.update(product=ProductEmbedded(**product))
        if not key:
            instance = cls(**kwargs)
            await instance.save()
            return instance
        async with cls.lock(key):
            try:
                instance = await cls.find(cls.id == key).first()
            except NotFoundError:
                return None
            await instance.update(**kwargs)
        return instance

    @classmethod
    async def init(cls):
        instances = [cls(**x) for x in await Order.all().values()]
        await cls.add(instances)


async def migrate() -> None:
    migrator = Migrator()
    await migrator.run()
    await AddressInfo.init()
    await OrderInfo.init()
    await ProductInfo.init()

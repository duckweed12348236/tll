from decimal import Decimal
from enum import IntEnum
from typing import Any

from tortoise.fields import BigIntField, CharField, DecimalField, JSONField, IntField, IntEnumField, BooleanField, \
    DatetimeField, ForeignKeyField, RESTRICT

from plugins.snowflake.snowflake import Snowflake
from models import Model

snowflake = Snowflake()


class Product(Model):
    """
    商品数据模型

    用于表示商品信息的数据库模型，包含商品的基本属性、价格、库存、封面图片、详细信息等。

    Attributes:
        id (BigInt): 商品唯一标识符，使用雪花算法生成
        name (str): 商品名称，最大长度200字符
        price (Decimal): 商品价格，最多10位数字，其中2位小数
        covers (list): 商品封面图片列表，JSON格式存储
        details (list): 商品详细信息列表，JSON格式存储
        stock (int): 商品库存数量
        per_max_quantity (int): 单次购买最大数量限制
        discontinued (bool): 是否已下架，默认为False
        creation_time (datetime): 商品创建时间，自动记录创建时刻
    """
    id = BigIntField(primary_key=True, default=lambda: snowflake.get_id(), generated=False)
    name = CharField(max_length=200)
    price = DecimalField(max_digits=10, decimal_places=2)
    covers = JSONField(default=list)
    details = JSONField(default=list)
    stock = IntField()
    per_max_quantity = IntField()
    discontinued = BooleanField(default=False)
    creation_time = DatetimeField(auto_now_add=True)


class OrderStatus(IntEnum):
    """
    订单状态枚举类

    定义订单的各种状态，包括未支付、已支付、配送中、已完成、退款中和已退款。

    Attributes:
        UNPAID (int): 未支付状态
        PAID (int): 已支付状态
        DELIVERING (int): 配送中状态
        FINISHED (int): 已完成状态
        REFUNDING (int): 退款中状态
        REFUNDED (int): 已退款状态
    """
    UNPAID = 0
    PAID = 1
    DELIVERING = 2
    FINISHED = 3
    REFUNDING = 4
    REFUNDED = 5


class Order(Model):
    id = BigIntField(primary_key=True, default=lambda: snowflake.get_id(), generated=False)
    status = IntEnumField(OrderStatus, default=OrderStatus.UNPAID)
    quantity = IntField()
    amount = DecimalField(max_digits=10, decimal_places=2)
    creation_time = DatetimeField(auto_now_add=True)
    address = JSONField[dict[str, str | int]]()
    product = JSONField[dict[str, Any]]()
    url = CharField(max_length=200, null=True)
    trade_number = BigIntField(null=True)
    is_deleted = BooleanField(default=False)
    user_id: int
    user = ForeignKeyField("models.User", "orders", RESTRICT)

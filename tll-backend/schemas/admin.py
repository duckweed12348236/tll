from decimal import Decimal
from enum import IntEnum
from typing import Annotated, Self
from datetime import datetime

from schemas import Schema

from pydantic import Field, StringConstraints, model_validator


class ProductIn(Schema):
    """
    产品输入数据模型

    用于创建或更新产品时的请求数据验证。

    Attributes:
        name (str): 产品名称，长度为1-200个字符
        price (Decimal): 产品价格，必须大于0，最多10位数字，其中2位小数
        covers (list[str]): 产品封面图片URL列表，至少包含1个非空字符串
        details (list[str]): 产品详情描述列表，至少包含1个非空字符串
        stock (int): 产品库存数量，必须大于0
        per_max_quantity (int): 单次购买最大数量，必须大于0
    """
    name: str = Field(min_length=1, max_length=200)
    price: Decimal = Field(gt=0, decimal_places=2, max_digits=10)
    covers: list[Annotated[str, StringConstraints(min_length=1)]] = Field(min_length=1)
    details: list[Annotated[str, StringConstraints(min_length=1)]] = Field(min_length=1)
    stock: int = Field(gt=0)
    per_max_quantity: int = Field(gt=0)


class ProductStatusOption(IntEnum):
    ALL = -1
    DELISTED = 0
    LISTED = 1


class ProductQuery(Schema):
    page: int = Field(gt=0)
    size: int = Field(gt=0)
    price_max: Decimal | None = Field(None, decimal_places=2, max_digits=10, gt=0)
    price_min: Decimal | None = Field(None, decimal_places=2, max_digits=10, gt=0)
    stock_max: int | None = Field(None, gt=0)
    stock_min: int | None = Field(None, gt=0)
    name: str | None = Field(None, max_length=200)
    status: ProductStatusOption

    @model_validator(mode="after")
    def validate_self(self) -> Self:
        if self.price_min and self.price_max and self.price_min > self.price_max:
            raise ValueError("价格范围错误")
        if self.stock_min and self.stock_max and self.stock_min > self.stock_max:
            raise ValueError("库存范围错误")
        return self


class OrderStatusOption(IntEnum):
    """
    订单状态枚举类

    定义订单的各种状态选项，用于标识订单在生命周期中的不同阶段。

    Attributes:
        ALL (int): 全部状态，用于查询所有订单
        UNPAID (int): 未支付状态
        PAID (int): 已支付状态
        DELIVERING (int): 配送中状态
        FINISHED (int): 已完成状态
        REFUNDING (int): 退款中状态
        REFUNDED (int): 已退款状态
    """
    ALL = -1
    UNPAID = 0
    PAID = 1
    DELIVERING = 2
    FINISHED = 3
    REFUNDING = 4
    REFUNDED = 5


class OrderQuery(Schema):
    page: int = Field(gt=0)
    size: int = Field(gt=0)
    status: OrderStatusOption
    amount_min: Decimal | None = Field(None, decimal_places=2, max_digits=10, gt=0)
    amount_max: Decimal | None = Field(None, decimal_places=2, max_digits=10, gt=0)
    creation_time_min: datetime | None = None
    creation_time_max: datetime | None = None

    @model_validator(mode="after")
    def validate_self(self) -> Self:
        if self.amount_min and self.amount_max and self.amount_min > self.amount_max:
            raise ValueError("金额范围错误")
        if self.creation_time_min and self.creation_time_max and self.creation_time_min > self.creation_time_max:
            raise ValueError("时间范围错误")
        return self


class DayOption(IntEnum):
    SEVEN_DAYS = 7
    THIRTY_DAYS = 30
    SIXTY_DAYS = 60
    NINETY_DAYS = 90

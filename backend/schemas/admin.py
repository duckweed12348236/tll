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


class SalesStatusOption(IntEnum):
    ALL = -1
    DELISTED = 0
    LISTED = 1


class ProductQuery(Schema):
    """
    产品查询参数的验证模型

    用于产品列表查询时的参数验证，包括分页、价格范围、库存范围和售卖状态等查询条件。

    Attributes:
        page (int): 页码，必须大于0
        size (int): 每页数量，必须大于0
        price_max (Decimal): 最高价格，最多10位数字，其中2位小数
        price_min (Decimal): 最低价格，最多10位数字，其中2位小数
        stock_max (int): 最大库存数量
        stock_min (int): 最小库存数量
        name (str): 产品名称，最大长度200字符
        discontinued (int): 售卖状态，0为在售，1为停售
    """
    page: int = Field(gt=0)
    size: int = Field(gt=0)
    price_max: Decimal = Field(decimal_places=2, max_digits=10)
    price_min: Decimal = Field(decimal_places=2, max_digits=10)
    stock_max: int = Field()
    stock_min: int = Field()
    name: str = Field(max_length=200)
    discontinued: SalesStatusOption

    @model_validator(mode="after")
    def validate_self(self) -> Self:
        if 0 <= self.price_max < self.price_min and self.price_min >= 0:
            raise ValueError("价格范围错误")
        if 0 <= self.stock_max < self.stock_min and self.stock_min >= 0:
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
    """
    订单查询参数验证模型

    用于订单列表查询的参数验证和范围检查。

    Attributes:
        page (int): 页码，必须大于0
        size (int): 每页数量，必须大于0
        status (OrderStatusOption): 订单状态筛选条件
        amount_min (Decimal | None): 最小金额，可选，必须大于0，最多10位数字其中2位小数
        amount_max (Decimal | None): 最大金额，可选，必须大于0，最多10位数字其中2位小数
        creation_time_min (datetime | None): 创建时间起始，可选
        creation_time_max (datetime | None): 创建时间结束，可选
    """
    page: int = Field(gt=0)
    size: int = Field(gt=0)
    status: OrderStatusOption
    amount_min: Decimal | None = Field(None, gt=0, decimal_places=2, max_digits=10)
    amount_max: Decimal | None = Field(None, gt=0, decimal_places=2, max_digits=10)
    creation_time_min: datetime | None = Field(None)
    creation_time_max: datetime | None = Field(None)

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

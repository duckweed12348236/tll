from enum import IntEnum

from pydantic import Field

from schemas import Schema


class OrderOption(IntEnum):
    ALL = -1
    UNPAID = 0
    PAID = 1
    DELIVERING = 2
    FINISHED = 3
    REFUNDING = 4
    REFUNDED = 5


class AddressIn(Schema):
    name: str = Field(min_length=1)
    telephone: str = Field(min_length=11, pattern=r'^1[3-9]\d{9}$')
    region: str = Field(min_length=1)
    detail: str = Field(min_length=1)


class OrderIn(Schema):
    quantity: int = Field(gt=0)
    product_id: int = Field(gt=0)
    address_id: int = Field(gt=0)
    token: str = Field(min_length=1)

from pydantic import Field

from schemas import Schema


class Account(Schema):
    telephone: str = Field(min_length=1)
    code: str = Field(min_length=4, max_length=4)


class AddressIn(Schema):
    name: str = Field(min_length=1)
    telephone: str = Field(min_length=11, pattern=r'^1[3-9]\d{9}$')
    region: str = Field(min_length=1)
    detail: str = Field(min_length=1)


class RefreshToken(Schema):
    value: str = Field(min_length=1)


class Username(Schema):
    value: str = Field(min_length=1)

from pydantic import Field

from schemas import Schema


class Account(Schema):
    telephone: str = Field(min_length=1)
    code: str = Field(min_length=4, max_length=4)


class RefreshToken(Schema):
    value: str = Field(min_length=1)


class Username(Schema):
    value: str = Field(min_length=1)

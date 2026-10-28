from pydantic import BaseModel, Field


class Schema(BaseModel):
    class Config:
        from_attributes = True


class Login(Schema):
    telephone: str = Field(min_length=1)


class RefreshToken(Schema):
    value: str = Field(min_length=1)

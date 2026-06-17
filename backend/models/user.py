import random
import string

from tortoise.fields import BigIntField, CharField, BooleanField, DatetimeField, ReverseRelation, ForeignKeyField

from models import Model
from models.shopping import Order
from plugins.snowflake import Snowflake

snowflake = Snowflake()


class User(Model):
    id = BigIntField(primary_key=True, default=lambda: snowflake.get_id(), generated=False)
    telephone = CharField(max_length=20, unique=True, index=True)
    username = CharField(max_length=30, default=lambda: "".join(random.sample(string.digits, 6)))
    password = CharField(max_length=200, null=True)
    avatar = CharField(max_length=200, null=True)
    active = BooleanField(default=True)
    last_login = DatetimeField(null=True)
    default_address_id: int
    default_address = ForeignKeyField("models.Address", "users", null=True)
    addresses: ReverseRelation["Address"]
    orders: ReverseRelation[Order]


class Address(Model):
    """
    地址模型类，用于存储用户的收货地址信息

    Attributes:
        id (BigIntField): 地址记录的唯一标识符，主键
        name (CharField): 收货人姓名，最大长度100字符
        telephone (CharField): 联系电话，最大长度20字符
        region (CharField): 地区信息，最大长度200字符
        detail (CharField): 详细地址，最大长度200字符
        user_id (int): 关联用户的ID
        user (ForeignKeyField): 外键关联到用户模型，表示该地址所属的用户
    """
    id = BigIntField(primary_key=True)
    name = CharField(max_length=100)
    telephone = CharField(max_length=20)
    region = CharField(max_length=200)
    detail = CharField(max_length=200)
    user_id: int
    user = ForeignKeyField("models.User", "addresses")

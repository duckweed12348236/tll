import random
import string

from tortoise.fields import BigIntField, CharField

from models import Model
from plugins.snowflake import Snowflake

snowflake = Snowflake()


class Identity(Model):
    """
    身份模型，用于承载用户在系统中的名称、头像与默认地址

    Attributes:
        id (BigIntField): 身份唯一标识，使用雪花算法生成
        user_id (BigIntField): 绑定的用户 ID，对应用户服务中的用户
        username (str): 用户在系统中的名称
        avatar (str | None): 用户头像地址
        default_address_id (int | None): 用户默认收货地址 ID
    """
    id = BigIntField(primary_key=True, default=lambda: snowflake.get_id(), generated=False)
    user_id = BigIntField(unique=True)
    username = CharField(max_length=30, default=lambda: "".join(random.sample(string.digits, 6)))
    avatar = CharField(max_length=200, null=True)
    default_address_id = BigIntField(null=True)

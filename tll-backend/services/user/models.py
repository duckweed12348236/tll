from typing import Any

import tortoise
from tortoise.fields import BigIntField, CharField, BooleanField, DatetimeField, ManyToManyRelation

from services.user.utils.snowflake import Snowflake

snowflake = Snowflake()


class Model(tortoise.Model):
    excluded_fields = {"_partial", "_saved_in_db", "_custom_generated_pk", "_await_when_save"}

    def serialize(self) -> dict[str, Any]:
        pairs = {}
        excluded_fields = self.excluded_fields
        for key, value in self.__dict__.items():
            if key in excluded_fields:
                continue
            if key.startswith("_"):
                key = key[1:]

            if isinstance(value, Model):
                pairs[key] = value.serialize()
            elif ((isinstance(value, list) and len(value) > 0 and isinstance(value[0], Model)) or
                  isinstance(value, ManyToManyRelation)):
                pairs[key] = [x.serialize() for x in value]
            else:
                pairs[key] = value
        return pairs


class User(Model):
    """
    用户模型，只承载鉴权相关的身份信息

    Attributes:
        id (BigIntField): 用户唯一标识，使用雪花算法生成
        telephone (str): 手机号，登录账号
        password (str | None): 密码
        active (bool): 是否活跃
        last_login (datetime | None): 上次登录时间
    """
    id = BigIntField(primary_key=True, default=lambda: snowflake.get_id(), generated=False)
    telephone = CharField(max_length=20, unique=True, index=True)
    password = CharField(max_length=200, null=True)
    active = BooleanField(default=True)
    last_login = DatetimeField(null=True)

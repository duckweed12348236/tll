from tortoise.fields import BigIntField, CharField

from models import Model
from plugins.snowflake import Snowflake

snowflake = Snowflake()


class Admin(Model):
    id = BigIntField(primary_key=True, default=snowflake.get_id, generated=False)
    username = CharField(unique=True, max_length=200)
    password = CharField(max_length=200)

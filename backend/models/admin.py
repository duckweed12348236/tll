from tortoise.fields import BigIntField, CharField, UUIDField

from models import Model
from plugins.snowflake.snowflake import Snowflake

snowflake = Snowflake()

class Admin(Model):
    id = BigIntField(primary_key=True, default=snowflake.get_id, generated=False)
    username = UUIDField(unique=True)
    password = CharField(max_length=200)


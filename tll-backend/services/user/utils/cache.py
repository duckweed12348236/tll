from abc import ABC
from datetime import datetime
from typing import Any, Self

from aredis_om import Field, JsonModel, Migrator, NotFoundError, get_redis_connection
from redis.asyncio.client import Pipeline, Redis

from services.user.config import REDIS_URL

redis: Redis = get_redis_connection(url=REDIS_URL)


class Cache(JsonModel, ABC):
    class Meta:
        database = redis

    @classmethod
    def create_pipeline(cls) -> Pipeline:
        return cls.db().pipeline()


class UserInfo(Cache, index=True):
    id: int = Field(index=True, primary_key=True)
    telephone: str
    password: str | None = None
    active: bool = True
    last_login: datetime | None = None

    class Meta:
        database = redis
        model_key_prefix = "user"

    @classmethod
    async def save_user(cls, key: int | None = None, **kwargs: Any) -> Self | None:
        if not key:
            instance = cls(**kwargs)
            pipeline = cls.create_pipeline()
            await instance.save(pipeline)
            await instance.expire(7 * 24 * 60 * 60, pipeline)
            await pipeline.execute()
            return instance
        try:
            instance = await cls.find(cls.id == key).first()
        except NotFoundError:
            return None
        await instance.update(**kwargs)
        return instance


async def migrate() -> None:
    migrator = Migrator()
    await migrator.run()

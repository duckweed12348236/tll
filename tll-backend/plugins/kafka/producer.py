from typing import Any

from aiokafka import AIOKafkaProducer

from config import KAFKA_URL
from plugins import Plugin
from plugins.json import dump


class KafkaProducer(Plugin):
    def __init__(self) -> None:
        self.producer = None

    async def send(self, topic: str, value: Any) -> None:
        await self.producer.send(topic, value)

    async def init(self) -> None:
        self.producer = AIOKafkaProducer(
            bootstrap_servers=KAFKA_URL,
            value_serializer=dump
        )
        await self.producer.start()

    async def close(self) -> None:
        await self.producer.stop()

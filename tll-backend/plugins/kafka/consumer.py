import asyncio
import signal
from multiprocessing import Event, Process
from typing import Any

from aiokafka import AIOKafkaConsumer
from loguru import logger
from tortoise import Tortoise

from config import KAFKA_URL, TORTOISE_ORM_CONFIG
from plugins.json import load
from plugins.kafka.tasks import handlers

order_topics = ["create_orders", "pay_orders", "refund_orders", "delete_orders"]


async def poll(stop_event: Any, topics: list[str]) -> None:
    await Tortoise.init(config=TORTOISE_ORM_CONFIG)
    consumer = AIOKafkaConsumer(
        *topics,
        bootstrap_servers=KAFKA_URL,
        value_deserializer=load,
        auto_offset_reset="latest",
        enable_auto_commit=False,
        group_id="orders",
    )
    await consumer.start()

    while not stop_event.is_set():
        records = await consumer.getmany(timeout_ms=5000, max_records=1000)
        if not records:
            continue
        logger.info(records)

        offsets = {}
        for topic_partition, messages in records.items():
            handler = handlers.get(topic_partition.topic)
            if not handler:
                logger.warning(f"no task registered for topic {topic_partition.topic}")
                continue
            await handler([message.value for message in messages if message.value])
            offsets[topic_partition] = messages[-1].offset + 1
        if offsets:
            await consumer.commit(offsets)

    await Tortoise.close_connections()
    await consumer.stop()


def create_loop(stop_event: Any, topics: list[str]) -> None:
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    try:
        asyncio.run(poll(stop_event, topics))
    except KeyboardInterrupt:
        pass


class KafkaConsumer:
    """订单消息消费者，由应用生命周期显式拉起与关闭"""

    def __init__(self) -> None:
        self.stop_event = Event()
        self.topics = order_topics
        self.worker = Process(
            target=create_loop,
            args=(self.stop_event, self.topics)
        )

    async def start(self) -> None:
        self.worker.start()
        logger.info(f"kafka consumer started, pid={self.worker.pid}")
        return None

    async def close(self) -> None:
        self.stop_event.set()
        await asyncio.to_thread(self.worker.join, 10)
        if self.worker.is_alive():
            self.worker.terminate()
        logger.info("kafka consumer stopped")
        return None

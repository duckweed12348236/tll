import asyncio
from multiprocessing import Process, Event
from typing import Any

from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from tortoise import Tortoise
from tortoise.transactions import in_transaction
from loguru import logger

from config import KAFKA_URL, TORTOISE_ORM_CONFIG
from plugins import Plugin
from plugins.json import serialize, deserialize
from models.shopping import Order, Product


class KafkaProducer(Plugin):
    def __init__(self) -> None:
        self.producer = None

    async def send(self, topic: str, value: Any) -> None:
        await self.producer.send(topic, value)

    async def init(self) -> None:
        self.producer = AIOKafkaProducer(
            bootstrap_servers=KAFKA_URL,
            value_serializer=serialize
        )
        await self.producer.start()

    async def close(self) -> None:
        await self.producer.stop()


async def poll(stop_event, topics: list[str]) -> None:
    await Tortoise.init(config=TORTOISE_ORM_CONFIG)
    consumer = AIOKafkaConsumer(
        *topics,
        bootstrap_servers=KAFKA_URL,
        value_deserializer=deserialize,
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
            topic = topic_partition.topic
            values = [message.value for message in messages]
            match topic:
                case "create_orders":
                    async with in_transaction():
                        products = await Product.select_for_update().only("id", "stock").in_bulk(
                            {value["product_id"] for value in values if value is not None},
                            "id"
                        )
                        for value in values:
                            if not value:
                                continue
                            product_id = value.pop("product_id")
                            quantity = value["quantity"]
                            product = products[product_id]
                            stock = product.stock
                            if stock < 0 or stock < quantity:
                                continue
                            product.stock -= quantity
                        await Product.bulk_update(products.values(), ["stock"])
                        await Order.bulk_create(
                            [Order(**value) for value in values if value is not None],
                            ignore_conflicts=True
                        )

                case "update_orders":
                    async with in_transaction():
                        products = await Product.select_for_update().only("id", "stock").in_bulk(
                            {value["product_id"] for value in values if value is not None},
                            "id"
                        )
                        orders = await Order.select_for_update().in_bulk(
                            {value["id"] for value in values if value is not None},
                            "id"
                        )
                        for value in values:
                            if not value:
                                continue
                            product_id = value.pop("product_id", None)
                            if product_id:
                                quantity = value["quantity"]
                                product = products[product_id]
                                stock = product.stock
                                if stock < 0 or stock < quantity:
                                    continue
                                product.stock += quantity
                            order_id = value["id"]
                            if order_id not in orders:
                                orders[order_id] = Order(**value)
                                continue
                            order = orders[order_id]
                            order.status = value["status"]
                            order.trade_number = value["trade_number"]
                        await Order.bulk_create(
                            orders.values(),
                            on_conflict=["id"],
                            update_fields=["status", "trade_number"]
                        )

                case "delete_orders":
                    async with in_transaction():
                        orders = await Order.select_for_update().in_bulk(
                            {value["id"] for value in values if value is not None},
                            "id"
                        )
                        for value in values:
                            if not value:
                                continue
                            order_id = value["id"]
                            if order_id not in orders:
                                orders[order_id] = Order(**value)
                                continue
                            order = orders[order_id]
                            order.is_deleted = True
                        await Order.bulk_create(
                            orders.values(),
                            on_conflict=["id"],
                            update_fields=["is_deleted"]
                        )

            offsets[topic_partition] = messages[-1].offset + 1
        if offsets:
            await consumer.commit(offsets)

    await Tortoise.close_connections()
    await consumer.stop()


def create_loop(stop_event, topics: list[str]):
    asyncio.run(poll(stop_event, topics))


class KafkaConsumer(Plugin):
    def __init__(self) -> None:
        self.stop_event = Event()
        self.child_signal = Event()
        self.topics = ["create_orders", "update_orders", "delete_orders"]
        self.worker = Process(
            target=create_loop,
            args=(self.stop_event, self.topics)
        )

    async def init(self) -> None:
        self.worker.start()

    async def close(self) -> None:
        self.stop_event.set()

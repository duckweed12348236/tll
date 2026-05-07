import asyncio
from threading import Thread
from typing import Any
from time import sleep

from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
import orjson
from tortoise import Tortoise
from tortoise.transactions import in_transaction
from loguru import logger

from config import KAFKA_URL, TORTOISE_ORM_CONFIG
from plugins import Plugin
from models.shopping import Order, Product


class KafkaProducer(Plugin):
    def __init__(self) -> None:
        self.producer = None

    async def send(self, topic: str, value: Any) -> None:
        await self.producer.send(topic, value)

    async def init(self) -> None:
        self.producer = AIOKafkaProducer(
            bootstrap_servers=KAFKA_URL,
            value_serializer=lambda value: orjson.dumps(value),
        )
        await self.producer.start()

    async def close(self) -> None:
        await self.producer.stop()


class KafkaConsumer(Plugin):
    def __init__(self) -> None:
        self.stop_signal = False
        self.worker = Thread(target=lambda: asyncio.run(self.consume()), daemon=True)
        self.topics = ["crate_orders", "delete_orders"]

    async def consume(self) -> None:
        await Tortoise.init(config=TORTOISE_ORM_CONFIG)
        producer = AIOKafkaProducer(
            bootstrap_servers=KAFKA_URL,
            value_serializer=lambda value: orjson.dumps(value),
        )
        await producer.start()
        consumer = AIOKafkaConsumer(
            *self.topics,
            bootstrap_servers=KAFKA_URL,
            value_deserializer=lambda value: orjson.loads(value),
            auto_offset_reset="latest",
            enable_auto_commit=False
        )
        await consumer.start()
        while not self.stop_signal:
            records = await consumer.getmany(timeout_ms=5000, max_records=200)
            if not records:
                continue
            offsets = {}
            for topic_partition, messages in records.items():
                topic = topic_partition.topic
                values = [message.value for message in messages]
                logger.info(values)
                match topic:
                    case "create_orders":
                        orders = [Order(**value) for value in values]
                        await Order.bulk_create(orders)

                    case "update_orders":
                        retries = []
                        async with in_transaction():
                            orders = await Order.select_for_update().in_bulk([value["id"] for value in values], "id")
                            for value in values:
                                order_id = value["id"]
                                if order_id in orders:
                                    order = orders[order_id]
                                    order.status = value["status"]
                                    order.trade_number = value["trade_number"]
                                else:
                                    retries.append(producer.send("update_orders", value))
                            await Order.bulk_update(orders.values(), ["status", "trade_number"])
                        if retries:
                            await asyncio.gather(*retries)

                    case "delete_orders":
                        retries = []
                        async with in_transaction():
                            orders = await Order.select_for_update().in_bulk(values, "id")
                            for value in values:
                                if value in orders:
                                    order = orders[value]
                                    order.is_deleted = True
                                else:
                                    retries.append(producer.send("delete_orders", value))
                            await Order.bulk_update(orders.values(), ["is_deleted"])
                        if retries:
                            await asyncio.gather(*retries)

                    case "increase_stocks":
                        async with in_transaction():
                            products = await Product.select_for_update().in_bulk(
                                [value["id"] for value in values], "id")
                            for value in values:
                                product_id = value["id"]
                                quantity = value["quantity"]
                                product = products[product_id]
                                product.stock += quantity
                            await Product.bulk_update(products.values(), ["stock"])

                    case "decrease_stocks":
                        async with in_transaction():
                            products = await Product.select_for_update().in_bulk(
                                [value["id"] for value in values], "id")
                            for value in values:
                                product_id = value["id"]
                                quantity = value["quantity"]
                                product = products[product_id]
                                stock = product.stock
                                if stock < 1 or stock < quantity:
                                    logger.info(f"商品{product_id}库存不足，当前库存{stock}，需要{quantity}")
                                    continue
                                product.stock = stock - quantity
                            await Product.bulk_update(products.values(), ["stock"])

                offsets[topic_partition] = messages[-1].offset + 1
            if offsets:
                await consumer.commit(offsets)

        await Tortoise.close_connections()
        await producer.stop()
        await consumer.stop()

    async def init(self) -> None:
        self.worker.start()

    async def close(self) -> None:
        self.stop_signal = True
        sleep(1)
        self.worker.join()

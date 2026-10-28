import asyncio
import socket
from typing import Any
from uuid import uuid4

from consul import Check, Consul
from loguru import logger

from config import CONSULT_HOST, CONSULT_PORT


def local_address() -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        try:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
        except OSError:
            return "127.0.0.1"


def tcp_check(address: str, port: int) -> dict[str, Any]:
    return Check.tcp(address, port, "5s", deregister="1m")


class ConsulRegistry:
    """基于 Consul 的服务注册与发现，服务地址与端口均在运行时确定"""

    def __init__(self, host: str = CONSULT_HOST, port: int = CONSULT_PORT) -> None:
        self.client = Consul(host=host, port=port)

    async def register(self, name: str, address: str, port: int) -> str:
        service_id = f"{name}-{uuid4().hex}"
        await asyncio.to_thread(
            self.client.agent.service.register,
            name=name,
            service_id=service_id,
            address=address,
            port=port,
            check=tcp_check(address, port)
        )
        logger.info(f"registered service {name} at {address}:{port}, id={service_id}")
        return service_id

    async def deregister(self, service_id: str) -> None:
        await asyncio.to_thread(self.client.agent.service.deregister, service_id)
        logger.info(f"deregistered service {service_id}")

    async def resolve(self, name: str) -> list[tuple[str, int]]:
        _, nodes = await asyncio.to_thread(self.client.health.service, name, passing=True)
        endpoints = {
            (node["Service"]["Address"], node["Service"]["Port"])
            for node in nodes
            if node["Service"]["Address"] and node["Service"]["Port"]
        }
        return sorted(endpoints)

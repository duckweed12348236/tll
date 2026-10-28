import asyncio
import signal
from multiprocessing import Process
from typing import Any

from celery import Celery
from celery.apps.worker import Worker
from loguru import logger

from config import REDIS_URL
from plugins import Plugin
from plugins.celery.tasks import close_worker

celery_includes = ["plugins.celery.tasks"]
celery_config = {
    "task_serializer": "json",
    "result_serializer": "json",
    "accept_content": ["json"],
    "result_expires": 600,
    "timezone": "Asia/Shanghai",
    "enable_utc": True,
}


def create_app(name: str) -> Celery:
    app = Celery(name, broker=REDIS_URL, backend=REDIS_URL, include=celery_includes)
    app.conf.update(**celery_config)
    return app


app = create_app("tll")
app.set_default()


def run_worker() -> None:
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    worker = Worker(app=create_app("tll-worker"), pool="solo", loglevel="INFO", without_gossip=True)
    try:
        worker.start()
    except KeyboardInterrupt:
        pass
    finally:
        close_worker()


class CeleryClient(Plugin):
    """任务发布端，用于向 Celery 队列投递任务"""

    def __init__(self) -> None:
        self.app = app

    async def send(self, name: str, *args: Any, **kwargs: Any) -> Any:
        return await asyncio.to_thread(self.app.send_task, name, args=args, kwargs=kwargs)

    async def init(self) -> None:
        logger.info(f"celery client is ready, broker={REDIS_URL}")
        return None

    async def close(self) -> None:
        self.app.close()
        logger.info("celery client closed")
        return None


class CeleryProcess:
    """任务消费端，由应用生命周期显式拉起与关闭"""

    def __init__(self) -> None:
        self.worker = Process(target=run_worker)

    async def start(self) -> None:
        self.worker.start()
        logger.info(f"celery worker started, pid={self.worker.pid}")
        return None

    async def close(self) -> None:
        if self.worker.is_alive():
            self.worker.terminate()
        await asyncio.to_thread(self.worker.join, 10)
        logger.info("celery worker stopped")
        return None


from __future__ import annotations

import asyncio
import json
from typing import Any

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.errors import KafkaError

from shared import topics as T
from shared.config import settings
from shared.logging import q, setup_logging

log = setup_logging("kafka")


def _dumps(obj: Any) -> bytes:
    return json.dumps(obj, default=str, ensure_ascii=False).encode("utf-8")


def _loads(data: bytes) -> dict[str, Any]:
    return json.loads(data.decode("utf-8"))


class Producer:

    def __init__(self, bootstrap: str | None = None) -> None:
        self._bootstrap = bootstrap or settings.kafka_bootstrap_servers
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        if self._producer is not None:
            return
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self._bootstrap,
            client_id=settings.kafka_client_id,
            acks="all",
            enable_idempotence=True,
            value_serializer=_dumps,
        )
        await self._producer.start()
        log.info(q("kafka producer started"))

    async def stop(self) -> None:
        if self._producer is not None:
            await self._producer.stop()
            self._producer = None

    async def send(self, topic: str, value: Any, key: str | None = None) -> None:
        if self._producer is None:
            await self.start()
        assert self._producer is not None
        await self._producer.send_and_wait(topic, value=value, key=key.encode() if key else None)

    async def send_raw(self, topic: str, value: dict[str, Any], key: str | None = None) -> None:
        await self.send(topic, value, key)


class Consumer:

    def __init__(self, topic: str, group: str, bootstrap: str | None = None) -> None:
        self.topic = topic
        self.group = group
        self._bootstrap = bootstrap or settings.kafka_bootstrap_servers
        self._consumer: AIOKafkaConsumer | None = None

    async def start(self) -> None:
        if self._consumer is not None:
            return
        self._consumer = AIOKafkaConsumer(
            self.topic,
            bootstrap_servers=self._bootstrap,
            group_id=self.group,
            client_id=f"{settings.kafka_client_id}-{self.group}",
            enable_auto_commit=True,
            auto_offset_reset="earliest",
            value_deserializer=_loads,
            max_poll_interval_ms=300000,
        )
        await self._consumer.start()
        log.info(q(f"consumer started topic={self.topic} group={self.group}"))

    async def stop(self) -> None:
        if self._consumer is not None:
            await self._consumer.stop()
            self._consumer = None

    async def getone(self) -> dict[str, Any]:
        assert self._consumer is not None
        msg = await self._consumer.getone()
        return msg.value

    async def __aiter__(self):  # pragma: no cover - convenience
        assert self._consumer is not None
        async for msg in self._consumer:
            yield msg.value


async def ensure_topics(bootstrap: str | None = None, retries: int = 30) -> None:
    from aiokafka.admin import AIOKafkaAdminClient, NewTopic

    bootstrap = bootstrap or settings.kafka_bootstrap_servers
    admin = AIOKafkaAdminClient(bootstrap_servers=bootstrap)
    try:
        for _ in range(retries):
            try:
                await admin.start()
                break
            except KafkaError:
                await asyncio.sleep(1)
        else:
            log.warning(q("kafka admin could not connect; topics assumed pre-created"))
            return
        existing = set(await admin.list_topics())
        new_topics = [
            NewTopic(name=t, num_partitions=T.PARTITIONS, replication_factor=T.REPLICATION)
            for t in T.ALL_TOPICS
            if t not in existing
        ]
        if new_topics:
            await admin.create_topics(new_topics, validate_only=False)
            log.info(q(f"created topics: {[t.name for t in new_topics]}"))
    finally:
        await admin.close()


async def ensure_topic(topic: str, bootstrap: str | None = None) -> None:
    from aiokafka.admin import AIOKafkaAdminClient, NewTopic

    bootstrap = bootstrap or settings.kafka_bootstrap_servers
    admin = AIOKafkaAdminClient(bootstrap_servers=bootstrap)
    try:
        await admin.start()
        existing = set(await admin.list_topics())
        if topic not in existing:
            await admin.create_topics(
                [NewTopic(name=topic, num_partitions=1, replication_factor=1)]
            )
    finally:
        await admin.close()

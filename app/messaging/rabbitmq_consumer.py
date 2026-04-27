"""AMQP consumer that fans out every incoming event to audit + analytics."""

import asyncio
import json
from typing import Any

import aio_pika
from aio_pika import ExchangeType, IncomingMessage

from app.core.config import settings
from app.core.logging import get_logger
from app.domain.models import EventEnvelope
from app.messaging.amqp_retry import connect_robust_when_ready
from app.services.audit_handler import DuplicateEventError, handle_event

logger = get_logger(__name__)

QUORUM_QUEUE_ARGS: dict[str, str] = {"x-queue-type": "quorum"}


class AnalyticsConsumer:
    """Durable consumer bound to ``events.topic`` with configurable binding keys.

    Binding key defaults to ``#`` so the queue receives every published event,
    making this service a true fan-out consumer independent of notification flow.
    """

    def __init__(self) -> None:
        self._connection: aio_pika.abc.AbstractRobustConnection | None = None
        self._channel: aio_pika.abc.AbstractChannel | None = None

    async def start(self) -> None:
        """Connect, declare topology, and block consuming messages."""
        self._connection = await connect_robust_when_ready(
            settings.rabbitmq_url,
            logger=logger,
        )
        self._channel = await self._connection.channel()
        await self._channel.set_qos(prefetch_count=settings.rabbitmq_prefetch)

        exchange = await self._channel.declare_exchange(
            settings.rabbitmq_events_exchange,
            ExchangeType.TOPIC,
            durable=True,
        )

        queue = await self._channel.declare_queue(
            settings.rabbitmq_queue,
            durable=True,
            arguments=QUORUM_QUEUE_ARGS,
        )

        for binding_key in settings.binding_keys:
            await queue.bind(exchange, routing_key=binding_key)

        logger.info(
            "Analytics consumer started",
            extra={
                "queue": settings.rabbitmq_queue,
                "bindings": settings.binding_keys,
                "prefetch": settings.rabbitmq_prefetch,
            },
        )

        await queue.consume(self._process_message)
        await asyncio.Future()  # block until cancelled

    async def close(self) -> None:
        if self._connection is not None:
            await self._connection.close()

    async def _process_message(self, message: IncomingMessage) -> None:
        try:
            payload = self._decode_payload(message)
            event = EventEnvelope.model_validate(payload)

            handle_event(event)

            await message.ack()

            logger.info(
                "Analytics message acknowledged",
                extra={
                    "event_id": str(event.event_id),
                    "event_type": event.event_type,
                },
            )

        except DuplicateEventError as exc:
            logger.warning("Duplicate event skipped", extra={"error": str(exc)})
            await message.ack()  # safe to discard — already processed

        except Exception as exc:
            logger.exception(
                "Analytics processing failed — message rejected",
                extra={"error": str(exc)},
            )
            await message.nack(requeue=False)

    @staticmethod
    def _decode_payload(message: IncomingMessage) -> dict[str, Any]:
        return json.loads(message.body.decode("utf-8"))

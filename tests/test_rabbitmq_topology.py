"""Topology tests: ``analytics.events`` is declared as a quorum queue."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from unittest.mock import AsyncMock, patch

from app.messaging.rabbitmq_consumer import QUORUM_QUEUE_ARGS, AnalyticsConsumer


def test_quorum_queue_args_is_canonical_literal() -> None:
    assert QUORUM_QUEUE_ARGS == {"x-queue-type": "quorum"}


def test_start_declares_analytics_queue_as_quorum() -> None:
    asyncio.run(_start_declares_analytics_queue_as_quorum())


async def _start_declares_analytics_queue_as_quorum() -> None:
    channel = AsyncMock()
    channel.declare_exchange = AsyncMock(return_value=AsyncMock())

    declared_queue = AsyncMock()
    declared_queue.bind = AsyncMock()
    declared_queue.consume = AsyncMock()
    channel.declare_queue = AsyncMock(return_value=declared_queue)

    connection = AsyncMock()
    connection.channel = AsyncMock(return_value=channel)

    consumer = AnalyticsConsumer()

    with (
        patch(
            "app.messaging.rabbitmq_consumer.connect_robust_when_ready",
            AsyncMock(return_value=connection),
        ),
        suppress(asyncio.TimeoutError),
    ):
        # ``start()`` blocks on ``await asyncio.Future()`` after setup —
        # break out via a short timeout once topology is declared.
        await asyncio.wait_for(consumer.start(), timeout=0.1)

    queue_calls = channel.declare_queue.call_args_list
    assert len(queue_calls) == 1, (
        f"Expected exactly one declare_queue call, got {len(queue_calls)}: "
        f"{queue_calls}"
    )
    assert queue_calls[0].kwargs["arguments"] == QUORUM_QUEUE_ARGS

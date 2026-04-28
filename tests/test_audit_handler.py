"""Unit tests for audit_handler: orchestration, idempotency, error flow."""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Coroutine
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.domain.models import EventEnvelope
from app.services import audit_handler as ah
from app.services.audit_handler import handle_event

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_event(event_type: str = "user.registered") -> EventEnvelope:
    return EventEnvelope(
        event_id=uuid.uuid4(),
        event_type=event_type,
        source="frontend",
        occurred_at=datetime.now(tz=UTC),
        payload={},
    )


def _run(coro: Coroutine[Any, Any, None]) -> None:
    asyncio.run(coro)


@pytest.fixture(autouse=True)
def mock_idempotency_store(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    store = MagicMock()
    store.try_start_processing = AsyncMock(return_value=True)
    store.mark_processed = AsyncMock()
    store.release_processing = AsyncMock()
    monkeypatch.setattr(ah, "idempotency_store", store)
    return store


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_handle_event_calls_audit_repository(
    monkeypatch: pytest.MonkeyPatch,
    mock_idempotency_store: MagicMock,
) -> None:
    mock_repo = MagicMock()
    monkeypatch.setattr(ah, "audit_repository", mock_repo)
    monkeypatch.setattr(ah, "analytics_service", MagicMock())

    event = _make_event()
    _run(handle_event(event))

    mock_repo.append_event.assert_called_once_with(event)
    mock_idempotency_store.mark_processed.assert_awaited_once()


def test_handle_event_calls_analytics_service(
    monkeypatch: pytest.MonkeyPatch,
    mock_idempotency_store: MagicMock,
) -> None:
    mock_analytics = MagicMock()
    monkeypatch.setattr(ah, "audit_repository", MagicMock())
    monkeypatch.setattr(ah, "analytics_service", mock_analytics)

    event = _make_event()
    _run(handle_event(event))

    mock_analytics.register_event.assert_called_once_with(event)
    mock_idempotency_store.mark_processed.assert_awaited_once()


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


def test_duplicate_second_try_does_not_call_repository_again(
    monkeypatch: pytest.MonkeyPatch,
    mock_idempotency_store: MagicMock,
) -> None:
    mock_repo = MagicMock()
    monkeypatch.setattr(ah, "audit_repository", mock_repo)
    monkeypatch.setattr(ah, "analytics_service", MagicMock())

    event = _make_event()
    mock_idempotency_store.try_start_processing = AsyncMock(side_effect=[True, False])
    monkeypatch.setattr(ah, "idempotency_store", mock_idempotency_store)

    _run(handle_event(event))
    _run(handle_event(event))

    assert mock_idempotency_store.try_start_processing.await_count == 2
    assert mock_repo.append_event.call_count == 1


def test_different_events_both_processed(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_repo = MagicMock()
    monkeypatch.setattr(ah, "audit_repository", mock_repo)
    monkeypatch.setattr(ah, "analytics_service", MagicMock())

    ev1 = _make_event("user.registered")
    ev2 = _make_event("order.created")
    _run(handle_event(ev1))
    _run(handle_event(ev2))
    assert mock_repo.append_event.call_count == 2


def test_processing_error_releases_key(
    monkeypatch: pytest.MonkeyPatch,
    mock_idempotency_store: MagicMock,
) -> None:
    def boom(_event: EventEnvelope) -> None:
        raise RuntimeError("disk full")

    mock_repo = MagicMock()
    mock_repo.append_event.side_effect = boom
    monkeypatch.setattr(ah, "audit_repository", mock_repo)
    monkeypatch.setattr(ah, "analytics_service", MagicMock())

    event = _make_event()
    with pytest.raises(RuntimeError, match="disk full"):
        _run(handle_event(event))

    mock_idempotency_store.release_processing.assert_awaited_once()
    mock_idempotency_store.mark_processed.assert_not_awaited()

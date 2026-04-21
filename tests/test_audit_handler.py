"""Unit tests for audit_handler: orchestration, idempotency, error flow."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.domain.models import EventEnvelope
from app.services import audit_handler as ah
from app.services.audit_handler import DuplicateEventError, handle_event


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_event(event_type: str = "user.registered") -> EventEnvelope:
    return EventEnvelope(
        event_id=uuid.uuid4(),
        event_type=event_type,
        source="frontend",
        occurred_at=datetime.now(tz=timezone.utc),
        payload={},
    )


@pytest.fixture(autouse=True)
def _clear_processed() -> Iterator[None]:
    """Isolate tests: wipe the deduplication set before and after each test."""
    ah.processed_event_ids.clear()
    yield
    ah.processed_event_ids.clear()


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_handle_event_calls_audit_repository(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_repo = MagicMock()
    monkeypatch.setattr(ah, "audit_repository", mock_repo)
    monkeypatch.setattr(ah, "analytics_service", MagicMock())

    event = _make_event()
    handle_event(event)

    mock_repo.append_event.assert_called_once_with(event)


def test_handle_event_calls_analytics_service(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_analytics = MagicMock()
    monkeypatch.setattr(ah, "audit_repository", MagicMock())
    monkeypatch.setattr(ah, "analytics_service", mock_analytics)

    event = _make_event()
    handle_event(event)

    mock_analytics.register_event.assert_called_once_with(event)


def test_handle_event_adds_to_processed_set() -> None:
    with (
        patch.object(ah, "audit_repository"),
        patch.object(ah, "analytics_service"),
    ):
        event = _make_event()
        handle_event(event)
        assert str(event.event_id) in ah.processed_event_ids


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


def test_duplicate_event_raises_duplicate_error() -> None:
    with (
        patch.object(ah, "audit_repository"),
        patch.object(ah, "analytics_service"),
    ):
        event = _make_event()
        handle_event(event)

        with pytest.raises(DuplicateEventError, match=str(event.event_id)):
            handle_event(event)


def test_duplicate_event_does_not_call_repository_again(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_repo = MagicMock()
    monkeypatch.setattr(ah, "audit_repository", mock_repo)
    monkeypatch.setattr(ah, "analytics_service", MagicMock())

    event = _make_event()
    handle_event(event)

    with pytest.raises(DuplicateEventError):
        handle_event(event)

    assert mock_repo.append_event.call_count == 1


def test_different_events_both_processed() -> None:
    with (
        patch.object(ah, "audit_repository") as mock_repo,
        patch.object(ah, "analytics_service"),
    ):
        ev1 = _make_event("user.registered")
        ev2 = _make_event("order.created")
        handle_event(ev1)
        handle_event(ev2)
        assert mock_repo.append_event.call_count == 2
        assert len(ah.processed_event_ids) == 2

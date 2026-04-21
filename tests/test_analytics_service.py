"""Unit tests for AnalyticsService counters (no I/O)."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from app.domain.models import EventEnvelope
from app.services.analytics_service import AnalyticsService, _extract_domain

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_event(
    event_type: str = "user.registered",
    source: str = "frontend",
) -> EventEnvelope:
    return EventEnvelope(
        event_id=uuid.uuid4(),
        event_type=event_type,
        source=source,
        occurred_at=datetime.now(tz=UTC),
        payload={},
    )


@pytest.fixture
def svc() -> Iterator[AnalyticsService]:
    """Fresh AnalyticsService instance per test."""
    yield AnalyticsService()


# ---------------------------------------------------------------------------
# _extract_domain helper
# ---------------------------------------------------------------------------


def test_extract_domain_standard() -> None:
    assert _extract_domain("user.registered") == "user"


def test_extract_domain_multi_segment() -> None:
    assert _extract_domain("payment.card.failed") == "payment"


def test_extract_domain_no_dot() -> None:
    assert _extract_domain("ping") == "ping"


# ---------------------------------------------------------------------------
# Counter increments
# ---------------------------------------------------------------------------


def test_total_counter_increments(svc: AnalyticsService) -> None:
    svc.register_event(_make_event())
    assert svc.snapshot()["events.total"] == 1


def test_total_counter_accumulates(svc: AnalyticsService) -> None:
    for _ in range(5):
        svc.register_event(_make_event())
    assert svc.snapshot()["events.total"] == 5


def test_by_type_counter(svc: AnalyticsService) -> None:
    svc.register_event(_make_event("order.created"))
    svc.register_event(_make_event("order.created"))
    svc.register_event(_make_event("user.registered"))
    snap = svc.snapshot()
    assert snap["events.by_type.order.created"] == 2
    assert snap["events.by_type.user.registered"] == 1


def test_by_source_counter(svc: AnalyticsService) -> None:
    svc.register_event(_make_event(source="checkout-api"))
    svc.register_event(_make_event(source="checkout-api"))
    svc.register_event(_make_event(source="frontend"))
    snap = svc.snapshot()
    assert snap["events.by_source.checkout-api"] == 2
    assert snap["events.by_source.frontend"] == 1


# ---------------------------------------------------------------------------
# Mini-challenge A: by_domain counters
# ---------------------------------------------------------------------------


def test_by_domain_counter_user(svc: AnalyticsService) -> None:
    svc.register_event(_make_event("user.registered"))
    svc.register_event(_make_event("user.deleted"))
    assert svc.snapshot()["events.by_domain.user"] == 2


def test_by_domain_counter_multiple_domains(svc: AnalyticsService) -> None:
    svc.register_event(_make_event("order.created"))
    svc.register_event(_make_event("payment.failed"))
    svc.register_event(_make_event("user.registered"))
    snap = svc.snapshot()
    assert snap["events.by_domain.order"] == 1
    assert snap["events.by_domain.payment"] == 1
    assert snap["events.by_domain.user"] == 1


def test_by_domain_counter_same_domain(svc: AnalyticsService) -> None:
    for _ in range(3):
        svc.register_event(_make_event("payment.failed"))
    assert svc.snapshot()["events.by_domain.payment"] == 3


# ---------------------------------------------------------------------------
# Mini-challenge B: count_by_type
# ---------------------------------------------------------------------------


def test_count_by_type_known_type(svc: AnalyticsService) -> None:
    svc.register_event(_make_event("order.created"))
    svc.register_event(_make_event("order.created"))
    assert svc.count_by_type("order.created") == 2


def test_count_by_type_unknown_type_returns_zero(svc: AnalyticsService) -> None:
    assert svc.count_by_type("no.such.event") == 0


def test_count_by_type_does_not_affect_other_counters(svc: AnalyticsService) -> None:
    svc.register_event(_make_event("user.registered"))
    _ = svc.count_by_type("user.registered")
    assert svc.snapshot()["events.total"] == 1


# ---------------------------------------------------------------------------
# snapshot
# ---------------------------------------------------------------------------


def test_snapshot_returns_copy(svc: AnalyticsService) -> None:
    svc.register_event(_make_event())
    snap = svc.snapshot()
    snap["events.total"] = 999  # mutate the copy
    assert svc.snapshot()["events.total"] == 1  # original untouched


def test_snapshot_empty_on_fresh_service(svc: AnalyticsService) -> None:
    assert svc.snapshot() == {}

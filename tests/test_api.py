"""Integration tests for HTTP endpoints (no AMQP, no file I/O)."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from app.domain.models import EventEnvelope
from app.services import analytics_service as _as_module
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _fresh_analytics() -> Iterator[None]:
    """Reset the module-level analytics_service singleton between tests."""
    _as_module.analytics_service._counter.clear()
    yield
    _as_module.analytics_service._counter.clear()


def _register(event_type: str, source: str = "test") -> None:
    _as_module.analytics_service.register_event(
        EventEnvelope(
            event_id=uuid.uuid4(),
            event_type=event_type,
            source=source,
            occurred_at=datetime.now(tz=UTC),
            payload={},
        )
    )


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------


def test_health_returns_200(client: TestClient) -> None:
    assert client.get("/health").status_code == 200


def test_health_response_body(client: TestClient) -> None:
    data = client.get("/health").json()
    assert data["status"] == "ok"
    assert data["service"] == "analytics-audit-service"


# ---------------------------------------------------------------------------
# GET /analytics/snapshot
# ---------------------------------------------------------------------------


def test_snapshot_empty_on_fresh_start(client: TestClient) -> None:
    assert client.get("/analytics/snapshot").json() == {}


def test_snapshot_reflects_registered_events(client: TestClient) -> None:
    _register("user.registered")
    _register("user.registered")
    _register("order.created")

    data = client.get("/analytics/snapshot").json()
    assert data["events.total"] == 3
    assert data["events.by_type.user.registered"] == 2
    assert data["events.by_type.order.created"] == 1


def test_snapshot_includes_domain_counters(client: TestClient) -> None:
    _register("payment.failed")
    _register("payment.completed")

    data = client.get("/analytics/snapshot").json()
    assert data["events.by_domain.payment"] == 2


def test_snapshot_includes_source_counters(client: TestClient) -> None:
    _register("user.registered", source="mobile")
    _register("user.registered", source="web")

    data = client.get("/analytics/snapshot").json()
    assert data["events.by_source.mobile"] == 1
    assert data["events.by_source.web"] == 1


# ---------------------------------------------------------------------------
# GET /analytics/by-type/{event_type}  (mini-challenge B)
# ---------------------------------------------------------------------------


def test_by_type_known_event(client: TestClient) -> None:
    _register("order.created")
    _register("order.created")
    _register("order.created")

    data = client.get("/analytics/by-type/order.created").json()
    assert data["event_type"] == "order.created"
    assert data["count"] == 3


def test_by_type_unknown_event_returns_zero(client: TestClient) -> None:
    data = client.get("/analytics/by-type/ghost.event").json()
    assert data["count"] == 0
    assert data["event_type"] == "ghost.event"


def test_by_type_url_with_dot_segments(client: TestClient) -> None:
    _register("payment.card.failed")
    data = client.get("/analytics/by-type/payment.card.failed").json()
    assert data["count"] == 1

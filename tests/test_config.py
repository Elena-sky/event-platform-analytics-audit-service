"""Tests for Settings properties derived from env variables."""

from app.core.config import settings


def test_rabbitmq_url_format() -> None:
    url = settings.rabbitmq_url
    assert url.startswith("amqp://")
    assert "test:test" in url
    assert "localhost:5672" in url
    assert url.endswith("/")


def test_binding_keys_single_wildcard() -> None:
    """test.env sets RABBITMQ_BINDING_KEYS=# — should parse to a one-element list."""
    keys = settings.binding_keys
    assert keys == ["#"]


def test_binding_keys_strips_whitespace(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(settings, "rabbitmq_binding_keys", " user.* , order.* , # ")
    assert settings.binding_keys == ["user.*", "order.*", "#"]


def test_binding_keys_ignores_empty_segments(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(settings, "rabbitmq_binding_keys", "user.*,,order.*")
    assert settings.binding_keys == ["user.*", "order.*"]


def test_audit_log_path_set() -> None:
    assert settings.audit_log_path == "/tmp/test-audit-events.jsonl"

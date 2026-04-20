"""Shared test fixtures and environment bootstrap."""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

# Must run before any ``app`` import because Settings has no in-code defaults.
load_dotenv(Path(__file__).resolve().parent / "test.env", override=True)

import pytest  # noqa: E402
from app.api import app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    """FastAPI TestClient — no lifespan (consumer not started in unit tests)."""
    return TestClient(app)

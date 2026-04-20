"""Domain models shared across the service."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class EventEnvelope(BaseModel):
    """Incoming event as published by gateway-api."""

    event_id: UUID
    event_type: str
    source: str
    occurred_at: datetime
    payload: dict[str, Any]

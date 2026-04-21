"""Lightweight HTTP API: health check and analytics read endpoints.

Mini-challenge B: ``GET /analytics/by-type/{event_type}`` returns the count
for a specific event type.
"""

from fastapi import FastAPI

from app.core.config import settings
from app.services.analytics_service import analytics_service

app = FastAPI(
    title=settings.app_name,
    description=(
        "Audit trail and event analytics for the event-platform. "
        "Consumes all events from the topic exchange and exposes aggregated counters."
    ),
    version="0.1.0",
)

OPENAPI_TAGS_METADATA = [
    {"name": "health", "description": "Process liveness."},
    {"name": "analytics", "description": "In-memory event counters and aggregates."},
]

app.openapi_tags = OPENAPI_TAGS_METADATA


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    """Process liveness — used by load balancers and orchestrators."""
    return {"status": "ok", "service": settings.app_name}


@app.get("/analytics/snapshot", tags=["analytics"])
async def snapshot() -> dict[str, int]:
    """Return all current analytics counters as a flat dictionary."""
    return analytics_service.snapshot()


@app.get("/analytics/by-type/{event_type}", tags=["analytics"])
async def count_by_event_type(event_type: str) -> dict[str, int | str]:
    """Return the count for a specific event type.

    Mini-challenge B — example: ``GET /analytics/by-type/user.registered``
    """
    count = analytics_service.count_by_type(event_type)
    return {"event_type": event_type, "count": count}

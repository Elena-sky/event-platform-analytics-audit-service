"""Orchestrates audit persistence and analytics counter update.

Idempotency: duplicate events (same ``event_id``) are detected and skipped
so that neither the audit log nor the counters are polluted on redelivery.
"""

from app.core.logging import get_logger
from app.domain.models import EventEnvelope
from app.services.analytics_service import analytics_service
from app.storage.audit_repository import audit_repository

logger = get_logger(__name__)

# In-memory deduplication set — sufficient for a single-process service.
# Replace with Redis / DB for multi-replica deployments.
processed_event_ids: set[str] = set()


class DuplicateEventError(Exception):
    """Raised when an event with the same ID has already been processed."""


def handle_event(event: EventEnvelope) -> None:
    """Persist the event to the audit log and update analytics counters.

    Raises:
        DuplicateEventError: if ``event.event_id`` was already processed.
    """
    event_id = str(event.event_id)

    if event_id in processed_event_ids:
        raise DuplicateEventError(f"Duplicate event detected: {event_id}")

    audit_repository.append_event(event)
    analytics_service.register_event(event)

    processed_event_ids.add(event_id)

    logger.info(
        "Audit event processed",
        extra={
            "event_id": event_id,
            "event_type": event.event_type,
        },
    )

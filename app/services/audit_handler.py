"""Orchestrates audit persistence and analytics counter update.

Idempotency: duplicate events (same ``event_id``) are skipped via a shared Redis
store so that neither the audit log nor the counters are polluted on redelivery
or when scaling out consumers.
"""

from app.core.logging import get_logger
from app.domain.models import EventEnvelope
from app.services.analytics_service import analytics_service
from app.services.idempotency_store import idempotency_store
from app.storage.audit_repository import audit_repository

logger = get_logger(__name__)

IDEMPOTENCY_SCOPE = "analytics-audit"


async def handle_event(event: EventEnvelope) -> None:
    """Persist the event to the audit log and update analytics counters."""
    event_id = str(event.event_id)

    acquired = await idempotency_store.try_start_processing(
        event_id=event_id,
        scope=IDEMPOTENCY_SCOPE,
    )
    if not acquired:
        logger.warning(
            "Duplicate analytics/audit event skipped",
            extra={"event_id": event_id, "event_type": event.event_type},
        )
        return

    try:
        audit_repository.append_event(event)
        analytics_service.register_event(event)

        await idempotency_store.mark_processed(
            event_id=event_id,
            scope=IDEMPOTENCY_SCOPE,
        )

        logger.info(
            "Audit event processed",
            extra={
                "event_id": event_id,
                "event_type": event.event_type,
            },
        )
    except Exception:
        await idempotency_store.release_processing(
            event_id=event_id,
            scope=IDEMPOTENCY_SCOPE,
        )
        raise

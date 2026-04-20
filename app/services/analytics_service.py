"""In-memory analytics counters updated on every processed event.

Counters tracked per event:
  - ``events.total``                       total events seen
  - ``events.by_type.<event_type>``        per event type
  - ``events.by_source.<source>``          per publishing source
  - ``events.by_domain.<domain>``          per domain (part before the first dot)

Thread-safe via ``threading.Lock`` because uvicorn may serve HTTP while the
consumer thread updates counters.

Mini-challenge A: ``events.by_domain.*`` counters.
Mini-challenge B: per-type query served from :func:`count_by_type`.
"""

from collections import Counter
from threading import Lock

from app.core.logging import get_logger
from app.domain.models import EventEnvelope

logger = get_logger(__name__)


def _extract_domain(event_type: str) -> str:
    """Return the part before the first dot, e.g. ``user`` from ``user.registered``."""
    return event_type.split(".")[0]


class AnalyticsService:
    def __init__(self) -> None:
        self._counter: Counter[str] = Counter()
        self._lock = Lock()

    def register_event(self, event: EventEnvelope) -> None:
        domain = _extract_domain(event.event_type)

        with self._lock:
            self._counter["events.total"] += 1
            self._counter[f"events.by_type.{event.event_type}"] += 1
            self._counter[f"events.by_source.{event.source}"] += 1
            self._counter[f"events.by_domain.{domain}"] += 1

        logger.info(
            "Analytics counters updated",
            extra={
                "event_id": str(event.event_id),
                "event_type": event.event_type,
                "source": event.source,
                "domain": domain,
            },
        )

    def snapshot(self) -> dict[str, int]:
        """Return a copy of all counters."""
        with self._lock:
            return dict(self._counter)

    def count_by_type(self, event_type: str) -> int:
        """Return the count for a specific event type (0 if never seen)."""
        with self._lock:
            return self._counter[f"events.by_type.{event_type}"]


analytics_service = AnalyticsService()

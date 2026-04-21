"""Append-only audit log backed by a JSON Lines file."""

import json
from pathlib import Path

from app.core.config import settings
from app.core.logging import get_logger
from app.domain.models import EventEnvelope

logger = get_logger(__name__)


class AuditRepository:
    """Writes one JSON record per line to the configured audit log file."""

    def __init__(self, file_path: str) -> None:
        self._path = Path(file_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def append_event(self, event: EventEnvelope) -> None:
        line = json.dumps(event.model_dump(mode="json"), ensure_ascii=False)

        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

        logger.info(
            "Audit event appended",
            extra={
                "event_id": str(event.event_id),
                "event_type": event.event_type,
                "path": str(self._path),
            },
        )


audit_repository = AuditRepository(settings.audit_log_path)

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(slots=True)
class AuditRecord:
    audit_id: str
    event_type: str
    created_at: str
    query_classification: str


def build_audit_record(audit_id: str, event_type: str, query_classification: str) -> AuditRecord:
    return AuditRecord(
        audit_id=audit_id,
        event_type=event_type,
        created_at=datetime.now(UTC).isoformat(),
        query_classification=query_classification,
    )
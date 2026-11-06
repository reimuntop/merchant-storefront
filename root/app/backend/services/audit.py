import json
from typing import Any

from sqlalchemy.orm import Session

from ..database import AuditLog


def record_audit(
    db: Session,
    store_id: int,
    actor_user_id: int,
    entity_type: str,
    action: str,
    entity_id: int | None = None,
    changes: dict[str, Any] | None = None,
) -> AuditLog:
    entry = AuditLog(
        store_id=store_id,
        actor_user_id=actor_user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        changes=json.dumps(changes, default=str) if changes else None,
    )
    db.add(entry)
    return entry

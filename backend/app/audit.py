from sqlalchemy.orm import Session
from .models import IntegrationLog


def log_event(db: Session, source: str, event_type: str, payload: dict | None = None, success: bool = True, message: str = "") -> None:
    db.add(IntegrationLog(source=source, event_type=event_type, payload=payload or {}, success=success, message=message))

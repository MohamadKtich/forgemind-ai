from sqlalchemy.orm import Session
from ..models import Alert, Machine, MachinePrediction, SensorReading
from .predictive import predictive_service


def resolve_machine(db: Session, identifier: str | int) -> Machine | None:
    if isinstance(identifier, int) or str(identifier).isdigit():
        return db.get(Machine, int(identifier))
    return db.query(Machine).filter(Machine.code == str(identifier)).first()


def ingest_and_analyze(db: Session, machine: Machine, payload: dict) -> tuple[SensorReading, MachinePrediction, Alert | None]:
    machine.operating_hours = float(payload.get("operating_hours") or machine.operating_hours + .05)
    machine.tool_wear = float(payload.get("tool_wear") if payload.get("tool_wear") is not None else min(300, machine.tool_wear + .018))
    data = {**payload, "operating_hours": machine.operating_hours, "tool_wear": machine.tool_wear}
    reading = SensorReading(
        machine_id=machine.id,
        **{key: float(data[key]) for key in ["temperature", "vibration", "pressure", "rpm", "torque", "power", "operating_hours", "tool_wear"]},
        source=data.get("source", "api"),
    )
    db.add(reading)
    db.flush()
    result = predictive_service.predict(data, machine.age_years, machine.machine_type)
    prediction = MachinePrediction(
        machine_id=machine.id,
        reading_id=reading.id,
        health_score=result["health_score"],
        failure_probability=result["failure_probability"],
        anomaly_score=result["anomaly_score"],
        remaining_useful_hours=result["remaining_useful_hours"],
        risk_level=result["risk_level"],
        likely_issue=result["likely_issue"],
        recommendation=result["recommended_action"],
        maintenance_priority=result["maintenance_priority"],
        explanation=result["explanation"],
    )
    machine.status = "critical" if result["risk_level"] == "critical" else "at_risk" if result["risk_level"] in {"high", "warning"} else "running"
    db.add(prediction)
    alert = None
    if result["risk_level"] in {"critical", "high"}:
        recent = db.query(Alert).filter(Alert.machine_id == machine.id, Alert.acknowledged == False).order_by(Alert.created_at.desc()).first()
        if not recent or recent.severity != result["risk_level"] or recent.title != f"{machine.code}: {result['likely_issue'].title()}":
            alert = Alert(
                machine_id=machine.id,
                category="predictive_maintenance",
                severity=result["risk_level"],
                title=f"{machine.code}: {result['likely_issue'].title()}",
                message=result["recommended_action"],
            )
            db.add(alert)
    db.commit()
    db.refresh(reading)
    db.refresh(prediction)
    return reading, prediction, alert

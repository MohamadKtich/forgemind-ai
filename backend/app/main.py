from __future__ import annotations
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
import time
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy import func
from sqlalchemy.orm import Session
from .audit import log_event
from .config import get_settings
from .db import Base, SessionLocal, engine, get_db
from .deps import get_current_user, require_roles
from .models import (
    Alert, AppSetting, AssistantConversation, AssistantMessage, DeviceCommand, Factory,
    Inspection, IntegrationLog, Machine, MachinePrediction, MaintenanceRecord,
    ProductionRecord, Report, SensorReading, User,
)
from .schemas import (
    AdminPasswordResetIn, AssistantQuery, ChangePasswordIn, DeviceCommandIn, FactoryCreate, FactoryUpdate,
    LocalRecoveryIn, LoginIn, MachineCreate, MachineOut, MachineUpdate, MaintenanceCreate,
    MaintenanceUpdate, ProductionCreate, ProfileUpdateIn, RegisterIn, ReportGenerateIn,
    SensorReadingIn, SettingUpdateIn, SimulationConfigIn, UserAdminUpdate, UserOut,
)
from .security import create_access_token, hash_password, verify_password
from .seed import seed_database
from .services.assistant import assistant_service
from .services.core import ingest_and_analyze, resolve_machine
from .services.predictive import predictive_service
from .services.quality import quality_service
from .services.reporting import production_csv, save_report
from .services.simulator import simulator

settings = get_settings()
RATE_BUCKETS: dict[str, deque[float]] = defaultdict(deque)


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
    predictive_service.ensure_model()
    Path(settings.storage_dir).mkdir(parents=True, exist_ok=True)
    with SessionLocal() as db:
        seed_database(db)
    try:
        yield
    finally:
        # Release pooled database connections so SQLite files are not locked on Windows.
        engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version="3.0.0",
    description="Agentic industrial intelligence platform for predictive maintenance, visual quality control, production operations, reports, alerts, and device integration.",
    contact={
        "name": "Mohamad Abdullatif Ktich",
        "url": "https://www.linkedin.com/in/mohamad-ktich",
        "email": "ktichmohamad@gmail.com",
    },
    license_info={
        "name": "MIT",
        "identifier": "MIT",
    },
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def basic_rate_limit(request: Request, call_next):
    if request.url.path in {"/api/auth/login", "/api/auth/register"} or request.url.path.startswith("/api/quality/inspect"):
        key = f"{request.client.host if request.client else 'unknown'}:{request.url.path}"
        now = time.time()
        bucket = RATE_BUCKETS[key]
        while bucket and now - bucket[0] > 60:
            bucket.popleft()
        limit = 12 if "auth" in request.url.path else 30
        if len(bucket) >= limit:
            return Response(content='{"detail":"Too many requests. Try again shortly."}', status_code=429, media_type="application/json")
        bucket.append(now)
    return await call_next(request)


def _user_payload(user: User) -> dict:
    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "role": user.role,
        "active": user.active,
        "created_at": user.created_at,
        "last_login_at": user.last_login_at,
    }


def _latest_prediction(db: Session, machine_id: int) -> MachinePrediction | None:
    return db.query(MachinePrediction).filter(MachinePrediction.machine_id == machine_id).order_by(MachinePrediction.created_at.desc()).first()


def _latest_reading(db: Session, machine_id: int) -> SensorReading | None:
    return db.query(SensorReading).filter(SensorReading.machine_id == machine_id).order_by(SensorReading.recorded_at.desc()).first()


def _production_metrics(rows: list[ProductionRecord]) -> dict:
    planned = sum(row.planned for row in rows)
    produced = sum(row.produced for row in rows)
    rejected = sum(row.rejected for row in rows)
    downtime = sum(row.downtime_minutes for row in rows)
    scheduled = sum(row.runtime_minutes + row.downtime_minutes for row in rows)
    availability = max(0.0, 100 - downtime / max(1, scheduled) * 100)
    performance = min(100.0, produced / max(1, planned) * 100)
    quality = max(0.0, 100 - rejected / max(1, produced) * 100)
    oee = availability / 100 * performance / 100 * quality / 100 * 100
    return {
        "planned": planned,
        "produced": produced,
        "rejected": rejected,
        "downtime_minutes": round(downtime, 1),
        "availability": round(availability, 1),
        "performance": round(performance, 1),
        "quality": round(quality, 1),
        "oee": round(oee, 1),
    }


@app.get("/health")
def health():
    return {"status": "ok", "service": settings.app_name, "version": "3.0.0", "environment": settings.environment}


@app.post("/api/auth/register")
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    if not settings.allow_local_registration:
        raise HTTPException(status_code=403, detail="Local registration is disabled")
    email = payload.email.lower().strip()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    user = User(full_name=payload.full_name.strip(), email=email, password_hash=hash_password(payload.password), role="viewer")
    db.add(user)
    log_event(db, "auth", "user_registered", {"email": email})
    db.commit()
    db.refresh(user)
    return {"access_token": create_access_token(user.id, user.role), "token_type": "bearer", "user": _user_payload(user)}


@app.post("/api/auth/login")
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower().strip()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        log_event(db, "auth", "login_failed", {"email": payload.email}, success=False, message="Invalid credentials")
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.active:
        raise HTTPException(status_code=403, detail="This account is inactive")
    user.last_login_at = datetime.now(timezone.utc)
    log_event(db, "auth", "login_success", {"user_id": user.id, "role": user.role})
    db.commit()
    return {"access_token": create_access_token(user.id, user.role), "token_type": "bearer", "user": _user_payload(user)}


@app.get("/api/auth/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@app.patch("/api/auth/profile", response_model=UserOut)
def update_profile(payload: ProfileUpdateIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    user.full_name = payload.full_name.strip()
    log_event(db, "auth", "profile_updated", {"user_id": user.id})
    db.commit()
    db.refresh(user)
    return user


@app.post("/api/auth/change-password")
def change_password(payload: ChangePasswordIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if payload.current_password == payload.new_password:
        raise HTTPException(status_code=400, detail="New password must be different")
    user.password_hash = hash_password(payload.new_password)
    log_event(db, "auth", "password_changed", {"user_id": user.id})
    db.commit()
    return {"ok": True}


@app.post("/api/auth/recover-local")
def recover_local_password(payload: LocalRecoveryIn, db: Session = Depends(get_db)):
    if payload.recovery_key != settings.local_recovery_key:
        log_event(db, "auth", "password_recovery_failed", {"email": payload.email}, success=False, message="Invalid local recovery key")
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid local recovery key")
    user = db.query(User).filter(User.email == payload.email.lower().strip()).first()
    if not user:
        raise HTTPException(status_code=404, detail="Account not found")
    user.password_hash = hash_password(payload.new_password)
    log_event(db, "auth", "password_recovered", {"user_id": user.id})
    db.commit()
    return {"ok": True, "message": "Password updated. You can now sign in."}


@app.get("/api/model/info")
def model_info(_: User = Depends(get_current_user)):
    predictive_service.ensure_model()
    return predictive_service.metadata


@app.get("/api/models/status")
def models_status(_: User = Depends(get_current_user)):
    return {"predictive": predictive_service.model_status(), "quality": quality_service.model_status()}


@app.get("/api/dashboard")
def dashboard(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    machines = db.query(Machine).filter(Machine.archived == False).order_by(Machine.code).all()
    machine_rows = []
    risk_distribution = {"healthy": 0, "warning": 0, "high": 0, "critical": 0}
    for machine in machines:
        prediction = _latest_prediction(db, machine.id)
        reading = _latest_reading(db, machine.id)
        risk = prediction.risk_level if prediction else "healthy"
        risk_distribution[risk] = risk_distribution.get(risk, 0) + 1
        machine_rows.append({
            "id": machine.id,
            "code": machine.code,
            "name": machine.name,
            "type": machine.machine_type,
            "line_name": machine.line_name,
            "status": machine.status,
            "health_score": prediction.health_score if prediction else 100,
            "failure_probability": prediction.failure_probability if prediction else 0,
            "remaining_useful_hours": prediction.remaining_useful_hours if prediction else None,
            "risk_level": risk,
            "likely_issue": prediction.likely_issue if prediction else "normal operation",
            "temperature": reading.temperature if reading else None,
            "vibration": reading.vibration if reading else None,
            "power": reading.power if reading else None,
        })
    production_rows = db.query(ProductionRecord).order_by(ProductionRecord.recorded_at.asc()).all()
    production_metrics = _production_metrics(production_rows)
    trend = production_rows[-18:]
    alerts = db.query(Alert).order_by(Alert.created_at.desc()).limit(8).all()
    inspections = db.query(Inspection).order_by(Inspection.created_at.desc()).limit(8).all()
    maintenance_open = db.query(MaintenanceRecord).filter(MaintenanceRecord.status.in_(["open", "scheduled", "in_progress"])).count()
    energy_kw = sum(float(row["power"] or 0) for row in machine_rows)
    sorted_risk = sorted(machine_rows, key=lambda row: row["failure_probability"], reverse=True)
    insights = []
    if sorted_risk:
        top = sorted_risk[0]
        insights.append({"type": "risk", "title": f"Prioritize {top['code']}", "message": f"{top['likely_issue'].title()} is the leading concern at {top['failure_probability']:.0%} risk."})
    if production_metrics["quality"] < 97:
        insights.append({"type": "quality", "title": "Quality below target", "message": f"Current calculated quality is {production_metrics['quality']:.1f}%. Review recent rejects and inspections."})
    if production_metrics["oee"] < 82:
        insights.append({"type": "production", "title": "OEE improvement opportunity", "message": f"Calculated OEE is {production_metrics['oee']:.1f}%. Downtime and output variance are the main improvement levers."})
    if not insights:
        insights.append({"type": "healthy", "title": "Operations stable", "message": "No critical performance deviation is visible in the current operating window."})
    return {
        "kpis": {
            "total_machines": len(machines),
            "healthy_machines": risk_distribution.get("healthy", 0),
            "at_risk_machines": risk_distribution.get("warning", 0) + risk_distribution.get("high", 0),
            "critical_machines": risk_distribution.get("critical", 0),
            "production_count": production_metrics["produced"],
            "quality_rate": production_metrics["quality"],
            "oee": production_metrics["oee"],
            "downtime_minutes": production_metrics["downtime_minutes"],
            "open_alerts": sum(not alert.acknowledged for alert in alerts),
            "open_maintenance": maintenance_open,
            "energy_kw": round(energy_kw, 1),
        },
        "machines": machine_rows,
        "risk_distribution": risk_distribution,
        "production_metrics": production_metrics,
        "production_trend": [{"time": row.recorded_at.isoformat(), "planned": row.planned, "produced": row.produced, "rejected": row.rejected, "downtime": row.downtime_minutes} for row in trend],
        "alerts": [{"id": row.id, "severity": row.severity, "category": row.category, "title": row.title, "message": row.message, "acknowledged": row.acknowledged, "created_at": row.created_at.isoformat()} for row in alerts],
        "inspections": [{"id": row.id, "product_name": row.product_name, "status": row.status, "confidence": row.confidence, "defect_types": row.defect_types, "created_at": row.created_at.isoformat(), "annotated_url": f"/api/quality/images/{Path(row.annotated_path).name}" if row.annotated_path else None} for row in inspections],
        "insights": insights,
        "simulation": simulator.status(),
    }


@app.get("/api/factories")
def factories(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    rows = db.query(Factory).order_by(Factory.name).all()
    return [{"id": row.id, "name": row.name, "location": row.location, "timezone": row.timezone, "target_oee": row.target_oee, "machine_count": db.query(Machine).filter(Machine.factory_id == row.id, Machine.archived == False).count(), "created_at": row.created_at} for row in rows]


@app.post("/api/factories", status_code=201)
def create_factory(payload: FactoryCreate, db: Session = Depends(get_db), user: User = Depends(require_roles("admin"))):
    if db.query(Factory).filter(func.lower(Factory.name) == payload.name.lower().strip()).first():
        raise HTTPException(status_code=409, detail="Factory name already exists")
    row = Factory(**payload.model_dump())
    db.add(row)
    log_event(db, "factories", "factory_created", {"name": row.name, "user_id": user.id})
    db.commit()
    db.refresh(row)
    return {"id": row.id, "name": row.name, "location": row.location, "timezone": row.timezone, "target_oee": row.target_oee, "machine_count": 0, "created_at": row.created_at}


@app.patch("/api/factories/{factory_id}")
def update_factory(factory_id: int, payload: FactoryUpdate, db: Session = Depends(get_db), user: User = Depends(require_roles("admin"))):
    row = db.get(Factory, factory_id)
    if not row:
        raise HTTPException(status_code=404, detail="Factory not found")
    changes = payload.model_dump(exclude_unset=True)
    if "name" in changes:
        duplicate = db.query(Factory).filter(func.lower(Factory.name) == changes["name"].lower().strip(), Factory.id != row.id).first()
        if duplicate:
            raise HTTPException(status_code=409, detail="Factory name already exists")
    for key, value in changes.items():
        setattr(row, key, value)
    log_event(db, "factories", "factory_updated", {"factory_id": row.id, "changes": changes, "user_id": user.id})
    db.commit()
    db.refresh(row)
    return {"id": row.id, "name": row.name, "location": row.location, "timezone": row.timezone, "target_oee": row.target_oee, "machine_count": db.query(Machine).filter(Machine.factory_id == row.id, Machine.archived == False).count(), "created_at": row.created_at}


@app.delete("/api/factories/{factory_id}")
def delete_factory(factory_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles("admin"))):
    row = db.get(Factory, factory_id)
    if not row:
        raise HTTPException(status_code=404, detail="Factory not found")
    machine_count = db.query(Machine).filter(Machine.factory_id == row.id).count()
    if machine_count:
        raise HTTPException(status_code=409, detail="Move or archive and remove factory machines before deleting this factory")
    db.delete(row)
    log_event(db, "factories", "factory_deleted", {"factory_id": factory_id, "user_id": user.id})
    db.commit()
    return {"ok": True}


@app.get("/api/machines", response_model=list[MachineOut])
def list_machines(include_archived: bool = False, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    query = db.query(Machine)
    if not include_archived:
        query = query.filter(Machine.archived == False)
    return query.order_by(Machine.code).all()


@app.post("/api/machines", response_model=MachineOut, status_code=201)
def create_machine(payload: MachineCreate, db: Session = Depends(get_db), user: User = Depends(require_roles("admin", "factory_manager"))):
    if db.query(Machine).filter(Machine.code == payload.code.strip()).first():
        raise HTTPException(status_code=409, detail="Machine code already exists")
    if not db.get(Factory, payload.factory_id):
        raise HTTPException(status_code=404, detail="Factory not found")
    machine = Machine(**payload.model_dump())
    db.add(machine)
    log_event(db, "machines", "machine_created", {"code": machine.code, "user_id": user.id})
    db.commit()
    db.refresh(machine)
    return machine


@app.get("/api/machines/{machine_id}")
def machine_detail(machine_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    machine = db.get(Machine, machine_id)
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    readings = db.query(SensorReading).filter(SensorReading.machine_id == machine.id).order_by(SensorReading.recorded_at.desc()).limit(80).all()[::-1]
    predictions = db.query(MachinePrediction).filter(MachinePrediction.machine_id == machine.id).order_by(MachinePrediction.created_at.desc()).limit(30).all()
    maintenance = db.query(MaintenanceRecord).filter(MaintenanceRecord.machine_id == machine.id).order_by(MaintenanceRecord.created_at.desc()).all()
    alerts = db.query(Alert).filter(Alert.machine_id == machine.id).order_by(Alert.created_at.desc()).limit(25).all()
    commands = db.query(DeviceCommand).filter(DeviceCommand.machine_id == machine.id).order_by(DeviceCommand.created_at.desc()).limit(20).all()
    return {
        "machine": MachineOut.model_validate(machine),
        "readings": [{"id": row.id, "temperature": row.temperature, "vibration": row.vibration, "pressure": row.pressure, "rpm": row.rpm, "torque": row.torque, "power": row.power, "tool_wear": row.tool_wear, "recorded_at": row.recorded_at} for row in readings],
        "predictions": [{"id": row.id, "health_score": row.health_score, "failure_probability": row.failure_probability, "anomaly_score": row.anomaly_score, "remaining_useful_hours": row.remaining_useful_hours, "risk_level": row.risk_level, "likely_issue": row.likely_issue, "recommendation": row.recommendation, "maintenance_priority": row.maintenance_priority, "explanation": row.explanation, "created_at": row.created_at} for row in predictions],
        "maintenance": [{"id": row.id, "title": row.title, "action": row.action, "priority": row.priority, "status": row.status, "assigned_to": row.assigned_to, "scheduled_for": row.scheduled_for, "cost_estimate": row.cost_estimate, "notes": row.notes, "created_at": row.created_at, "updated_at": row.updated_at} for row in maintenance],
        "alerts": [{"id": row.id, "severity": row.severity, "category": row.category, "title": row.title, "message": row.message, "acknowledged": row.acknowledged, "created_at": row.created_at} for row in alerts],
        "commands": [{"id": row.id, "command": row.command, "status": row.status, "payload": row.payload, "response": row.response, "created_at": row.created_at} for row in commands],
    }


@app.patch("/api/machines/{machine_id}", response_model=MachineOut)
def update_machine(machine_id: int, payload: MachineUpdate, db: Session = Depends(get_db), user: User = Depends(require_roles("admin", "factory_manager", "maintenance_engineer"))):
    machine = db.get(Machine, machine_id)
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(machine, key, value)
    log_event(db, "machines", "machine_updated", {"machine_id": machine.id, "changes": payload.model_dump(exclude_unset=True), "user_id": user.id})
    db.commit()
    db.refresh(machine)
    return machine


@app.delete("/api/machines/{machine_id}")
def archive_machine(machine_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles("admin", "factory_manager"))):
    machine = db.get(Machine, machine_id)
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    machine.archived = True
    machine.status = "archived"
    log_event(db, "machines", "machine_archived", {"machine_id": machine.id, "user_id": user.id})
    db.commit()
    return {"ok": True, "machine_id": machine.id}


@app.get("/api/predictive/latest")
def predictive_latest(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    rows = []
    for machine in db.query(Machine).filter(Machine.archived == False).order_by(Machine.code).all():
        prediction = _latest_prediction(db, machine.id)
        reading = _latest_reading(db, machine.id)
        if prediction:
            rows.append({
                "machine": {"id": machine.id, "code": machine.code, "name": machine.name, "type": machine.machine_type, "line_name": machine.line_name},
                "prediction": {"health_score": prediction.health_score, "failure_probability": prediction.failure_probability, "anomaly_score": prediction.anomaly_score, "remaining_useful_hours": prediction.remaining_useful_hours, "risk_level": prediction.risk_level, "likely_issue": prediction.likely_issue, "recommendation": prediction.recommendation, "maintenance_priority": prediction.maintenance_priority, "explanation": prediction.explanation, "created_at": prediction.created_at},
                "reading": {"temperature": reading.temperature, "vibration": reading.vibration, "pressure": reading.pressure, "rpm": reading.rpm, "power": reading.power, "tool_wear": reading.tool_wear} if reading else None,
            })
    return sorted(rows, key=lambda row: row["prediction"]["failure_probability"], reverse=True)


@app.post("/api/hardware/readings")
def hardware_reading(payload: SensorReadingIn, x_device_key: str | None = Header(default=None), db: Session = Depends(get_db)):
    if x_device_key != settings.device_api_key:
        raise HTTPException(status_code=401, detail="Invalid device API key")
    machine = resolve_machine(db, payload.machine_id)
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    _, prediction, alert = ingest_and_analyze(db, machine, payload.model_dump())
    log_event(db, "hardware", "sensor_reading_ingested", {"machine_id": machine.code, "source": payload.source, "risk": prediction.risk_level})
    db.commit()
    return {"machine_id": machine.code, "status": machine.status, "health_score": prediction.health_score, "failure_probability": prediction.failure_probability, "anomaly_score": prediction.anomaly_score, "remaining_useful_hours": prediction.remaining_useful_hours, "risk_level": prediction.risk_level, "likely_issue": prediction.likely_issue, "recommended_action": prediction.recommendation, "alert_created": bool(alert)}


@app.get("/api/maintenance")
def maintenance_list(status_filter: str | None = None, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    query = db.query(MaintenanceRecord)
    if status_filter:
        query = query.filter(MaintenanceRecord.status == status_filter)
    rows = query.order_by(MaintenanceRecord.created_at.desc()).all()
    return [{"id": row.id, "machine_id": row.machine_id, "machine_code": db.get(Machine, row.machine_id).code if db.get(Machine, row.machine_id) else None, "title": row.title, "action": row.action, "priority": row.priority, "status": row.status, "assigned_to": row.assigned_to, "scheduled_for": row.scheduled_for, "cost_estimate": row.cost_estimate, "notes": row.notes, "created_at": row.created_at, "updated_at": row.updated_at, "completed_at": row.completed_at} for row in rows]


@app.post("/api/machines/{machine_id}/maintenance", status_code=201)
def maintenance_create(machine_id: int, payload: MaintenanceCreate, db: Session = Depends(get_db), user: User = Depends(require_roles("admin", "factory_manager", "maintenance_engineer"))):
    if not db.get(Machine, machine_id):
        raise HTTPException(status_code=404, detail="Machine not found")
    row = MaintenanceRecord(machine_id=machine_id, created_by=user.id, **payload.model_dump())
    db.add(row)
    log_event(db, "maintenance", "task_created", {"machine_id": machine_id, "title": row.title, "user_id": user.id})
    db.commit()
    db.refresh(row)
    return {"id": row.id, "status": row.status}


@app.patch("/api/maintenance/{record_id}")
def maintenance_update(record_id: int, payload: MaintenanceUpdate, db: Session = Depends(get_db), user: User = Depends(require_roles("admin", "factory_manager", "maintenance_engineer"))):
    row = db.get(MaintenanceRecord, record_id)
    if not row:
        raise HTTPException(status_code=404, detail="Maintenance record not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    if row.status == "completed" and not row.completed_at:
        row.completed_at = datetime.now(timezone.utc)
        machine = db.get(Machine, row.machine_id)
        if machine:
            machine.tool_wear = max(0, machine.tool_wear * .35)
            machine.status = "running"
    log_event(db, "maintenance", "task_updated", {"record_id": row.id, "changes": payload.model_dump(exclude_unset=True), "user_id": user.id})
    db.commit()
    return {"ok": True, "id": row.id, "status": row.status}


@app.get("/api/alerts")
def alerts(severity: str | None = None, category: str | None = None, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    query = db.query(Alert)
    if severity:
        query = query.filter(Alert.severity == severity)
    if category:
        query = query.filter(Alert.category == category)
    rows = query.order_by(Alert.created_at.desc()).limit(250).all()
    return [{"id": row.id, "machine_id": row.machine_id, "machine_code": db.get(Machine, row.machine_id).code if row.machine_id and db.get(Machine, row.machine_id) else None, "category": row.category, "severity": row.severity, "title": row.title, "message": row.message, "acknowledged": row.acknowledged, "read": row.read, "acknowledged_at": row.acknowledged_at, "created_at": row.created_at} for row in rows]


@app.get("/api/alerts/summary")
def alert_summary(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    rows = db.query(Alert).all()
    return {"total": len(rows), "unread": sum(not row.read for row in rows), "open": sum(not row.acknowledged for row in rows), "critical": sum(row.severity == "critical" and not row.acknowledged for row in rows), "high": sum(row.severity == "high" and not row.acknowledged for row in rows)}


@app.patch("/api/alerts/{alert_id}/read")
def alert_read(alert_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    row = db.get(Alert, alert_id)
    if not row:
        raise HTTPException(status_code=404, detail="Alert not found")
    row.read = True
    db.commit()
    return {"ok": True}


@app.patch("/api/alerts/{alert_id}/acknowledge")
def acknowledge(alert_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles("admin", "factory_manager", "maintenance_engineer", "quality_engineer"))):
    row = db.get(Alert, alert_id)
    if not row:
        raise HTTPException(status_code=404, detail="Alert not found")
    row.acknowledged = True
    row.read = True
    row.acknowledged_by = user.id
    row.acknowledged_at = datetime.now(timezone.utc)
    log_event(db, "alerts", "alert_acknowledged", {"alert_id": row.id, "user_id": user.id})
    db.commit()
    return {"ok": True, "id": row.id}


@app.patch("/api/alerts/acknowledge-all")
def acknowledge_all(db: Session = Depends(get_db), user: User = Depends(require_roles("admin", "factory_manager"))):
    rows = db.query(Alert).filter(Alert.acknowledged == False).all()
    now = datetime.now(timezone.utc)
    for row in rows:
        row.acknowledged = True
        row.read = True
        row.acknowledged_by = user.id
        row.acknowledged_at = now
    log_event(db, "alerts", "alerts_acknowledged_all", {"count": len(rows), "user_id": user.id})
    db.commit()
    return {"ok": True, "count": len(rows)}


@app.post("/api/quality/inspect")
async def inspect_quality(
    file: UploadFile = File(...),
    reference: UploadFile | None = File(default=None),
    machine_id: int | None = Form(default=None),
    product_name: str = Form(default="Industrial Component"),
    batch_code: str = Form(default=""),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin", "factory_manager", "quality_engineer")),
):
    raw = await file.read()
    reference_raw = await reference.read() if reference else None
    try:
        result = quality_service.inspect(raw, file.content_type or "", file.filename or "upload", reference_raw, reference.content_type if reference else None)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    row = Inspection(
        machine_id=machine_id,
        product_name=product_name.strip() or "Industrial Component",
        batch_code=batch_code.strip(),
        inspection_mode=result["inspection_mode"],
        status=result["status"],
        confidence=result["confidence"],
        anomaly_score=result["anomaly_score"],
        defect_types=result["defect_types"],
        bounding_boxes=result["bounding_boxes"],
        measurements=result["measurements"],
        original_path=result["original_path"],
        reference_path=result["reference_path"],
        annotated_path=result["annotated_path"],
    )
    db.add(row)
    if row.status == "defective":
        db.add(Alert(machine_id=machine_id, category="quality", severity="high", title="Defective product detected", message=f"{row.product_name} in batch {row.batch_code or 'unassigned'} failed visual inspection at {row.confidence:.0%} confidence."))
    log_event(db, "quality", "inspection_completed", {"status": row.status, "product": row.product_name, "batch": row.batch_code, "user_id": user.id})
    db.commit()
    db.refresh(row)
    return {"id": row.id, **result, "annotated_url": f"/api/quality/images/{Path(result['annotated_path']).name}"}


@app.get("/api/quality/images/{filename}")
def inspection_image(filename: str):
    safe = Path(filename).name
    path = Path(settings.storage_dir) / "inspections" / safe
    if not path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(path)


@app.get("/api/quality/inspections")
def inspections(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    rows = db.query(Inspection).order_by(Inspection.created_at.desc()).limit(250).all()
    return [{"id": row.id, "machine_id": row.machine_id, "product_name": row.product_name, "batch_code": row.batch_code, "inspection_mode": row.inspection_mode, "status": row.status, "confidence": row.confidence, "anomaly_score": row.anomaly_score, "defect_types": row.defect_types, "bounding_boxes": row.bounding_boxes, "measurements": row.measurements, "annotated_url": f"/api/quality/images/{Path(row.annotated_path).name}" if row.annotated_path else None, "created_at": row.created_at} for row in rows]


@app.get("/api/quality/stats")
def quality_stats(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    rows = db.query(Inspection).order_by(Inspection.created_at.asc()).all()
    defective = sum(row.status == "defective" for row in rows)
    types: dict[str, int] = defaultdict(int)
    for row in rows:
        for defect in row.defect_types:
            types[defect] += 1
    recent = rows[-20:]
    return {"total": len(rows), "passed": len(rows) - defective, "defective": defective, "pass_rate": round((len(rows) - defective) / max(1, len(rows)) * 100, 1), "defect_types": dict(sorted(types.items(), key=lambda item: item[1], reverse=True)), "trend": [{"time": row.created_at.isoformat(), "status": row.status, "anomaly_score": row.anomaly_score, "confidence": row.confidence} for row in recent], "engine": quality_service.model_status().get("model_name", "ForgeMind Vision Surface Inspector 3.0"), "model_runtime_mode": quality_service.model_status().get("runtime_mode"), "modes": ["surface anomaly", "reference comparison"]}


@app.get("/api/production")
def production(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    rows = db.query(ProductionRecord).order_by(ProductionRecord.recorded_at.desc()).limit(300).all()
    metrics = _production_metrics(rows)
    return {"metrics": metrics, "records": [{"id": row.id, "factory_id": row.factory_id, "line_name": row.line_name, "product_name": row.product_name, "planned": row.planned, "produced": row.produced, "rejected": row.rejected, "downtime_minutes": row.downtime_minutes, "runtime_minutes": row.runtime_minutes, "ideal_cycle_seconds": row.ideal_cycle_seconds, "shift": row.shift, "recorded_at": row.recorded_at} for row in rows]}


@app.post("/api/production", status_code=201)
def production_create(payload: ProductionCreate, db: Session = Depends(get_db), user: User = Depends(require_roles("admin", "factory_manager"))):
    if payload.rejected > payload.produced:
        raise HTTPException(status_code=400, detail="Rejected count cannot exceed produced count")
    row = ProductionRecord(**payload.model_dump())
    db.add(row)
    reject_rate = payload.rejected / max(1, payload.produced) * 100
    if reject_rate >= 5:
        db.add(Alert(category="production", severity="warning", title="Production reject rate increased", message=f"Recorded reject rate reached {reject_rate:.1f}% on {payload.line_name}."))
    log_event(db, "production", "production_record_created", {"line": payload.line_name, "produced": payload.produced, "user_id": user.id})
    db.commit()
    db.refresh(row)
    return {"id": row.id}


@app.post("/api/assistant/query")
def assistant(payload: AssistantQuery, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    conversation = db.get(AssistantConversation, payload.conversation_id) if payload.conversation_id else None
    if conversation and conversation.user_id != user.id:
        raise HTTPException(status_code=403, detail="Conversation belongs to another user")
    if not conversation:
        conversation = AssistantConversation(user_id=user.id, title=payload.question[:80])
        db.add(conversation)
        db.flush()
    db.add(AssistantMessage(conversation_id=conversation.id, role="user", content=payload.question))
    result = assistant_service.answer(db, payload.question, payload.locale)
    db.add(AssistantMessage(conversation_id=conversation.id, role="assistant", content=result["answer"], evidence=result["evidence"]))
    conversation.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {**result, "conversation_id": conversation.id}


@app.get("/api/assistant/conversations")
def assistant_conversations(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.query(AssistantConversation).filter(AssistantConversation.user_id == user.id).order_by(AssistantConversation.updated_at.desc()).all()
    return [{"id": row.id, "title": row.title, "created_at": row.created_at, "updated_at": row.updated_at} for row in rows]


@app.get("/api/assistant/conversations/{conversation_id}")
def assistant_conversation(conversation_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    conversation = db.get(AssistantConversation, conversation_id)
    if not conversation or conversation.user_id != user.id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    messages = db.query(AssistantMessage).filter(AssistantMessage.conversation_id == conversation.id).order_by(AssistantMessage.created_at.asc()).all()
    return {"id": conversation.id, "title": conversation.title, "messages": [{"id": row.id, "role": row.role, "content": row.content, "evidence": row.evidence, "created_at": row.created_at} for row in messages]}


@app.get("/api/simulation/status")
def simulation_status(_: User = Depends(get_current_user)):
    return simulator.status()


@app.post("/api/simulation/configure")
def simulation_configure(payload: SimulationConfigIn, _: User = Depends(require_roles("admin", "factory_manager"))):
    return simulator.configure(**payload.model_dump())


@app.post("/api/simulation/tick")
def simulation_tick(db: Session = Depends(get_db), _: User = Depends(require_roles("admin", "factory_manager"))):
    return simulator.tick(db)


@app.post("/api/simulation/{action}")
def simulation_action(action: str, _: User = Depends(require_roles("admin", "factory_manager"))):
    try:
        return simulator.action(action)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/reports/generate", status_code=201)
def report_generate(payload: ReportGenerateIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row = save_report(db, payload.report_type, user.id, payload.start_date, payload.end_date)
    log_event(db, "reports", "report_generated", {"report_id": row.id, "type": row.report_type, "user_id": user.id})
    db.commit()
    return {"id": row.id, "title": row.title, "report_type": row.report_type, "download_url": f"/api/reports/{row.id}/download", "created_at": row.created_at}


@app.get("/api/reports")
def reports(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    rows = db.query(Report).order_by(Report.created_at.desc()).limit(200).all()
    return [{"id": row.id, "title": row.title, "report_type": row.report_type, "period_start": row.period_start, "period_end": row.period_end, "download_url": f"/api/reports/{row.id}/download", "created_at": row.created_at} for row in rows]


@app.get("/api/reports/production.csv")
def report_csv(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return Response(content=production_csv(db), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=forgemind-production.csv"})


@app.get("/api/reports/{report_id}/download")
def report_download(report_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    row = db.get(Report, report_id)
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")
    path = Path(row.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Report file is unavailable")
    return FileResponse(path, media_type="application/pdf", filename=path.name)


@app.post("/api/device/commands", status_code=201)
def device_command(payload: DeviceCommandIn, db: Session = Depends(get_db), user: User = Depends(require_roles("admin", "factory_manager", "maintenance_engineer"))):
    machine = resolve_machine(db, payload.machine_id)
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")
    allowed = {"reject_product", "stop_machine", "start_machine", "pause_conveyor", "resume_conveyor", "request_inspection", "trigger_warning_light", "open_maintenance_ticket"}
    if payload.command not in allowed:
        raise HTTPException(status_code=400, detail=f"Unsupported command. Allowed: {', '.join(sorted(allowed))}")
    response = {"device": machine.code, "accepted": True, "gateway": "local-industrial-adapter", "message": f"Command {payload.command} was accepted and recorded."}
    row = DeviceCommand(machine_id=machine.id, command=payload.command, payload=payload.payload, response=response, status="completed", issued_by=user.id)
    db.add(row)
    if payload.command == "stop_machine":
        machine.status = "maintenance"
    elif payload.command == "start_machine":
        machine.status = "running"
    elif payload.command == "open_maintenance_ticket":
        db.add(MaintenanceRecord(machine_id=machine.id, title=payload.payload.get("title", "Device-requested inspection"), action=payload.payload.get("action", "Inspect machine condition"), priority=payload.payload.get("priority", "high"), assigned_to=payload.payload.get("assigned_to", "Maintenance Team"), created_by=user.id))
    elif payload.command == "request_inspection":
        db.add(Alert(machine_id=machine.id, category="quality", severity="informational", title="Inspection requested", message=f"An operator requested a product inspection from {machine.code}."))
    log_event(db, "device_gateway", "command_issued", {"machine": machine.code, "command": payload.command, "user_id": user.id})
    db.commit()
    db.refresh(row)
    return {"command_id": row.id, **response}


@app.get("/api/device/commands")
def device_commands(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    rows = db.query(DeviceCommand).order_by(DeviceCommand.created_at.desc()).limit(200).all()
    return [{"id": row.id, "machine_id": row.machine_id, "machine_code": db.get(Machine, row.machine_id).code if db.get(Machine, row.machine_id) else None, "command": row.command, "status": row.status, "payload": row.payload, "response": row.response, "created_at": row.created_at} for row in rows]


@app.get("/api/admin/users", response_model=list[UserOut])
def admin_users(db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    return db.query(User).order_by(User.created_at.desc()).all()


@app.post("/api/admin/users/{user_id}/reset-password")
def admin_reset_password(user_id: int, payload: AdminPasswordResetIn, db: Session = Depends(get_db), admin: User = Depends(require_roles("admin"))):
    row = db.get(User, user_id)
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    row.password_hash = hash_password(payload.new_password)
    log_event(db, "admin", "user_password_reset", {"target_user": row.id, "admin_id": admin.id})
    db.commit()
    return {"ok": True}


@app.patch("/api/admin/users/{user_id}", response_model=UserOut)
def admin_user_update(user_id: int, payload: UserAdminUpdate, db: Session = Depends(get_db), admin: User = Depends(require_roles("admin"))):
    row = db.get(User, user_id)
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    changes = payload.model_dump(exclude_unset=True)
    if "role" in changes and changes["role"] not in {"admin", "factory_manager", "quality_engineer", "maintenance_engineer", "viewer"}:
        raise HTTPException(status_code=400, detail="Invalid role")
    if row.id == admin.id and changes.get("active") is False:
        raise HTTPException(status_code=400, detail="You cannot deactivate your own account")
    for key, value in changes.items():
        setattr(row, key, value)
    log_event(db, "admin", "user_updated", {"target_user": row.id, "changes": changes, "admin_id": admin.id})
    db.commit()
    db.refresh(row)
    return row


@app.get("/api/admin/settings")
def admin_settings(db: Session = Depends(get_db), _: User = Depends(require_roles("admin", "factory_manager"))):
    rows = db.query(AppSetting).order_by(AppSetting.key).all()
    return [{"id": row.id, "key": row.key, "value": row.value, "description": row.description, "updated_at": row.updated_at} for row in rows]


@app.put("/api/admin/settings/{key}")
def admin_setting_update(key: str, payload: SettingUpdateIn, db: Session = Depends(get_db), user: User = Depends(require_roles("admin"))):
    row = db.query(AppSetting).filter(AppSetting.key == key).first()
    if not row:
        row = AppSetting(key=key, value=payload.value, description=payload.description, updated_by=user.id)
        db.add(row)
    else:
        row.value = payload.value
        row.description = payload.description or row.description
        row.updated_by = user.id
    log_event(db, "admin", "setting_updated", {"key": key, "user_id": user.id})
    db.commit()
    db.refresh(row)
    return {"ok": True, "key": row.key, "value": row.value}


@app.get("/api/admin/logs")
def admin_logs(limit: int = 100, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    rows = db.query(IntegrationLog).order_by(IntegrationLog.created_at.desc()).limit(min(max(limit, 1), 500)).all()
    return [{"id": row.id, "source": row.source, "event_type": row.event_type, "payload": row.payload, "success": row.success, "message": row.message, "created_at": row.created_at} for row in rows]

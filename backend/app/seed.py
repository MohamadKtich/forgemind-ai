from __future__ import annotations
from datetime import datetime, timedelta, timezone
import random
from sqlalchemy.orm import Session
from .models import Alert, AppSetting, Factory, Machine, MaintenanceRecord, ProductionRecord, User
from .security import hash_password
from .services.core import ingest_and_analyze


def seed_database(db: Session) -> None:
    if db.query(User).count() == 0:
        users = [
            User(full_name="ForgeMind Administrator", email="admin@forgemind.ai", password_hash=hash_password("ForgeMind#2026"), role="admin"),
            User(full_name="Operations Manager", email="manager@forgemind.ai", password_hash=hash_password("ForgeMind#2026"), role="factory_manager"),
            User(full_name="Maintenance Engineer", email="maintenance@forgemind.ai", password_hash=hash_password("ForgeMind#2026"), role="maintenance_engineer"),
            User(full_name="Quality Engineer", email="quality@forgemind.ai", password_hash=hash_password("ForgeMind#2026"), role="quality_engineer"),
        ]
        db.add_all(users)
        db.commit()

    if db.query(Factory).count() > 0:
        return

    factory = Factory(name="ForgeMind Smart Manufacturing Plant", location="Ras Al Khaimah Industrial Zone", timezone="Asia/Dubai", target_oee=86)
    db.add(factory)
    db.flush()
    specs = [
        ("M-001", "CNC Milling Center", "CNC", "DMG Mori", "CMX 1100 V", "Precision Line", 2.5, 5400, 72, 21),
        ("M-002", "Hydraulic Forming Press", "Hydraulic Press", "Schuler", "HSP-500", "Forming Line", 6.2, 13900, 164, 44),
        ("M-003", "Conveyor Drive System", "Conveyor", "SEW Eurodrive", "MOVI-C", "Assembly Line", 3.7, 8200, 94, 12),
        ("M-004", "Robotic Packaging Cell", "Packaging", "ABB", "IRB 460", "Packaging Line", 1.8, 3300, 45, 18),
        ("M-005", "Injection Molding Unit", "Injection Molder", "ENGEL", "victory 500", "Polymer Line", 8.4, 19100, 214, 55),
        ("M-006", "Industrial Air Compressor", "Compressor", "Atlas Copco", "GA 45", "Utilities", 5.1, 12500, 126, 45),
        ("M-007", "Laser Cutting Station", "Laser Cutter", "TRUMPF", "TruLaser 3030", "Sheet Metal Line", 2.1, 4800, 62, 30),
    ]
    machines: list[Machine] = []
    for code, name, machine_type, manufacturer, model_number, line_name, age, hours, wear, power in specs:
        machine = Machine(
            factory_id=factory.id,
            code=code,
            name=name,
            machine_type=machine_type,
            manufacturer=manufacturer,
            model_number=model_number,
            line_name=line_name,
            age_years=age,
            operating_hours=hours,
            tool_wear=wear,
            rated_power_kw=power,
            installation_date=f"{2026 - int(age):04d}-01-15",
            notes="Connected to ForgeMind local monitoring gateway.",
        )
        db.add(machine)
        machines.append(machine)
    db.commit()

    rng = random.Random(41)
    for index, machine in enumerate(machines):
        for sample in range(18):
            stress = .065 * index + sample * .002 + rng.random() * .055
            if machine.code == "M-005":
                stress += .24
            if machine.code == "M-002":
                stress += .10
            payload = {
                "temperature": 61 + stress * 31 + rng.uniform(-2.2, 2.0),
                "vibration": .20 + stress * 1.05 + rng.uniform(.01, .08),
                "pressure": 31 + rng.uniform(-2.0, 2.0) + stress * 1.7,
                "rpm": 1470 + rng.uniform(-110, 105) - stress * 75,
                "torque": 44 + rng.uniform(-5, 7) + stress * 10,
                "power": 12.5 + rng.uniform(-1.2, 1.8) + stress * 4,
                "source": "seed_history",
            }
            ingest_and_analyze(db, machine, payload)

    now = datetime.now(timezone.utc)
    products = ["Precision Housing", "Valve Body", "Motor Bracket", "Pump Casing"]
    lines = ["Precision Line", "Forming Line", "Assembly Line", "Packaging Line"]
    for index in range(36):
        planned = rng.randint(46, 62)
        produced = max(0, planned + rng.randint(-7, 5))
        rejected = rng.randint(0, 3)
        downtime = 0 if rng.random() > .22 else round(rng.uniform(1.5, 8), 1)
        db.add(ProductionRecord(
            factory_id=factory.id,
            line_name=lines[index % len(lines)],
            product_name=products[index % len(products)],
            planned=planned,
            produced=produced,
            rejected=rejected,
            downtime_minutes=downtime,
            runtime_minutes=60 - downtime,
            ideal_cycle_seconds=60,
            shift="A" if index % 3 == 0 else "B" if index % 3 == 1 else "C",
            recorded_at=now - timedelta(hours=35 - index),
        ))

    manager = db.query(User).filter(User.role == "factory_manager").first()
    db.add_all([
        MaintenanceRecord(machine_id=machines[4].id, title="Injection tool inspection", action="Inspect tool wear, replace nozzle insert, and validate cycle pressure.", priority="high", status="scheduled", assigned_to="Maintenance Engineer", scheduled_for="Next planned stop", cost_estimate=850, created_by=manager.id if manager else None),
        MaintenanceRecord(machine_id=machines[1].id, title="Hydraulic seal inspection", action="Inspect hydraulic seals and pressure regulator for gradual pressure drift.", priority="medium", status="open", assigned_to="Hydraulics Team", scheduled_for="Within 72 hours", cost_estimate=420, created_by=manager.id if manager else None),
        MaintenanceRecord(machine_id=machines[0].id, title="Spindle lubrication", action="Complete scheduled spindle lubrication and verify vibration baseline.", priority="low", status="completed", assigned_to="Maintenance Engineer", scheduled_for="Completed", cost_estimate=120, created_by=manager.id if manager else None, completed_at=now - timedelta(days=2)),
    ])
    db.add_all([
        Alert(machine_id=machines[4].id, category="predictive_maintenance", severity="high", title="M-005 tool wear trend", message="Tool wear and thermal load are approaching the configured intervention threshold."),
        Alert(machine_id=machines[1].id, category="sensor", severity="warning", title="M-002 pressure drift", message="Pressure variance has increased across the latest operating window."),
        Alert(machine_id=machines[2].id, category="production", severity="informational", title="Assembly line recovered", message="The assembly line returned to target throughput after a short slowdown.", acknowledged=True, read=True),
    ])
    settings = [
        AppSetting(key="alert_thresholds", value={"temperature_warning": 78, "temperature_critical": 92, "vibration_warning": .72, "vibration_critical": 1.15, "defect_rate_warning": 4.0}, description="Operational alert thresholds."),
        AppSetting(key="factory_profile", value={"name": factory.name, "location": factory.location, "timezone": factory.timezone, "target_oee": factory.target_oee}, description="Factory identity and operating targets."),
        AppSetting(key="notification_channels", value={"in_app": True, "email": False, "webhook": False}, description="Notification channel configuration."),
    ]
    db.add_all(settings)
    db.commit()

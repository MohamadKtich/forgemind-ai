from __future__ import annotations
from dataclasses import dataclass, field
import random
from sqlalchemy.orm import Session
from ..models import Alert, Inspection, Machine, MaintenanceRecord, ProductionRecord
from .core import ingest_and_analyze


@dataclass
class SimulationState:
    running: bool = False
    tick: int = 0
    scenario: str | None = None
    degradation: dict[int, float] = field(default_factory=dict)
    speed_seconds: float = 3.0
    degradation_rate: float = 1.0
    anomaly_frequency: float = .08
    production_rate: int = 52


class FactorySimulator:
    def __init__(self):
        self.state = SimulationState()
        self.rng = random.Random(73)

    def action(self, action: str) -> dict:
        if action == "start":
            self.state.running = True
        elif action == "pause":
            self.state.running = False
        elif action == "reset":
            self.state = SimulationState()
        elif action in {"failure", "defect", "critical", "power_spike", "pressure_drop"}:
            self.state.scenario = action
            self.state.running = True
        else:
            raise ValueError("Unsupported simulation action")
        return self.status()

    def configure(self, *, speed_seconds: float, degradation_rate: float, anomaly_frequency: float, production_rate: int) -> dict:
        self.state.speed_seconds = speed_seconds
        self.state.degradation_rate = degradation_rate
        self.state.anomaly_frequency = anomaly_frequency
        self.state.production_rate = production_rate
        return self.status()

    def status(self) -> dict:
        return {
            "running": self.state.running,
            "tick": self.state.tick,
            "scenario": self.state.scenario,
            "speed_seconds": self.state.speed_seconds,
            "degradation_rate": self.state.degradation_rate,
            "anomaly_frequency": self.state.anomaly_frequency,
            "production_rate": self.state.production_rate,
        }

    def tick(self, db: Session) -> dict:
        if not self.state.running:
            return {**self.status(), "updated": 0}
        machines = db.query(Machine).filter(Machine.archived == False).order_by(Machine.id).all()
        updates = []
        selected_index = 1 if len(machines) > 1 else 0
        for index, machine in enumerate(machines):
            degradation = self.state.degradation.get(machine.id, .02 * index)
            degradation += self.rng.uniform(.001, .010) * self.state.degradation_rate
            self.state.degradation[machine.id] = min(1.2, degradation)
            stress = degradation
            active_scenario = self.state.scenario if index == selected_index else None
            if active_scenario == "failure":
                stress += .62
            elif active_scenario == "critical":
                stress += 1.02
            elif active_scenario == "power_spike":
                stress += .42
            elif active_scenario == "pressure_drop":
                stress += .35
            elif self.rng.random() < self.state.anomaly_frequency:
                stress += self.rng.uniform(.12, .32)
            pressure = 31 + self.rng.uniform(-1.8, 1.8) + stress * 2.6
            if active_scenario == "pressure_drop":
                pressure -= 13
            power = 13.5 + self.rng.uniform(-1.2, 1.4) + stress * 5.4
            if active_scenario == "power_spike":
                power += 15
            payload = {
                "temperature": round(62 + stress * 34 + self.rng.uniform(-2.0, 2.2), 2),
                "vibration": round(.22 + stress * 1.28 + self.rng.uniform(0, .10), 3),
                "pressure": round(max(5, pressure), 2),
                "rpm": round(max(80, 1470 + self.rng.uniform(-115, 115) - stress * 110), 1),
                "torque": round(45 + self.rng.uniform(-5, 6) + stress * 17, 2),
                "power": round(max(.5, power), 2),
                "source": "factory_simulator",
            }
            _, prediction, alert = ingest_and_analyze(db, machine, payload)
            if prediction.risk_level == "critical":
                existing = db.query(MaintenanceRecord).filter(
                    MaintenanceRecord.machine_id == machine.id,
                    MaintenanceRecord.status.in_(["open", "scheduled", "in_progress"]),
                ).first()
                if not existing:
                    db.add(MaintenanceRecord(
                        machine_id=machine.id,
                        title=f"Critical inspection: {prediction.likely_issue}",
                        action=prediction.recommendation,
                        priority="critical",
                        status="open",
                        assigned_to="Maintenance Team",
                        notes="Created automatically by the predictive-maintenance engine.",
                    ))
                    db.commit()
            updates.append({
                "machine": machine.code,
                "name": machine.name,
                "risk": prediction.risk_level,
                "health": prediction.health_score,
                "failure_probability": prediction.failure_probability,
                "temperature": payload["temperature"],
                "vibration": payload["vibration"],
                "alert_created": bool(alert),
            })

        planned = self.state.production_rate
        produced = max(0, planned + self.rng.randint(-7, 8))
        rejected = self.rng.randint(0, 2)
        downtime = 0.0
        if self.state.scenario == "defect":
            rejected += self.rng.randint(8, 15)
            db.add(Alert(category="quality", severity="high", title="Quality defect spike", message="Rejected product rate exceeded the configured quality threshold."))
            db.add(Inspection(
                product_name="Simulated Production Batch",
                batch_code=f"SIM-{self.state.tick + 1:04d}",
                inspection_mode="sensor_quality_event",
                status="defective",
                confidence=.94,
                anomaly_score=.88,
                defect_types=["surface_irregularity", "process_variation"],
                bounding_boxes=[],
                measurements={"simulated": True, "reject_count": rejected},
                original_path="",
                annotated_path="",
            ))
        if any(row["risk"] == "critical" for row in updates):
            downtime = round(self.rng.uniform(4, 12), 1)
        db.add(ProductionRecord(
            factory_id=1,
            line_name="Main Assembly Line",
            product_name="Precision Housing",
            planned=planned,
            produced=produced,
            rejected=rejected,
            downtime_minutes=downtime,
            runtime_minutes=max(1, 60 - downtime),
            ideal_cycle_seconds=60,
            shift="A" if (self.state.tick // 8) % 2 == 0 else "B",
        ))
        db.commit()
        scenario = self.state.scenario
        self.state.scenario = None
        self.state.tick += 1
        return {
            **self.status(),
            "scenario_completed": scenario,
            "updated": len(updates),
            "machines": updates,
            "production": {"planned": planned, "produced": produced, "rejected": rejected, "downtime_minutes": downtime},
        }


simulator = FactorySimulator()

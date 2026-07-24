from __future__ import annotations
from pathlib import Path
import json
import math
import joblib
import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier, IsolationForest, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from ..config import get_settings

FEATURES = [
    "temperature", "vibration", "pressure", "rpm", "torque", "power",
    "operating_hours", "tool_wear", "age_years",
]


class PredictiveService:
    def __init__(self):
        self.settings = get_settings()
        self.model_path = Path(self.settings.predictive_model_path)
        self.metadata_path = Path(self.settings.predictive_metadata_path)
        self.bundle: dict | None = None
        self.metadata: dict = {}
        self.metropt_model_path = Path(self.settings.metropt_model_path)
        self.metropt_metadata_path = Path(self.settings.metropt_metadata_path)
        self.metropt_bundle: dict | None = None
        self.metropt_metadata: dict = {}

    def ensure_model(self) -> None:
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        if self.model_path.exists():
            try:
                self.bundle = joblib.load(self.model_path)
                if self.metadata_path.exists():
                    self.metadata = json.loads(self.metadata_path.read_text(encoding="utf-8"))
                if isinstance(self.bundle, dict) and "classifier" in self.bundle:
                    self._load_specialized_models()
                    return
            except Exception:
                pass
        self.train_benchmark_model()
        self._load_specialized_models()

    def _load_specialized_models(self) -> None:
        self.metropt_bundle = None
        self.metropt_metadata = {}
        if not self.metropt_model_path.exists():
            return
        try:
            bundle = joblib.load(self.metropt_model_path)
            if isinstance(bundle, dict) and "classifier" in bundle:
                self.metropt_bundle = bundle
                if self.metropt_metadata_path.exists():
                    self.metropt_metadata = json.loads(self.metropt_metadata_path.read_text(encoding="utf-8"))
        except Exception as exc:
            self.metropt_metadata = {"available": False, "load_error": str(exc)}

    def model_status(self) -> dict:
        self.ensure_model()
        return {
            "generic": {**self.metadata, "installed": self.bundle is not None, "runtime_scope": "all machine families as a local fallback"},
            "air_compressor": {**self.metropt_metadata, "installed": self.metropt_bundle is not None, "runtime_scope": "compressor-like machine types only"},
        }

    @staticmethod
    def _metropt_snapshot(reading: dict) -> np.ndarray:
        pressure = float(reading["pressure"]); temperature = float(reading["temperature"]); rpm = float(reading["rpm"]); power = float(reading["power"]); wear = float(reading.get("tool_wear", 0))
        tp2 = pressure
        tp3 = pressure * .91
        h1 = max(0.0, tp2 - tp3)
        dv_pressure = max(0.0, tp2 - tp3)
        reservoirs = pressure * .98
        oil_temperature = temperature
        motor_current = max(.1, power * 1.35)
        comp = 1.0 if rpm > 350 else 0.0
        dv_electric = 1.0 if pressure < 27 else 0.0
        towers = 1.0 if temperature > 74 else 0.0
        mpg = 1.0 if rpm > 500 else 0.0
        lps = 1.0 if pressure < 18 else 0.0
        pressure_switch = 1.0 if pressure > 32 else 0.0
        oil_level = 0.0 if wear > 235 else 1.0
        caudal_impulses = max(0.0, rpm / 60.0)
        return np.array([[tp2,tp3,h1,dv_pressure,reservoirs,oil_temperature,motor_current,comp,dv_electric,towers,mpg,lps,pressure_switch,oil_level,caudal_impulses]], dtype=float)

    @staticmethod
    def _benchmark_data(n: int = 9_000, seed: int = 2026) -> tuple[np.ndarray, np.ndarray]:
        """Create a deterministic industrial benchmark aligned with AI4I-style ranges.

        UCI AI4I is itself synthetic. The included offline model uses a richer generated
        benchmark so the application works without internet; train_ai4i.py replaces it
        with the official CSV whenever available.
        """
        rng = np.random.default_rng(seed)
        age = rng.uniform(0.2, 24, n)
        hours = rng.uniform(20, 42_000, n)
        wear = np.clip(rng.gamma(2.1, 58, n), 0, 300)
        temperature = np.clip(rng.normal(66, 10, n) + age * .24 + wear * .018, 25, 145)
        vibration = np.clip(rng.gamma(1.8, .18, n) + age * .008 + wear * .0011, .02, 4.8)
        pressure = np.clip(rng.normal(31, 4.5, n) + rng.normal(0, 1.4, n), 7, 80)
        rpm = np.clip(rng.normal(1480, 310, n) - wear * .22, 120, 4800)
        torque = np.clip(rng.normal(46, 12, n) + wear * .055, 2, 190)
        power = np.clip((rpm * torque) / 9550 + rng.normal(5.8, 1.4, n), 1, 65)

        thermal = np.maximum(temperature - 78, 0) / 18
        bearing = np.maximum(vibration - .58, 0) * 1.9
        pressure_risk = np.abs(pressure - 31) / 18
        wear_risk = np.maximum(wear - 145, 0) / 85
        age_risk = age / 28
        hours_risk = hours / 50_000
        speed_risk = np.abs(rpm - 1450) / 2600
        interaction = thermal * bearing + wear_risk * np.maximum(torque - 50, 0) / 80
        logit = -4.9 + thermal + bearing + .7 * pressure_risk + 1.15 * wear_risk + .7 * age_risk + .75 * hours_risk + .5 * speed_risk + 1.1 * interaction
        probability = 1 / (1 + np.exp(-logit))
        target = rng.binomial(1, np.clip(probability, .002, .985))
        X = np.column_stack([temperature, vibration, pressure, rpm, torque, power, hours, wear, age])
        return X, target

    def train_benchmark_model(self) -> dict:
        X, y = self._benchmark_data()
        X_trainval, X_test, y_trainval, y_test = train_test_split(
            X, y, test_size=.22, random_state=42, stratify=y
        )
        X_train, X_val, y_train, y_val = train_test_split(
            X_trainval, y_trainval, test_size=.22, random_state=43, stratify=y_trainval
        )
        candidates = {
            "Logistic Regression": Pipeline([
                ("imputer", SimpleImputer(strategy="median")),
                ("scale", StandardScaler()),
                ("model", LogisticRegression(max_iter=1200, class_weight="balanced", C=.8)),
            ]),
            "Random Forest": RandomForestClassifier(
                n_estimators=180, max_depth=13, min_samples_leaf=3,
                class_weight="balanced_subsample", random_state=42, n_jobs=1,
            ),
            "Gradient Boosting": GradientBoostingClassifier(
                n_estimators=120, learning_rate=.06, max_depth=3, min_samples_leaf=4, random_state=42,
            ),
        }
        comparisons = []
        best_name = ""
        best_model = None
        best_threshold = .5
        best_score = -1.0
        best_metrics: dict = {}
        for name, model in candidates.items():
            sample_weight = np.where(y_train == 1, max(2.0, (len(y_train) - y_train.sum()) / max(1, y_train.sum()) * .55), 1.0)
            try:
                model.fit(X_train, y_train, model__sample_weight=sample_weight)
            except (TypeError, ValueError):
                try:
                    model.fit(X_train, y_train, sample_weight=sample_weight)
                except TypeError:
                    model.fit(X_train, y_train)
            validation_proba = model.predict_proba(X_val)[:, 1]
            threshold = .5
            validation_f1 = -1.0
            for candidate_threshold in np.linspace(.05, .90, 171):
                candidate_pred = validation_proba >= candidate_threshold
                _, _, candidate_f1, _ = precision_recall_fscore_support(
                    y_val, candidate_pred, average="binary", zero_division=0
                )
                if candidate_f1 > validation_f1:
                    threshold = float(candidate_threshold)
                    validation_f1 = float(candidate_f1)

            proba = model.predict_proba(X_test)[:, 1]
            pred = proba >= threshold
            precision, recall, f1, _ = precision_recall_fscore_support(y_test, pred, average="binary", zero_division=0)
            metrics = {
                "accuracy": float(accuracy_score(y_test, pred)),
                "precision": float(precision),
                "recall": float(recall),
                "f1": float(f1),
                "roc_auc": float(roc_auc_score(y_test, proba)),
                "decision_threshold": threshold,
                "confusion_matrix": confusion_matrix(y_test, pred).tolist(),
            }
            comparisons.append({"model": name, **{k: round(v, 4) if isinstance(v, float) else v for k, v in metrics.items()}})
            score = metrics["f1"] * .55 + metrics["roc_auc"] * .45
            if score > best_score:
                best_name, best_model, best_threshold, best_score, best_metrics = name, model, threshold, score, metrics

        anomaly = IsolationForest(n_estimators=110, contamination=.08, random_state=42, n_jobs=1)
        anomaly.fit(X_trainval)

        importance = self._feature_importance(best_model)
        self.bundle = {"classifier": best_model, "anomaly": anomaly, "features": FEATURES, "decision_threshold": best_threshold, "version": "3.0-generic-fallback", "runtime_mode": "generic_local_fallback"}
        self.metadata = {
            "model_name": best_name,
            "model_version": "3.0-generic-fallback",
            "dataset": "ForgeMind deterministic engineering benchmark aligned to common predictive-maintenance ranges; not real plant telemetry.",
            "dataset_rows": int(len(X)),
            "runtime_mode": "generic_local_fallback",
            "data_provenance": "deterministically generated engineering benchmark; not measured factory data",
            "license": "project-generated benchmark",
            "features": FEATURES,
            "target": "machine failure within the operating window",
            "metrics": {k: round(v, 4) if isinstance(v, float) else v for k, v in best_metrics.items()},
            "comparisons": comparisons,
            "feature_importance": importance,
            "limitations": [
                "This bundled model is an offline fallback trained on generated benchmark data, not measured factory telemetry.",
                "Install the MetroPT-3 real-data bundle for air-compressor assets or train on plant-specific labeled data.",
                "Thresholds must be validated against the target factory and machine family.",
                "Predictions support maintenance decisions and do not replace certified safety systems.",
            ],
        }
        joblib.dump(self.bundle, self.model_path)
        self.metadata_path.write_text(json.dumps(self.metadata, indent=2), encoding="utf-8")
        return self.metadata

    @staticmethod
    def _feature_importance(model) -> dict:
        values = None
        candidate = model
        if hasattr(model, "named_steps"):
            candidate = model.named_steps.get("model", model)
        if hasattr(candidate, "feature_importances_"):
            values = np.asarray(candidate.feature_importances_, dtype=float)
        elif hasattr(candidate, "coef_"):
            values = np.abs(np.asarray(candidate.coef_[0], dtype=float))
        if values is None or values.sum() == 0:
            values = np.ones(len(FEATURES), dtype=float)
        values = values / values.sum()
        return dict(sorted({name: round(float(value), 5) for name, value in zip(FEATURES, values)}.items(), key=lambda item: item[1], reverse=True))

    def predict(self, reading: dict, age_years: float, machine_type: str = "") -> dict:
        if self.bundle is None:
            self.ensure_model()
        assert self.bundle is not None
        values = np.array([[
            reading["temperature"], reading["vibration"], reading["pressure"], reading["rpm"],
            reading.get("torque", 45), reading["power"], reading["operating_hours"],
            reading["tool_wear"], age_years,
        ]], dtype=float)
        classifier = self.bundle["classifier"]
        probability = float(classifier.predict_proba(values)[0, 1])
        active_model = self.metadata.get("model_name", "generic predictive model")
        machine_family = (machine_type or "").lower()
        if self.metropt_bundle is not None and any(token in machine_family for token in ("compressor", "air production", "apu")):
            specialized = self.metropt_bundle["classifier"]
            probability = float(specialized.predict_proba(self._metropt_snapshot(reading))[0, 1])
            active_model = self.metropt_metadata.get("model_name", "MetroPT-3 air-compressor model")
        anomaly_model = self.bundle["anomaly"]
        raw_anomaly = float(-anomaly_model.score_samples(values)[0])
        anomaly = float(np.clip((raw_anomaly - .38) / .26, 0, 1))

        rule_components = {
            "temperature": float(np.clip((reading["temperature"] - 68) / 42, 0, 1.4)),
            "vibration": float(np.clip((reading["vibration"] - .28) / 1.25, 0, 1.5)),
            "pressure": float(np.clip(abs(reading["pressure"] - 31) / 22, 0, 1.2)),
            "rpm": float(np.clip(abs(reading["rpm"] - 1450) / 2100, 0, 1.2)),
            "tool_wear": float(np.clip(reading["tool_wear"] / 280, 0, 1.2)),
            "torque": float(np.clip((reading.get("torque", 45) - 48) / 95, 0, 1.2)),
        }
        engineering_risk = min(1.0, sum(rule_components.values()) / 2.65)
        blended = float(np.clip(probability * .70 + anomaly * .12 + engineering_risk * .28, .001, .995))
        health = round(max(1.0, 100 * (1 - blended)), 1)
        if blended >= .78:
            risk = "critical"
        elif blended >= .55:
            risk = "high"
        elif blended >= .30:
            risk = "warning"
        else:
            risk = "healthy"

        issue_scores = {
            "bearing degradation": reading["vibration"] / 1.05 + max(0, reading["temperature"] - 72) / 32,
            "thermal overload": max(0, reading["temperature"] - 69) / 23 + reading["power"] / 48,
            "tool wear": reading["tool_wear"] / 165 + reading.get("torque", 45) / 175,
            "pressure instability": abs(reading["pressure"] - 31) / 14,
            "speed imbalance": abs(reading["rpm"] - 1450) / 1050 + reading["vibration"] / 2.1,
        }
        issue = max(issue_scores, key=issue_scores.get) if risk != "healthy" else "normal operation"
        recommendations = {
            "bearing degradation": "Inspect bearing condition, lubrication, and shaft alignment. Reduce load until vibration returns below the configured limit.",
            "thermal overload": "Inspect cooling airflow, electrical load, and process temperature before the next production cycle.",
            "tool wear": "Replace or inspect the active tool, verify torque limits, and recalibrate the operation after replacement.",
            "pressure instability": "Inspect seals, regulator, valves, and supply pressure for leakage, blockage, or unstable control.",
            "speed imbalance": "Inspect coupling alignment, drive components, and RPM controller before continued high-speed operation.",
            "normal operation": "Continue standard monitoring and preventive-maintenance intervals.",
        }
        wear_factor = max(.05, 1 - reading["tool_wear"] / 320)
        risk_factor = max(.05, 1 - blended)
        remaining_hours = round(min(5000.0, max(8.0, 2400 * wear_factor * risk_factor + 120)), 1)
        drivers = sorted(rule_components.items(), key=lambda item: item[1], reverse=True)[:4]
        return {
            "status": "high_risk" if risk in {"critical", "high"} else "normal",
            "health_score": health,
            "failure_probability": round(blended, 4),
            "anomaly_score": round(anomaly, 4),
            "remaining_useful_hours": remaining_hours,
            "risk_level": risk,
            "likely_issue": issue,
            "recommended_action": recommendations[issue],
            "maintenance_priority": "immediate" if risk == "critical" else "high" if risk == "high" else "planned" if risk == "warning" else "routine",
            "explanation": {
                "top_drivers": [{"feature": name, "score": round(score, 3)} for name, score in drivers],
                "classifier_probability": round(probability, 4),
                "engineering_risk": round(engineering_risk, 4),
                "active_model": active_model,
                "model_runtime_mode": "trained_real_data_model" if self.metropt_bundle is not None and "MetroPT" in active_model else "generic_local_fallback",
            },
        }


predictive_service = PredictiveService()

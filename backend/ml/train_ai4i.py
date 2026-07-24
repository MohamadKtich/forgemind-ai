"""Train the optional UCI AI4I synthetic compatibility benchmark.

AI4I is an official public dataset, but it is synthetic. This script is retained for
benchmark compatibility and must not be presented as training on measured plant data.

Usage:
    python ml/train_ai4i.py path/to/ai4i2020.csv

The application already includes an offline benchmark model. This script is the
production data replacement path and intentionally requires the official CSV.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, roc_auc_score, confusion_matrix
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "ml" / "models"
FEATURES = ["temperature", "vibration", "pressure", "rpm", "torque", "power", "operating_hours", "tool_wear", "age_years"]


def main(csv_path: str) -> None:
    df = pd.read_csv(csv_path)
    required = {"Air temperature [K]", "Process temperature [K]", "Rotational speed [rpm]", "Torque [Nm]", "Tool wear [min]", "Machine failure"}
    missing = required - set(df.columns)
    if missing:
        raise SystemExit(f"Missing AI4I columns: {sorted(missing)}")
    temperature = df["Process temperature [K]"] - 273.15
    vibration_proxy = np.clip(abs(df["Torque [Nm]"] - df["Torque [Nm]"].median()) / 35 + abs(df["Rotational speed [rpm]"] - 1450) / 4000, .03, 3.5)
    pressure_proxy = 31 + (df["Air temperature [K]"] - df["Air temperature [K]"].mean()) * .8
    rpm = df["Rotational speed [rpm]"]
    torque = df["Torque [Nm]"]
    power = rpm * torque / 9550 + 5
    hours_proxy = np.linspace(100, 30000, len(df))
    tool_wear = df["Tool wear [min]"]
    age_proxy = np.clip(hours_proxy / 2200, .1, 25)
    X = np.column_stack([temperature, vibration_proxy, pressure_proxy, rpm, torque, power, hours_proxy, tool_wear, age_proxy])
    y = df["Machine failure"].astype(int).to_numpy()
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=.22, stratify=y, random_state=42)
    model = RandomForestClassifier(n_estimators=420, max_depth=16, min_samples_leaf=2, class_weight="balanced_subsample", random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    proba = model.predict_proba(X_test)[:, 1]
    precision, recall, f1, _ = precision_recall_fscore_support(y_test, pred, average="binary", zero_division=0)
    anomaly = IsolationForest(n_estimators=220, contamination=.05, random_state=42, n_jobs=-1).fit(X_train)
    metadata = {
        "model_name": "Random Forest",
        "model_version": "3.0-ai4i-synthetic",
        "dataset": "UCI AI4I 2020 synthetic predictive-maintenance benchmark",
        "dataset_rows": len(df),
        "features": FEATURES,
        "target": "Machine failure",
        "metrics": {
            "accuracy": round(float(accuracy_score(y_test, pred)), 4),
            "precision": round(float(precision), 4),
            "recall": round(float(recall), 4),
            "f1": round(float(f1), 4),
            "roc_auc": round(float(roc_auc_score(y_test, proba)), 4),
            "confusion_matrix": confusion_matrix(y_test, pred).tolist(),
        },
        "feature_importance": dict(sorted({name: round(float(value), 5) for name, value in zip(FEATURES, model.feature_importances_)}.items(), key=lambda item: item[1], reverse=True)),
        "limitations": ["Proxy mappings are used for sensor fields absent from AI4I.", "Validate against plant-specific data before operational use."],
    }
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump({"classifier": model, "anomaly": anomaly, "features": FEATURES, "version": "3.0-ai4i-synthetic", "runtime_mode": "synthetic_public_benchmark"}, MODEL_DIR / "predictive_maintenance.joblib")
    (MODEL_DIR / "predictive_maintenance.metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python ml/train_ai4i.py path/to/ai4i2020.csv")
    main(sys.argv[1])

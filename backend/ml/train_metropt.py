"""Train ForgeMind's compressor model from the real UCI MetroPT-3 dataset.

The raw time series is aggregated into one-minute operating windows. Labels mark a
reported failure interval and the configurable prediction horizon preceding it. The
split is chronological: events 1-2 are available to training, event 3 is in validation,
and event 4 is in the held-out test period. This avoids random leakage across time.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    accuracy_score,
    confusion_matrix,
    precision_recall_fscore_support,
    roc_auc_score,
    roc_curve,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

BACKEND = Path(__file__).resolve().parents[1]
FEATURES = [
    "TP2", "TP3", "H1", "DV_pressure", "Reservoirs", "Oil_temperature",
    "Motor_current", "COMP", "DV_eletric", "Towers", "MPG", "LPS",
    "Pressure_switch", "Oil_level", "Caudal_impulses",
]
ANALOG = FEATURES[:7]
DIGITAL = FEATURES[7:]
FAILURES = [
    ("2020-04-18 00:00", "2020-04-18 23:59", "air leak"),
    ("2020-05-29 23:30", "2020-05-30 06:00", "air leak"),
    ("2020-06-05 10:00", "2020-06-07 14:30", "air leak"),
    ("2020-07-15 14:30", "2020-07-15 19:00", "air leak"),
]


def read_aggregate(path: Path) -> tuple[pd.DataFrame, int]:
    pieces: list[pd.DataFrame] = []
    raw_rows = 0
    for chunk in pd.read_csv(path, chunksize=250_000):
        raw_rows += len(chunk)
        timestamp_col = next(
            (column for column in chunk.columns if column.lower() in {"timestamp", "datetime", "date_time"}),
            None,
        )
        if not timestamp_col:
            raise ValueError("MetroPT timestamp column was not found")
        missing = [column for column in FEATURES if column not in chunk.columns]
        if missing:
            raise ValueError(f"Missing MetroPT columns: {missing}")
        chunk[timestamp_col] = pd.to_datetime(chunk[timestamp_col], errors="coerce")
        selected = chunk.dropna(subset=[timestamp_col]).set_index(timestamp_col)[FEATURES]
        aggregation = {**{column: "mean" for column in ANALOG}, **{column: "max" for column in DIGITAL}}
        pieces.append(selected.resample("1min").agg(aggregation).dropna(how="all"))
    if not pieces:
        raise ValueError("MetroPT CSV contained no readable rows")
    frame = pd.concat(pieces).sort_index()
    frame = frame.groupby(frame.index).mean().interpolate(limit=5).dropna()
    return frame, raw_rows


def build_labels(index: pd.DatetimeIndex, horizon_hours: int) -> tuple[np.ndarray, np.ndarray]:
    target = np.zeros(len(index), dtype=int)
    event = np.zeros(len(index), dtype=int)
    for event_id, (start_text, end_text, _) in enumerate(FAILURES, 1):
        start = pd.Timestamp(start_text)
        end = pd.Timestamp(end_text)
        prediction_start = start - pd.Timedelta(hours=horizon_hours)
        mask = (index >= prediction_start) & (index <= end)
        target[mask] = 1
        event[mask] = event_id
    return target, event


def choose_threshold(y_true: np.ndarray, probability: np.ndarray) -> float:
    best_threshold, best_f1 = .5, -1.0
    for threshold in np.linspace(.05, .95, 181):
        _, _, f1, _ = precision_recall_fscore_support(
            y_true, probability >= threshold, average="binary", zero_division=0
        )
        if f1 > best_f1:
            best_threshold, best_f1 = float(threshold), float(f1)
    return best_threshold


def evaluate(y_true: np.ndarray, probability: np.ndarray, threshold: float) -> tuple[dict, np.ndarray]:
    prediction = probability >= threshold
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true, prediction, average="binary", zero_division=0
    )
    return {
        "accuracy": float(accuracy_score(y_true, prediction)),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "roc_auc": float(roc_auc_score(y_true, probability)),
        "confusion_matrix": confusion_matrix(y_true, prediction).tolist(),
    }, prediction


def sampled_indices(mask: np.ndarray, target: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    positive = np.where(mask & (target == 1))[0]
    negative = np.where(mask & (target == 0))[0]
    if not len(positive) or not len(negative):
        raise ValueError("Every chronological split must contain both normal and failure-horizon windows")
    negative_count = min(len(negative), max(len(positive) * 8, 5_000))
    kept_negative = rng.choice(negative, size=negative_count, replace=False)
    return np.sort(np.r_[positive, kept_negative])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", type=Path)
    parser.add_argument("--horizon-hours", type=int, default=12)
    parser.add_argument("--output", type=Path, default=BACKEND / "ml/models/metropt_air_compressor.joblib")
    parser.add_argument("--metadata", type=Path, default=BACKEND / "ml/models/metropt_air_compressor.metadata.json")
    parser.add_argument("--report-dir", type=Path, default=BACKEND / "ml/reports/metropt")
    parser.add_argument("--quick", action="store_true", help="Reduced estimators for pipeline verification, not final training")
    args = parser.parse_args()

    frame, raw_rows = read_aggregate(args.csv)
    target, event = build_labels(frame.index, args.horizon_hours)

    train_mask = frame.index < pd.Timestamp("2020-06-01")
    validation_mask = (frame.index >= pd.Timestamp("2020-06-01")) & (frame.index < pd.Timestamp("2020-07-01"))
    test_mask = frame.index >= pd.Timestamp("2020-07-01")
    rng = np.random.default_rng(42)
    train_index = sampled_indices(np.asarray(train_mask), target, rng)
    validation_index = sampled_indices(np.asarray(validation_mask), target, rng)
    test_index = sampled_indices(np.asarray(test_mask), target, rng)

    if not np.any(event[train_index] == 1) or not np.any(event[train_index] == 2):
        raise SystemExit("Training period does not contain the first two published failure reports")
    if not np.any(event[validation_index] == 3):
        raise SystemExit("Validation period does not contain the third published failure report")
    if not np.any(event[test_index] == 4):
        raise SystemExit("Held-out test period does not contain the fourth published failure report")

    forest_estimators = 40 if args.quick else 320
    boosting_iterations = 60 if args.quick else 260
    models = {
        "Logistic Regression": Pipeline([
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
            ("model", LogisticRegression(max_iter=2_000, class_weight="balanced", C=.6)),
        ]),
        "Random Forest": RandomForestClassifier(
            n_estimators=forest_estimators, max_depth=16, min_samples_leaf=3,
            class_weight="balanced_subsample", random_state=42, n_jobs=-1,
        ),
        "Histogram Gradient Boosting": HistGradientBoostingClassifier(
            max_iter=boosting_iterations, learning_rate=.055, max_leaf_nodes=31,
            l2_regularization=1.2, random_state=42,
        ),
    }

    comparisons: list[dict] = []
    best: tuple | None = None
    best_score = -1.0
    sample_weight = np.where(
        target[train_index] == 1,
        max(2.0, (target[train_index] == 0).sum() / max(1, (target[train_index] == 1).sum()) * .45),
        1.0,
    )
    for name, model in models.items():
        try:
            model.fit(frame.iloc[train_index], target[train_index], model__sample_weight=sample_weight)
        except (TypeError, ValueError):
            try:
                model.fit(frame.iloc[train_index], target[train_index], sample_weight=sample_weight)
            except TypeError:
                model.fit(frame.iloc[train_index], target[train_index])
        validation_probability = model.predict_proba(frame.iloc[validation_index])[:, 1]
        threshold = choose_threshold(target[validation_index], validation_probability)
        test_probability = model.predict_proba(frame.iloc[test_index])[:, 1]
        metrics, _ = evaluate(target[test_index], test_probability, threshold)
        row = {"model": name, "decision_threshold": threshold, **metrics}
        comparisons.append(row)
        score = metrics["f1"] * .6 + metrics["roc_auc"] * .4
        if score > best_score:
            best = (name, model, threshold, metrics, test_probability)
            best_score = score

    assert best is not None
    name, model, threshold, metrics, test_probability = best
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.metadata.parent.mkdir(parents=True, exist_ok=True)
    args.report_dir.mkdir(parents=True, exist_ok=True)

    bundle = {
        "classifier": model,
        "features": FEATURES,
        "decision_threshold": threshold,
        "machine_family": "air_compressor",
        "runtime_adapter": "metropt_snapshot_v1",
        "version": "3.0-metropt",
        "runtime_mode": "trained_real_data_model",
    }
    joblib.dump(bundle, args.output)
    metadata = {
        "available": True,
        "installed": True,
        "runtime_mode": "trained_real_data_model",
        "model_name": f"{name} · MetroPT-3 Air Compressor",
        "model_version": "3.0-metropt",
        "dataset": "UCI MetroPT-3, real operational metro air-compressor sensor data",
        "dataset_license": "CC BY 4.0",
        "dataset_doi": "10.24432/C5VW3R",
        "raw_rows": raw_rows,
        "aggregated_rows": len(frame),
        "features": FEATURES,
        "target": f"reported failure active or beginning within {args.horizon_hours} hours",
        "metrics": metrics,
        "decision_threshold": threshold,
        "comparisons": comparisons,
        "split": "Chronological: before June 2020 train, June validation, July onward held-out test",
        "split_rows": {
            "train": len(train_index), "validation": len(validation_index), "test": len(test_index)
        },
        "failure_intervals": FAILURES,
        "quick_verification_run": bool(args.quick),
        "limitations": [
            "This specialized model is selected only for compressor-like assets.",
            "The generic ForgeMind sensor payload is adapted to MetroPT fields; production should ingest native compressor signals or validate the adapter.",
            "Four published failure reports limit statistical certainty; plant-specific threshold validation is mandatory.",
        ],
    }
    args.metadata.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    prediction = test_probability >= threshold
    ConfusionMatrixDisplay(
        confusion_matrix(target[test_index], prediction), display_labels=["normal", "failure horizon"]
    ).plot(cmap="Blues")
    plt.title("MetroPT held-out period confusion matrix")
    plt.tight_layout()
    plt.savefig(args.report_dir / "confusion_matrix.png", dpi=180)
    plt.close()

    false_positive_rate, true_positive_rate, _ = roc_curve(target[test_index], test_probability)
    plt.figure(figsize=(6, 5))
    plt.plot(false_positive_rate, true_positive_rate, label=f"AUC {metrics['roc_auc']:.3f}")
    plt.plot([0, 1], [0, 1], "--", alpha=.45)
    plt.xlabel("False positive rate")
    plt.ylabel("True positive rate")
    plt.title("MetroPT held-out period ROC")
    plt.legend()
    plt.tight_layout()
    plt.savefig(args.report_dir / "roc_curve.png", dpi=180)
    plt.close()
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()

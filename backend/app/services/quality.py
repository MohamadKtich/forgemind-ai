from __future__ import annotations
from pathlib import Path
from uuid import uuid4
import json
import cv2
import joblib
import numpy as np
from ..config import get_settings
from .vision_features import quality_feature_vector

ALLOWED = {"image/jpeg", "image/png", "image/webp"}


class QualityService:
    def __init__(self):
        self.settings = get_settings()
        self.root = Path(self.settings.storage_dir) / "inspections"
        self.root.mkdir(parents=True, exist_ok=True)
        self.model_path = Path(self.settings.quality_model_path)
        if not self.model_path.is_absolute():
            self.model_path = Path(__file__).resolve().parents[2] / self.model_path
        self.metadata_path = Path(self.settings.quality_metadata_path)
        if not self.metadata_path.is_absolute():
            self.metadata_path = Path(__file__).resolve().parents[2] / self.metadata_path
        self.bundle: dict | None = None
        self.metadata: dict = {}
        self.load_model()

    def load_model(self) -> None:
        self.bundle = None
        self.metadata = {
            "available": False,
            "runtime_mode": "computer_vision_fallback",
            "model_name": "ForgeMind Surface Inspector",
            "dataset": "No trained KSDD bundle installed",
            "limitations": ["Uses deterministic surface and golden-reference analysis until a trained bundle is installed."],
        }
        if not self.model_path.exists():
            return
        try:
            bundle = joblib.load(self.model_path)
            if not isinstance(bundle, dict) or "classifier" not in bundle:
                return
            self.bundle = bundle
            if self.metadata_path.exists():
                self.metadata = json.loads(self.metadata_path.read_text(encoding="utf-8"))
            self.metadata.update({"available": True, "runtime_mode": "trained_real_data_model"})
        except Exception as exc:
            self.metadata["load_error"] = str(exc)

    def model_status(self) -> dict:
        return {**self.metadata, "model_path": str(self.model_path), "installed": self.bundle is not None}

    def _decode(self, raw: bytes, content_type: str) -> np.ndarray:
        if content_type not in ALLOWED:
            raise ValueError("Only JPEG, PNG, and WEBP images are supported")
        if len(raw) > self.settings.max_upload_mb * 1024 * 1024:
            raise ValueError(f"File exceeds {self.settings.max_upload_mb} MB")
        image = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
        if image is None or min(image.shape[:2]) < 120:
            raise ValueError("Image is invalid or too small. Use an image at least 120×120 pixels")
        return image

    @staticmethod
    def _normalize(image: np.ndarray) -> np.ndarray:
        max_side = 1280
        h, w = image.shape[:2]
        if max(h, w) > max_side:
            scale = max_side / max(h, w)
            image = cv2.resize(image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
        return image

    @staticmethod
    def _reference_difference(image: np.ndarray, reference: np.ndarray) -> tuple[np.ndarray, dict]:
        reference = cv2.resize(reference, (image.shape[1], image.shape[0]), interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        ref_gray = cv2.cvtColor(reference, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        ref_gray = cv2.GaussianBlur(ref_gray, (5, 5), 0)
        diff = cv2.absdiff(gray, ref_gray)
        diff = cv2.normalize(diff, None, 0, 255, cv2.NORM_MINMAX)
        _, mask = cv2.threshold(diff, max(24, int(np.percentile(diff, 91))), 255, cv2.THRESH_BINARY)
        metrics = {"mean_difference": round(float(diff.mean()) / 255, 4), "p95_difference": round(float(np.percentile(diff, 95)) / 255, 4)}
        return mask, metrics

    @staticmethod
    def _surface_anomaly(image: np.ndarray, percentile: float = 92.5) -> tuple[np.ndarray, dict]:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        illumination = cv2.GaussianBlur(gray, (0, 0), 21)
        residual = cv2.absdiff(gray, illumination)
        edges = cv2.Canny(gray, 45, 135)
        color_dev = cv2.absdiff(lab[:, :, 1], cv2.GaussianBlur(lab[:, :, 1], (0, 0), 17))
        combined = cv2.addWeighted(residual, .55, edges, .30, 0)
        combined = cv2.addWeighted(combined, .78, color_dev, .22, 0)
        threshold = max(18, int(np.percentile(combined, percentile)))
        _, mask = cv2.threshold(combined, threshold, 255, cv2.THRESH_BINARY)
        metrics = {
            "surface_texture_score": round(float(residual.mean()) / 255, 4),
            "edge_density": round(float((edges > 0).mean()), 4),
            "color_variation": round(float(color_dev.mean()) / 255, 4),
        }
        return mask, metrics

    @staticmethod
    def _extract_defects(image: np.ndarray, mask: np.ndarray) -> tuple[list[dict], list[str], float]:
        h, w = image.shape[:2]
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        boxes: list[dict] = []
        labels: list[str] = []
        total_area = float(h * w)
        anomalous_area = 0.0
        for contour in sorted(contours, key=cv2.contourArea, reverse=True):
            area = float(cv2.contourArea(contour))
            if area < total_area * .00035 or area > total_area * .32:
                continue
            x, y, bw, bh = cv2.boundingRect(contour)
            aspect = max(bw, bh) / max(1, min(bw, bh))
            perimeter = cv2.arcLength(contour, True)
            circularity = 4 * np.pi * area / max(1, perimeter * perimeter)
            roi = image[y:y+bh, x:x+bw]
            saturation = float(cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)[:, :, 1].mean()) if roi.size else 0
            if aspect > 4.2:
                label = "scratch"
            elif circularity > .58 and max(bw, bh) < min(h, w) * .18:
                label = "pit_or_dent"
            elif saturation > 82:
                label = "stain_or_discoloration"
            elif x <= 4 or y <= 4 or x + bw >= w - 4 or y + bh >= h - 4:
                label = "edge_damage"
            else:
                label = "surface_irregularity"
            score = min(.99, .46 + area / total_area * 9 + min(aspect, 8) * .025)
            boxes.append({"x": x, "y": y, "width": bw, "height": bh, "label": label, "confidence": round(float(score), 3)})
            labels.append(label)
            anomalous_area += area
            if len(boxes) >= 12:
                break
        coverage = anomalous_area / total_area
        anomaly_score = float(np.clip(coverage * 10 + len(boxes) * .035, 0, 1))
        return boxes, sorted(set(labels)), anomaly_score

    def _trained_probability(self, image: np.ndarray) -> float | None:
        if self.bundle is None:
            return None
        features = quality_feature_vector(image).reshape(1, -1)
        classifier = self.bundle["classifier"]
        if hasattr(classifier, "predict_proba"):
            classes = list(classifier.classes_)
            positive_index = classes.index(1) if 1 in classes else len(classes) - 1
            return float(classifier.predict_proba(features)[0, positive_index])
        if hasattr(classifier, "decision_function"):
            score = float(np.asarray(classifier.decision_function(features)).reshape(-1)[0])
            return float(1 / (1 + np.exp(-score)))
        return float(classifier.predict(features)[0])

    def inspect(self, raw: bytes, content_type: str, filename: str, reference_raw: bytes | None = None, reference_content_type: str | None = None) -> dict:
        image = self._normalize(self._decode(raw, content_type))
        reference = None
        mode = "surface_anomaly"
        if reference_raw:
            reference = self._normalize(self._decode(reference_raw, reference_content_type or "image/jpeg"))
            mask, measurements = self._reference_difference(image, reference)
            mode = "reference_comparison"
        else:
            mask, measurements = self._surface_anomaly(image)
        boxes, defect_types, anomaly_score = self._extract_defects(image, mask)
        base_score = anomaly_score
        if mode == "reference_comparison":
            base_score = max(base_score, measurements.get("mean_difference", 0) * 3.5, measurements.get("p95_difference", 0) * 1.45)

        model_probability = self._trained_probability(image)
        threshold = float((self.bundle or {}).get("decision_threshold", .5))
        if model_probability is not None:
            defective = model_probability >= threshold
            combined_score = max(base_score, model_probability * .85)
            status = "defective" if defective else "good"
            confidence = model_probability if defective else 1 - model_probability
            measurements["trained_model_probability"] = round(model_probability, 4)
            if defective and not boxes:
                mask, extra = self._surface_anomaly(image, percentile=88.5)
                boxes, defect_types, anomaly_score = self._extract_defects(image, mask)
                measurements.update({f"localization_{k}": v for k, v in extra.items()})
            if defective and not defect_types:
                defect_types = [str((self.bundle or {}).get("positive_label", "surface_defect"))]
        else:
            combined_score = base_score
            status = "defective" if boxes and base_score >= .10 else "good"
            confidence = float(np.clip(.74 + abs(base_score - .10) * 1.35, .68, .99))

        if status == "good":
            defect_types = []
            boxes = []
            confidence = float(np.clip(confidence if model_probability is not None else .78 + (1 - base_score) * .17, .55, .99))
        else:
            confidence = float(np.clip(confidence, .55, .99))

        annotated = image.copy()
        overlay = np.zeros_like(image)
        overlay[:, :, 2] = mask
        annotated = cv2.addWeighted(annotated, .90, overlay, .18, 0)
        for box in boxes:
            x, y, bw, bh = box["x"], box["y"], box["width"], box["height"]
            cv2.rectangle(annotated, (x, y), (x + bw, y + bh), (35, 98, 245), 2)
            cv2.putText(annotated, box["label"].replace("_", " "), (x, max(18, y - 7)), cv2.FONT_HERSHEY_SIMPLEX, .48, (35, 225, 245), 1, cv2.LINE_AA)
        stamp = uuid4().hex
        original_path = self.root / f"{stamp}-original.jpg"
        annotated_path = self.root / f"{stamp}-annotated.jpg"
        reference_path = self.root / f"{stamp}-reference.jpg" if reference is not None else None
        cv2.imwrite(str(original_path), image, [int(cv2.IMWRITE_JPEG_QUALITY), 93])
        cv2.imwrite(str(annotated_path), annotated, [int(cv2.IMWRITE_JPEG_QUALITY), 93])
        if reference is not None and reference_path is not None:
            cv2.imwrite(str(reference_path), reference, [int(cv2.IMWRITE_JPEG_QUALITY), 93])
        return {
            "status": status,
            "confidence": round(confidence, 4),
            "anomaly_score": round(float(combined_score), 4),
            "defect_types": defect_types,
            "bounding_boxes": boxes,
            "measurements": measurements,
            "inspection_mode": mode,
            "original_path": str(original_path),
            "reference_path": str(reference_path) if reference_path else None,
            "annotated_path": str(annotated_path),
            "engine": self.metadata.get("model_name", "ForgeMind Vision Surface Inspector 3.0"),
            "model_runtime_mode": self.metadata.get("runtime_mode", "computer_vision_fallback"),
        }


quality_service = QualityService()

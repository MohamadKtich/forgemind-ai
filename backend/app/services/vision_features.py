from __future__ import annotations
import cv2
import numpy as np

IMAGE_SIZE = 128


def quality_feature_vector(image: np.ndarray) -> np.ndarray:
    """Extract deterministic HOG, intensity, edge, and color features.

    The same feature contract is used by the KSDD real-data trainer and the
    runtime quality service, preventing the rather common "trained one thing,
    deployed another" form of industrial optimism.
    """
    image = cv2.resize(image, (IMAGE_SIZE, IMAGE_SIZE), interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)
    hog = cv2.HOGDescriptor(
        (IMAGE_SIZE, IMAGE_SIZE), (16, 16), (8, 8), (8, 8), 9,
        1, -1, 0, 0.2, False, 64, True,
    ).compute(gray).reshape(-1)
    edges = cv2.Canny(gray, 45, 135)
    lap = cv2.Laplacian(gray, cv2.CV_32F)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    hist_parts = []
    for channel, bins, limit in [(0, 18, 180), (1, 16, 256), (2, 16, 256)]:
        hist = cv2.calcHist([hsv], [channel], None, [bins], [0, limit]).reshape(-1)
        hist /= max(float(hist.sum()), 1.0)
        hist_parts.append(hist)
    stats = np.array([
        gray.mean() / 255.0,
        gray.std() / 255.0,
        float((edges > 0).mean()),
        float(np.abs(lap).mean()) / 255.0,
        float(np.percentile(gray, 10)) / 255.0,
        float(np.percentile(gray, 90)) / 255.0,
    ], dtype=np.float32)
    return np.concatenate([hog.astype(np.float32), *[h.astype(np.float32) for h in hist_parts], stats])

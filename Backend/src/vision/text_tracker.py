"""As caixas OCR seguem pontos visuais, com validade curta entre novas leituras."""

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class TextRegion:
    text: str
    kind: str
    polygon: np.ndarray
    points: np.ndarray
    timestamp: float
    exact_match: bool = False
    expected_prefix: str | None = None


def follow_groups(previous_gray, current_gray, groups):
    """Compartilhe as pirâmides de fluxo óptico entre todas as caixas de texto."""
    if not groups:
        return []
    points = np.concatenate(groups).astype(np.float32)
    next_points, status, _ = cv2.calcOpticalFlowPyrLK(
        previous_gray, current_gray, points, None, winSize=(31, 31), maxLevel=4,
        criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 25, 0.03),
    )
    if next_points is None:
        return [None] * len(groups)
    back_points, reverse_status, _ = cv2.calcOpticalFlowPyrLK(
        current_gray, previous_gray, next_points, points.copy(),
        winSize=(31, 31), maxLevel=4, flags=cv2.OPTFLOW_USE_INITIAL_FLOW,
        criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 25, 0.03),
    )
    if back_points is None:
        return [None] * len(groups)
    valid = (status.ravel() == 1) & (reverse_status.ravel() == 1)
    valid &= np.linalg.norm(points.reshape(-1, 2) - back_points.reshape(-1, 2), axis=1) < 2.5
    results = []
    offset = 0
    for group in groups:
        segment = slice(offset, offset + len(group))
        offset += len(group)
        keep = valid[segment]
        if keep.sum() < 3:
            results.append(None)
            continue
        before = points[segment][keep].reshape(-1, 2)
        after = next_points[segment][keep].reshape(-1, 2)
        matrix, inliers = cv2.estimateAffinePartial2D(before, after, method=cv2.RANSAC, ransacReprojThreshold=3)
        if matrix is None or inliers is None or inliers.sum() < 3 or not 0.7 <= np.linalg.norm(matrix[:, 0]) <= 1.4:
            results.append(None)
            continue
        results.append((matrix, after[inliers.ravel() == 1].reshape(-1, 1, 2)))
    return results


class TextTracker:
    def __init__(self):
        self.regions: dict[int, list[TextRegion]] = {}
        self.previous_gray = None

    def update(self, gray, active_ids, timestamp):
        pending = []
        for track_id in list(self.regions):
            if track_id not in active_ids:
                del self.regions[track_id]
                continue
            for region in self.regions[track_id]:
                if timestamp - region.timestamp > 4.0 or self.previous_gray is None:
                    continue
                pending.append((track_id, region))
            self.regions[track_id] = []
        motions = follow_groups(self.previous_gray, gray, [region.points for _, region in pending])
        for (track_id, region), motion in zip(pending, motions):
            if motion is not None:
                matrix, region.points = motion
                region.polygon = cv2.transform(region.polygon.reshape(1, -1, 2), matrix)[0]
                self.regions[track_id].append(region)
        self.previous_gray = gray

    def accept(self, result, gray, timestamp, matcher, expected_prefix=None, prefix_confirmed=False):
        regions = []
        if expected_prefix is not None:
            expected_prefix = str(expected_prefix)
        for reading in result.readings:
            kind = getattr(reading, "kind", None) or matcher.classify_text(reading.text)
            if kind == "TEXTO":
                continue
            polygon = np.array(reading.polygon, dtype=np.float32)
            mask = np.zeros(result.gray.shape, dtype=np.uint8)
            cv2.fillConvexPoly(mask, polygon.astype(np.int32), 255)
            points = cv2.goodFeaturesToTrack(result.gray, maxCorners=24, qualityLevel=0.015, minDistance=3, mask=mask)
            if points is None or len(points) < 3:
                continue
            exact_match = (kind == "PREFIXO" and expected_prefix is not None
                           and (prefix_confirmed or (reading.confidence >= 0.5 and reading.text.strip() == expected_prefix)))
            visible_text = reading.text if reading.confidence >= 0.2 else "ILEGIVEL"
            regions.append(TextRegion(visible_text, kind, polygon, points, result.timestamp, exact_match, expected_prefix if kind == "PREFIXO" else None))
        if timestamp > result.timestamp:
            motions = follow_groups(result.gray, gray, [region.points for region in regions])
            tracked = []
            for region, motion in zip(regions, motions):
                if motion is not None:
                    matrix, region.points = motion
                    region.polygon = cv2.transform(region.polygon.reshape(1, -1, 2), matrix)[0]
                    tracked.append(region)
            regions = tracked
        kinds = {region.kind for region in regions}
        previous = [r for r in self.regions.get(result.track_id, []) if r.kind not in kinds]
        self.regions[result.track_id] = previous + regions

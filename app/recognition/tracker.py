import time
from dataclasses import dataclass, field
from collections import Counter
import numpy as np


def iou(box_a, box_b) -> float:
    ax1, ay1, ax2, ay2 = box_a[:4]
    bx1, by1, bx2, by2 = box_b[:4]

    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)

    inter_area = max(0, inter_x2 - inter_x1) * max(0, inter_y2 - inter_y1)
    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)

    union = area_a + area_b - inter_area
    return inter_area / union if union > 0 else 0.0


@dataclass
class PlateTrack:
    last_box: tuple
    votes: list[tuple[str, float]] = field(default_factory=list)
    last_seen: float = field(default_factory=time.time)
    best_crop: np.ndarray | None = None
    best_crop_conf: float = 0.0

    def add_vote(self, text: str, confidence: float, box: tuple, crop: np.ndarray) -> None:
        self.votes.append((text, confidence))
        self.last_box = box
        self.last_seen = time.time()

        # сохраняем кроп с максимальным OCR confidence — вероятно, самый читаемый
        if crop is not None and confidence > self.best_crop_conf:
            self.best_crop = crop.copy()
            self.best_crop_conf = confidence

    def best_guess(self) -> tuple[str, float] | None:
        if not self.votes:
            return None
        texts = [t for t, _ in self.votes if t]
        if not texts:
            return None
        most_common_text, count = Counter(texts).most_common(1)[0]
        avg_conf = sum(c for t, c in self.votes if t == most_common_text) / count
        return most_common_text, avg_conf


class PlateTracker:
    """
    Упрощённый трекер по IoU между bbox соседних кадров.
    Не заменяет полноценный object tracking, но для одиночной сцены
    (парковка/шлагбаум) этого достаточно, чтобы отличать разные проезды.
    """

    def __init__(self, iou_threshold: float = 0.3, track_timeout_sec: float = 3.0):
        self.iou_threshold = iou_threshold
        self.track_timeout_sec = track_timeout_sec
        self.tracks: dict[int, PlateTrack] = {}
        self._next_id = 0

    def update(self, box: tuple, text: str | None, confidence: float, crop: np.ndarray = None) -> int:
        """Находит существующий трек по IoU или создаёт новый. Возвращает track_id."""
        best_match_id = None
        best_iou = self.iou_threshold

        for track_id, track in self.tracks.items():
            score = iou(box, track.last_box)
            if score > best_iou:
                best_iou = score
                best_match_id = track_id

        if best_match_id is None:
            best_match_id = self._next_id
            self._next_id += 1
            self.tracks[best_match_id] = PlateTrack(last_box=box)

        self.tracks[best_match_id].add_vote(text, confidence, box, crop=crop)
        return best_match_id

    def pop_finished_tracks(self) -> list[PlateTrack]:
        """Возвращает и удаляет треки, которые давно не обновлялись (машина уехала)."""
        now = time.time()
        finished = []
        for track_id in list(self.tracks.keys()):
            track = self.tracks[track_id]
            if now - track.last_seen > self.track_timeout_sec:
                finished.append(track)
                del self.tracks[track_id]
        return finished
"""Определение наличия движения в кадре (вычитание фона MOG2)."""

import cv2


class MotionDetector:
    """
    Детекция движения через вычитание фона (MOG2).
    Возвращает True, если в кадре есть контуры площадью больше threshold_area.
    """

    def __init__(self, threshold_area: int = 1500):
        """Создаёт MOG2-вычитатель фона и сохраняет порог площади движения."""
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=500, varThreshold=16, detectShadows=False
        )
        self.threshold_area = threshold_area

    def has_motion(self, frame) -> bool:
        """True, если в кадре есть контуры движения крупнее threshold_area."""
        mask = self.bg_subtractor.apply(frame)
        # убираем шум мелкими эрозией/дилатацией
        mask = cv2.erode(mask, None, iterations=1)
        mask = cv2.dilate(mask, None, iterations=2)

        contours, _ = cv2.findContours(
            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        return any(cv2.contourArea(c) > self.threshold_area for c in contours)
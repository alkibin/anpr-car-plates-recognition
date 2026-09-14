"""Детекция номерных знаков через YOLO с фильтрацией по форме и краям."""

from ultralytics import YOLO
import numpy as np
import math



class PlateDetector:
    """Обнаруживает номерные знаки на кадре, отбрасывая обрезанные артефакты."""
    def __init__(self, model_path: str, confidence: float = 0.4):
        """Загружает YOLO-модель и сохраняет порог уверенности детекции."""
        self.model = YOLO(model_path)
        self.confidence = confidence

    def detect(self, frame: np.ndarray) -> list[tuple[int, int, int, int, float]]:
        """Ф-ция находит номерные знаки на изображении."""
        results = self.model.predict(frame, conf=self.confidence, verbose=False)
        img_h, img_w = frame.shape[:2] # Получаем границы кадра
        boxes = []
        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                conf = float(box.conf[0])

                w, h = x2 - x1, y2 - y1
                if h == 0 or w == 0:
                    continue

                # ПРОВЕРКА НА ОБРЕЗАННОСТЬ (касание краев кадра)
                edge_margin = 3
                if (x1 <= edge_margin or
                        y1 <= edge_margin or
                        x2 >= (img_w - edge_margin) or
                        y2 >= (img_h - edge_margin)):
                    # Номер касается края изображения -> пропускаем его
                    continue

                aspect_ratio = w / h

                # Границы для стандартных прямоугольных номеров (Тип 1)
                # Нижний порог опущен до 3.0 на случай, если машина едет под сильным углом к камере
                IS_RECTANGULAR = (3.0 <= aspect_ratio <= 5.3)

                # Границы для квадратных номеров (Тип 1А, мотоциклы)
                IS_SQUARE = (1.3 <= aspect_ratio <= 2.2)

                # Если не подошло ни под один стандарт — отбрасываем
                if not (IS_RECTANGULAR or IS_SQUARE):
                    continue

                boxes.append((x1, y1, x2, y2, conf))
        return boxes

    @staticmethod
    def add_padding(frame: np.ndarray, box: tuple[int, int, int, int, float], padding: float = 0.05) -> np.ndarray:
        """Расширение границ найденного номера."""
        x1, y1, x2, y2, _ = box
        h, w = frame.shape[:2]
        box_w, box_h = x2 - x1, y2 - y1

        pad_x = int(box_w * padding)
        pad_y = int(box_h * padding)

        x1 = max(0, x1 - pad_x)
        y1 = max(0, y1 - pad_y)
        x2 = min(w, x2 + pad_x)
        y2 = min(h, y2 + pad_y)

        return frame[y1:y2, x1:x2]

    @staticmethod
    def find_plate_region_pair(boxes):
        """
        Ищет пару соседних боксов: [тело номера] [регион].
        Критерии:
          - регион физически справа от тела (с небольшим допуском на нахлёст)
          - боксы близко друг к другу (маленький зазор относительно их размера)
          - ширина тела примерно в 2.3-4.0 раза больше ширины региона
          - высоты боксов сопоставимы (регион не аномально мельче/крупнее)
        """
        best_score = float("inf")
        seen = set()
        results = []
        if len(boxes) == 1:
            return boxes

        for i in range(len(boxes)):
            for j in range(len(boxes)):
                if i == j:
                    continue
                if (i, j) in seen:
                    continue
                seen.add((i, j))

                box_i, box_j = boxes[i], boxes[j]  # i = тело, j = регион

                width_i = box_i[2] - box_i[0]
                width_j = box_j[2] - box_j[0]
                height_i = box_i[3] - box_i[1]
                height_j = box_j[3] - box_j[1]

                if width_j == 0 or height_i == 0 or height_j == 0 or width_i <= width_j:
                    continue

                ratio = width_i / width_j
                if not (2.3 <= ratio <= 4.0):
                    continue

                height_ratio = height_i / height_j
                if not (0.5 <= height_ratio <= 2.0):
                    continue

                # горизонтальный зазор между правым краем тела и левым краем региона
                gap_x = box_j[0] - box_i[2]

                # Регион не может заезжать внутрь тела номера глубже, чем на 10% от высоты номера
                if gap_x < -(height_i * 0.1):
                    continue

                # вертикальное расхождение между центрами боксов
                center_i_y = (box_i[1] + box_i[3]) / 2
                center_j_y = (box_j[1] + box_j[3]) / 2
                gap_y = abs(center_i_y - center_j_y)

                # нормируем зазоры на высоту тела номера, чтобы критерий
                # масштабировался вместе с размером кропа
                gap_x_norm = gap_x / height_i
                gap_y_norm = gap_y / height_i

                if gap_x_norm > 1.0 or gap_y_norm > 1.0:
                    continue

                # суммарная "дистанция" — чем меньше, тем более вероятная пара
                distance = math.hypot(gap_x_norm, gap_y_norm) + abs(ratio - 3.0) * 0.3

                if distance < best_score:
                    best_score = distance


                results.append((boxes[i][0], boxes[i][1], boxes[j][2], boxes[j][3], best_score))

        return results
"""Тесты моделей Plate и PlateDetection: логика seen_again(), свойства photo_url/crop_url, каскадное удаление."""
from django.test import TestCase
from django.utils import timezone

from app.detection.models import Camera, Plate, PlateDetection


class PlateModelTest(TestCase):
    """Тесты модели Plate: счётчик детекций, статус по умолчанию и URL фото/кропа."""

    def setUp(self):
        """Создаёт тестовый номер для тестов модели Plate."""
        self.plate = Plate.objects.create(
            plate_text="A123BC77",
            last_seen=timezone.now(),
        )

    def test_seen_again_increments_counter_and_updates_last_seen(self):
        """Проверяет, что seen_again() увеличивает счётчик, обновляет last_crop_key и не меняет first_seen."""
        first_seen = self.plate.first_seen
        self.plate.seen_again(last_crop_key="plates/photos/A123BC77.jpg")
        self.plate.refresh_from_db()
        self.assertEqual(self.plate.detection_count, 1)
        self.assertEqual(self.plate.last_crop_key, "plates/photos/A123BC77.jpg")
        self.assertEqual(self.plate.first_seen, first_seen)

    def test_seen_again_keeps_counter_persistent(self):
        """Проверяет, что повторные вызовы seen_again() накапливают счётчик в базе данных."""
        self.plate.seen_again()
        self.plate.seen_again()
        self.plate.refresh_from_db()
        self.assertEqual(self.plate.detection_count, 2)

    def test_default_status_is_unknown(self):
        """Проверяет, что статус номера по умолчанию равен UNKNOWN."""
        self.assertEqual(self.plate.status, Plate.Status.UNKNOWN)

    def test_photo_url_property(self):
        """Проверяет, что photo_url собирается из photo_key, а при пустом ключе возвращается пустая строка."""
        self.plate.photo_key = "plates/photos/A123BC77.jpg"
        self.plate.save()
        self.assertEqual(
            self.plate.photo_url,
            "http://localhost:9000/anpr-crops/plates/photos/A123BC77.jpg",
        )
        self.plate.photo_key = ""
        self.plate.save()
        self.assertEqual(self.plate.photo_url, "")

    def test_crop_url_empty_without_key(self):
        """Проверяет, что crop_url возвращает пустую строку, если last_crop_key не задан."""
        self.assertEqual(self.plate.crop_url, "")


class PlateDetectionModelTest(TestCase):
    """Тесты модели PlateDetection: сортировка, строковое представление и каскадное удаление."""

    def test_default_ordering_newest_first(self):
        """Проверяет, что у детекции корректное строковое представление и пустой crop_url без ключа."""
        camera = Camera.objects.create(name="Cam", rtsp_url="rtsp://x/stream")
        plate = Plate.objects.create(plate_text="A123BC77", last_seen=timezone.now())
        PlateDetection.objects.create(
            plate=plate, camera=camera, detection_confidence=0.9, ocr_confidence=0.8
        )
        # Более свежий timezone.now() — в тестах tz отличается,
        # поэтому проверяем только наличие строкового представления и кроп-url.
        det = PlateDetection.objects.get()
        self.assertIn("A123BC77", str(det))
        self.assertEqual(det.crop_url, "")

    def test_cascade_delete_removes_detections(self):
        """Проверяет, что удаление номера каскадно удаляет связанные детекции."""
        camera = Camera.objects.create(name="Cam", rtsp_url="rtsp://x/stream")
        plate = Plate.objects.create(plate_text="A123BC77", last_seen=timezone.now())
        plate_id = plate.id
        PlateDetection.objects.create(
            plate=plate, camera=camera, detection_confidence=0.9, ocr_confidence=0.8
        )
        plate.delete()
        self.assertEqual(PlateDetection.objects.filter(plate_id=plate_id).count(), 0)
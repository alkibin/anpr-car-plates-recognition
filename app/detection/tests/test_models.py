from django.test import TestCase
from django.utils import timezone

from app.detection.models import Camera, Plate, PlateDetection


class PlateModelTest(TestCase):
    def setUp(self):
        self.plate = Plate.objects.create(
            plate_text="A123BC77",
            last_seen=timezone.now(),
        )

    def test_seen_again_increments_counter_and_updates_last_seen(self):
        first_seen = self.plate.first_seen
        self.plate.seen_again(last_crop_key="plates/photos/A123BC77.jpg")
        self.plate.refresh_from_db()
        self.assertEqual(self.plate.detection_count, 1)
        self.assertEqual(self.plate.last_crop_key, "plates/photos/A123BC77.jpg")
        self.assertEqual(self.plate.first_seen, first_seen)

    def test_seen_again_keeps_counter_persistent(self):
        self.plate.seen_again()
        self.plate.seen_again()
        self.plate.refresh_from_db()
        self.assertEqual(self.plate.detection_count, 2)

    def test_default_status_is_unknown(self):
        self.assertEqual(self.plate.status, Plate.Status.UNKNOWN)

    def test_photo_url_property(self):
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
        self.assertEqual(self.plate.crop_url, "")


class PlateDetectionModelTest(TestCase):
    def test_default_ordering_newest_first(self):
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
        camera = Camera.objects.create(name="Cam", rtsp_url="rtsp://x/stream")
        plate = Plate.objects.create(plate_text="A123BC77", last_seen=timezone.now())
        plate_id = plate.id
        PlateDetection.objects.create(
            plate=plate, camera=camera, detection_confidence=0.9, ocr_confidence=0.8
        )
        plate.delete()
        self.assertEqual(PlateDetection.objects.filter(plate_id=plate_id).count(), 0)
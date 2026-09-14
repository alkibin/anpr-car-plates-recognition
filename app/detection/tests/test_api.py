from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from app.detection.models import Camera, Plate, PlateDetection


class ApiTestBase(TestCase):
    def setUp(self):
        self.camera = Camera.objects.create(
            name="Gate1", rtsp_url="rtsp://localhost:8554/stream"
        )
        self.plate = Plate.objects.create(
            plate_text="A123BC77",
            last_seen=timezone.now(),
            last_crop_key="plates/2026/09/14/A123BC77_latest.jpg",
            photo_key="plates/photos/A123BC77.jpg",
            detection_count=2,
        )
        self.det1 = PlateDetection.objects.create(
            plate=self.plate,
            camera=self.camera,
            detection_confidence=0.92,
            ocr_confidence=0.85,
            crop_object_key="plates/2026/09/14/A123BC77_1.jpg",
        )
        self.det2 = PlateDetection.objects.create(
            plate=self.plate,
            camera=self.camera,
            detection_confidence=0.81,
            ocr_confidence=0.74,
            crop_object_key="plates/2026/09/14/A123BC77_2.jpg",
        )
        self.other_plate = Plate.objects.create(
            plate_text="M567EF190",
            last_seen=timezone.now(),
            status=Plate.Status.DENIED,
            detection_count=1,
        )
        self.other_det = PlateDetection.objects.create(
            plate=self.other_plate,
            camera=self.camera,
            detection_confidence=0.71,
            ocr_confidence=0.65,
        )


class StatsApiTest(ApiTestBase):
    def test_totals_and_breakdown(self):
        resp = self.client.get(reverse("api-stats"))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["total_plates"], 2)
        self.assertEqual(data["total_detections"], 3)
        self.assertEqual(data["plates_by_status"]["unknown"], 1)
        self.assertEqual(data["plates_by_status"]["denied"], 1)
        self.assertEqual(
            data["detections_by_camera"],
            [{"camera": "Gate1", "detections": 3}],
        )
        self.assertGreaterEqual(data["detections_last_24h"], 3)


class PlatesApiTest(ApiTestBase):
    def test_list_includes_aggregates(self):
        resp = self.client.get(reverse("api-plates"))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["count"], 2)
        by_text = {r["plate_text"]: r for r in data["results"]}
        first = by_text["A123BC77"]
        self.assertIn("photo_url", first)
        self.assertIn("crop_url", first)
        self.assertEqual(first["detection_count"], 2)

    def test_pagination(self):
        resp = self.client.get(reverse("api-plates"), {"limit": 1, "offset": 1})
        data = resp.json()
        self.assertEqual(data["count"], 2)
        self.assertEqual(len(data["results"]), 1)

    def test_status_filter(self):
        resp = self.client.get(reverse("api-plates"), {"status": "denied"})
        data = resp.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["plate_text"], "M567EF190")

    def test_invalid_status_returns_all(self):
        resp = self.client.get(reverse("api-plates"), {"status": "bogus"})
        self.assertEqual(resp.json()["count"], 2)

    def test_search(self):
        resp = self.client.get(reverse("api-plates"), {"search": "123"})
        data = resp.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["plate_text"], "A123BC77")


class PlateDetailApiTest(ApiTestBase):
    def test_detail_with_detections(self):
        resp = self.client.get(reverse("api-plate-detail", args=["A123BC77"]))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["plate_text"], "A123BC77")
        self.assertEqual(data["photo_url"], "http://localhost:9000/anpr-crops/plates/photos/A123BC77.jpg")
        self.assertEqual(data["count"], 2)
        self.assertEqual(len(data["detections"]), 2)
        self.assertEqual(data["detections"][0]["camera"], "Gate1")

    def test_detail_not_found(self):
        resp = self.client.get(reverse("api-plate-detail", args=["ZZ999XX"]))
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["error"], "not found")

    def test_detail_uppercases_query(self):
        resp = self.client.get(reverse("api-plate-detail", args=["a123bc77"]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["plate_text"], "A123BC77")


class DetectionsApiTest(ApiTestBase):
    def test_list(self):
        resp = self.client.get(reverse("api-detections"))
        data = resp.json()
        self.assertEqual(data["count"], 3)
        self.assertEqual(
            {r["plate"] for r in data["results"]},
            {"A123BC77", "M567EF190"},
        )

    def test_filter_by_plate(self):
        resp = self.client.get(reverse("api-detections"), {"plate": "a123"})
        data = resp.json()
        self.assertEqual(data["count"], 2)
        self.assertEqual({r["plate"] for r in data["results"]}, {"A123BC77"})

    def test_filter_by_camera(self):
        resp = self.client.get(reverse("api-detections"), {"camera_id": self.camera.id})
        data = resp.json()
        self.assertEqual(data["count"], 3)

    def test_filter_by_date_range(self):
        future = timezone.now() + timezone.timedelta(days=1)
        resp = self.client.get(
            reverse("api-detections"), {"from": future.isoformat()}
        )
        self.assertEqual(resp.json()["count"], 0)

    def test_fields(self):
        resp = self.client.get(reverse("api-detections"), {"plate": "A123"})
        item = resp.json()["results"][0]
        self.assertIn("id", item)
        self.assertIn("crop_url", item)
        self.assertIn("detection_confidence", item)
        self.assertIn("ocr_confidence", item)
        self.assertEqual(item["camera"], "Gate1")
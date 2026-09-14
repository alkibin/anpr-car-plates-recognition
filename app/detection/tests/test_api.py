"""Тесты REST API: статистика, список деталей номеров и детекций (без DRF, обычные Django JSON-представления)."""
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from app.detection.models import Camera, Plate, PlateDetection


class ApiTestBase(TestCase):
    """Базовая подготовка данных для тестов API: камера, номера и детекции."""

    def setUp(self):
        """Создаёт камеру, два номера (один с детекциями) и связанные записи детекций."""
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
    """Тесты endpoинта статистики (/api/stats/)."""

    def test_totals_and_breakdown(self):
        """Проверяет, что /api/stats/ возвращает 200 и верные итоги по номерам, детекциям, статусам и камерам."""
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
    """Тесты списка номеров (/api/plates/) с агрегатами, пагинацией, фильтрами и поиском."""

    def test_list_includes_aggregates(self):
        """Проверяет, что список номеров возвращает 200, агрегаты и URL фото/кропа для каждого номера."""
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
        """Проверяет, что параметры limit/offset корректно ограничивают результаты списка номеров."""
        resp = self.client.get(reverse("api-plates"), {"limit": 1, "offset": 1})
        data = resp.json()
        self.assertEqual(data["count"], 2)
        self.assertEqual(len(data["results"]), 1)

    def test_status_filter(self):
        """Проверяет, что фильтр статуса возвращает только номера с указанным статусом."""
        resp = self.client.get(reverse("api-plates"), {"status": "denied"})
        data = resp.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["plate_text"], "M567EF190")

    def test_invalid_status_returns_all(self):
        """Проверяет, что несуществующий статус в фильтре не отбрасывает номера и возвращает все записи."""
        resp = self.client.get(reverse("api-plates"), {"status": "bogus"})
        self.assertEqual(resp.json()["count"], 2)

    def test_search(self):
        """Проверяет, что поиск по подстроке номера возвращает только подходящие записи."""
        resp = self.client.get(reverse("api-plates"), {"search": "123"})
        data = resp.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["plate_text"], "A123BC77")


class PlateDetailApiTest(ApiTestBase):
    """Тесты детализации номера (/api/plates/<plate_text>/)."""

    def test_detail_with_detections(self):
        """Проверяет, что детальная информация о номере возвращает 200 и список его детекций."""
        resp = self.client.get(reverse("api-plate-detail", args=["A123BC77"]))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["plate_text"], "A123BC77")
        self.assertEqual(data["photo_url"], "http://localhost:9000/anpr-crops/plates/photos/A123BC77.jpg")
        self.assertEqual(data["count"], 2)
        self.assertEqual(len(data["detections"]), 2)
        self.assertEqual(data["detections"][0]["camera"], "Gate1")

    def test_detail_not_found(self):
        """Проверяет, что запрос несуществующего номера возвращает 404 с ошибкой not found."""
        resp = self.client.get(reverse("api-plate-detail", args=["ZZ999XX"]))
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["error"], "not found")

    def test_detail_uppercases_query(self):
        """Проверяет, что запрос номера в нижнем регистре приводится к верхнему и возвращает 200."""
        resp = self.client.get(reverse("api-plate-detail", args=["a123bc77"]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["plate_text"], "A123BC77")


class DetectionsApiTest(ApiTestBase):
    """Тесты списка детекций (/api/detections/) с фильтрами по номеру, камере и диапазону дат."""

    def test_list(self):
        """Проверяет, что список детекций возвращает все записи и корректные номера в результатах."""
        resp = self.client.get(reverse("api-detections"))
        data = resp.json()
        self.assertEqual(data["count"], 3)
        self.assertEqual(
            {r["plate"] for r in data["results"]},
            {"A123BC77", "M567EF190"},
        )

    def test_filter_by_plate(self):
        """Проверяет, что фильтр по номеру оставляет только детекции подходящих номеров."""
        resp = self.client.get(reverse("api-detections"), {"plate": "a123"})
        data = resp.json()
        self.assertEqual(data["count"], 2)
        self.assertEqual({r["plate"] for r in data["results"]}, {"A123BC77"})

    def test_filter_by_camera(self):
        """Проверяет, что фильтр по камере возвращает все детекции указанной камеры."""
        resp = self.client.get(reverse("api-detections"), {"camera_id": self.camera.id})
        data = resp.json()
        self.assertEqual(data["count"], 3)

    def test_filter_by_date_range(self):
        """Проверяет, что диапазон дат из будущего не возвращает детекций."""
        future = timezone.now() + timezone.timedelta(days=1)
        resp = self.client.get(
            reverse("api-detections"), {"from": future.isoformat()}
        )
        self.assertEqual(resp.json()["count"], 0)

    def test_fields(self):
        """Проверяет, что в детекции присутствуют ожидаемые поля: id, crop_url, уверенности и камера."""
        resp = self.client.get(reverse("api-detections"), {"plate": "A123"})
        item = resp.json()["results"][0]
        self.assertIn("id", item)
        self.assertIn("crop_url", item)
        self.assertIn("detection_confidence", item)
        self.assertIn("ocr_confidence", item)
        self.assertEqual(item["camera"], "Gate1")
"""Тесты minio_adapter: формирование ключей/URL фото и загрузка фото номера с мокированным MinIO-клиентом."""
from unittest.mock import Mock, patch

from django.test import TestCase

from app.storage import minio_adapter


class PlatePhotoKeyTest(TestCase):
    """Тесты вспомогательных функций формирования ключей и URL."""

    def test_stable_deterministic_key(self):
        """Проверяет, что plate_photo_key() возвращает стабильный детерминированный ключ для номера."""
        self.assertEqual(
            minio_adapter.plate_photo_key("A123BC77"),
            "plates/photos/A123BC77.jpg",
        )
        self.assertEqual(
            minio_adapter.plate_photo_key("A123BC77"),
            minio_adapter.plate_photo_key("A123BC77"),
        )

    def test_build_crop_url(self):
        """Проверяет, что build_crop_url() собирает полный URL из ключа, а для пустого ключа возвращает пустую строку."""
        url = minio_adapter.build_crop_url("plates/photos/A123BC77.jpg")
        self.assertEqual(
            url, "http://localhost:9000/anpr-crops/plates/photos/A123BC77.jpg"
        )
        self.assertEqual(minio_adapter.build_crop_url(""), "")


@patch("app.storage.minio_adapter.ensure_bucket")
@patch("app.storage.minio_adapter.object_exists")
class StorePlatePhotoTest(TestCase):
    """Тесты store_plate_photo() с мокированным MinIO-клиентом и обеспечением бакета."""

    def test_uploads_when_photo_missing(self, mock_exists, mock_ensure):
        """Проверяет, что при отсутствии фото в бакете store_plate_photo() загружает объект и возвращает uploaded=True."""
        mock_exists.return_value = False
        client = Mock()
        with patch("app.storage.minio_adapter._client", return_value=client) as mock_client:
            key, uploaded = minio_adapter.store_plate_photo(b"jpeg-bytes", "A123BC77")

        self.assertTrue(uploaded)
        self.assertEqual(key, "plates/photos/A123BC77.jpg")
        mock_ensure.assert_called_once()
        client.put_object.assert_called_once()
        args, kwargs = client.put_object.call_args
        self.assertEqual(args[0], "anpr-crops")
        self.assertEqual(args[1], "plates/photos/A123BC77.jpg")
        self.assertEqual(kwargs["length"], 10)
        self.assertEqual(kwargs["content_type"], "image/jpeg")

    def test_skips_upload_when_photo_exists(self, mock_exists, mock_ensure):
        """Проверяет, что при уже существующем фото загрузка пропускается и возвращается uploaded=False."""
        mock_exists.return_value = True
        client = Mock()
        with patch("app.storage.minio_adapter._client", return_value=client):
            key, uploaded = minio_adapter.store_plate_photo(b"jpeg-bytes", "A123BC77")

        self.assertFalse(uploaded)
        self.assertEqual(key, "plates/photos/A123BC77.jpg")
        client.put_object.assert_not_called()
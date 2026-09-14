"""Тесты дедупликации и троттлинга кропов (PlateDedupStore)."""

from unittest.mock import MagicMock, patch
from django.test import SimpleTestCase

from app.events.storage import PlateDedupStore


class CropThrottleTest(SimpleTestCase):
    """Проверяет should_upload_crop: пропускает первый вызов и блокирует повторы в пределах TTL."""

    def _make_store(self) -> PlateDedupStore:
        """Создаёт PlateDedupStore с моком Redis-клиента."""
        with patch("app.events.storage.redis.Redis"):
            store = PlateDedupStore()
        store.client = MagicMock()
        return store

    def test_first_upload_allowed(self):
        """Первый вызов должен разрешить загрузку и поставить ключ."""
        store = self._make_store()
        store.client.get.return_value = None
        self.assertTrue(store.should_upload_crop("A123BC", ttl_seconds=86400))
        store.client.set.assert_called_once_with(
            "crop_throttle:A123BC", "1", ex=86400
        )

    def test_second_upload_blocked(self):
        """Второй вызов (ключ существует) должен вернуть False."""
        store = self._make_store()
        store.client.get.return_value = "1"
        self.assertFalse(store.should_upload_crop("A123BC", ttl_seconds=86400))
        store.client.set.assert_not_called()

    def test_different_plates_independent(self):
        """Разные номера не блокируют друг друга."""
        store = self._make_store()
        store.client.get.return_value = None
        self.assertTrue(store.should_upload_crop("A123BC"))
        store.client.get.return_value = "1"
        self.assertFalse(store.should_upload_crop("X999ZZ"))

    def test_custom_ttl(self):
        """Пользовательский TTL передаётся в Redis."""
        store = self._make_store()
        store.client.get.return_value = None
        store.should_upload_crop("A123BC", ttl_seconds=3600)
        store.client.set.assert_called_once_with(
            "crop_throttle:A123BC", "1", ex=3600
        )

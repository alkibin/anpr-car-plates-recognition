"""Конфигурация Django-приложения detection (камеры, номера, распознавания)."""

from django.apps import AppConfig


class DetectionConfig(AppConfig):
    """Настройки приложения app.detection: авто-поле и читаемое имя."""
    default_auto_field = "django.db.models.BigAutoField"
    name = "app.detection"
    verbose_name = "Распознавание"

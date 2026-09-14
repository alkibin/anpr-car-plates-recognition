from django.db import models


class Camera(models.Model):
    name = models.CharField("Название", max_length=128, unique=True)
    rtsp_url = models.URLField("RTSP URL", max_length=512)
    location = models.CharField("Местоположение", max_length=256, blank=True, default="")
    is_active = models.BooleanField("Активна", default=True)
    created_at = models.DateTimeField("Создана", auto_now_add=True)

    class Meta:
        verbose_name = "Камера"
        verbose_name_plural = "Камеры"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Plate(models.Model):
    class Status(models.TextChoices):
        UNKNOWN = "unknown", "Неизвестен"
        ALLOWED = "allowed", "Разрешён"
        DENIED = "denied", "Запрещён"

    plate_text = models.CharField("Номер", max_length=20, unique=True, db_index=True)
    status = models.CharField(
        "Статус", max_length=10, choices=Status.choices, default=Status.UNKNOWN, db_index=True
    )
    first_seen = models.DateTimeField("Первое появление", auto_now_add=True)
    last_seen = models.DateTimeField("Последнее появление", db_index=True)
    detection_count = models.PositiveIntegerField("Кол-во распознаваний", default=0)
    last_crop_key = models.CharField("Последний кроп (S3)", max_length=512, blank=True, default="")
    photo_key = models.CharField("Фото номера (S3)", max_length=512, blank=True, default="")
    note = models.TextField("Заметка", blank=True, default="")

    class Meta:
        verbose_name = "Номер"
        verbose_name_plural = "Номера"
        ordering = ["-last_seen"]

    def __str__(self):
        return f"{self.plate_text} ({self.get_status_display()})"

    @property
    def crop_url(self):
        from app.storage.minio_adapter import build_crop_url
        return build_crop_url(self.last_crop_key)

    @property
    def photo_url(self):
        from app.storage.minio_adapter import build_crop_url
        return build_crop_url(self.photo_key)

    def seen_again(self, last_crop_key: str = ""):
        """Обновляет агрегаты при новом распознавании номера."""
        self.detection_count += 1
        self.last_seen = models.functions.Now()
        update_fields = ["detection_count", "last_seen"]
        if last_crop_key:
            self.last_crop_key = last_crop_key
            update_fields.append("last_crop_key")
        self.save(update_fields=update_fields)


class PlateDetection(models.Model):
    plate = models.ForeignKey(
        Plate,
        on_delete=models.CASCADE,
        verbose_name="Номер",
        related_name="detections",
    )
    camera = models.ForeignKey(
        Camera,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Камера",
        related_name="detections",
    )
    detection_confidence = models.FloatField("Уверенность детекции")
    ocr_confidence = models.FloatField("Уверенность OCR")
    crop_object_key = models.CharField(
        "Object key в S3", max_length=512, blank=True, default=""
    )
    detected_at = models.DateTimeField("Время распознавания", auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Распознавание"
        verbose_name_plural = "Распознавания"
        ordering = ["-detected_at"]

    def __str__(self):
        return f"{self.plate.plate_text} ({self.detection_confidence:.0%})"

    @property
    def crop_url(self):
        from app.storage.minio_adapter import build_crop_url
        return build_crop_url(self.crop_object_key)
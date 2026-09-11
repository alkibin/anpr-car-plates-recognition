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


class PlateDetection(models.Model):
    camera = models.ForeignKey(
        Camera,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Камера",
        related_name="detections",
    )
    plate_text = models.CharField("Текст номера", max_length=20, db_index=True)
    detection_confidence = models.FloatField("Уверенность детекции")
    ocr_confidence = models.FloatField("Уверенность OCR")
    crop_object_key = models.CharField(
        "Object key в S3", max_length=512, blank=True, default=""
    )
    detected_at = models.DateTimeField("Время распознавания", auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Распознанный номер"
        verbose_name_plural = "Распознанные номера"
        ordering = ["-detected_at"]

    def __str__(self):
        return f"{self.plate_text} ({self.detection_confidence:.0%})"

    @property
    def crop_url(self):
        if self.crop_object_key:
            from django.conf import settings
            return f"http://{settings.MINIO_ENDPOINT}/{settings.MINIO_BUCKET}/{self.crop_object_key}"
        return ""

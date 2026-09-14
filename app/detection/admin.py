"""Django admin: редактирование камер, номеров и распознаваний."""

from django.contrib import admin
from django.http import HttpResponse, HttpResponseNotFound
from django.shortcuts import get_object_or_404
from django.urls import path, reverse
from django.utils.html import format_html

from app.detection.models import Camera, Plate, PlateDetection
from app.storage import minio_adapter


@admin.register(Camera)
class CameraAdmin(admin.ModelAdmin):
    """Админка камер: список с поиском по имени и местоположению."""
    list_display = ("name", "location", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "location")


class PlateDetectionInline(admin.TabularInline):
    """Табличный инлайн распознаваний внутри карточки номера."""
    model = PlateDetection
    fields = ("detected_at", "camera", "detection_confidence", "ocr_confidence")
    readonly_fields = fields
    extra = 0
    can_delete = False
    show_change_link = True


@admin.register(Plate)
class PlateAdmin(admin.ModelAdmin):
    """Админка номеров: фильтры по статусу, поиск, массовые действия, инлайн детекций, превью фото."""
    list_display = (
        "plate_text",
        "status",
        "preview_photo",
        "detection_count",
        "first_seen",
        "last_seen",
    )
    list_filter = ("status", "last_seen")
    search_fields = ("plate_text", "note")
    list_editable = ("status",)
    readonly_fields = (
        "first_seen",
        "last_seen",
        "detection_count",
        "preview_photo",
        "preview_crop",
    )
    date_hierarchy = "last_seen"
    fieldsets = (
        (None, {"fields": ("plate_text", "status", "note")}),
        ("Фото", {"fields": ("preview_photo", "preview_crop")}),
        ("Статистика", {"fields": ("first_seen", "last_seen", "detection_count")}),
        ("Хранилище", {"fields": ("photo_key", "last_crop_key")}),
    )
    inlines = (PlateDetectionInline,)
    actions = ("mark_allowed", "mark_denied", "mark_unknown")

    @staticmethod
    def _image_tag(url: str, alt: str = "") -> str:
        """Возвращает HTML-тег миниатюры изображения или пустую строку без URL."""
        if not url:
            return ""
        return format_html(
            '<a href="{}" target="_blank"><img src="{}" alt="{}" '
            'style="max-width:240px;max-height:80px;border:1px solid #ccc;'
            'border-radius:4px"/></a>',
            url,
            url,
            alt,
        )

    def preview_photo(self, obj):
        """Миниатюра стабильного фото номера из MinIO; пустая строка, если фото нет."""
        return self._image_tag(
            reverse("admin:plate-photo", args=[obj.pk]),
            f"Фото {obj.plate_text}",
        )

    preview_photo.short_description = "Фото номера"

    def preview_crop(self, obj):
        """Миниатюра последнего кропа номера из MinIO; пустая строка, если кропа нет."""
        return self._image_tag(
            reverse("admin:plate-crop", args=[obj.pk]),
            f"Кроп {obj.plate_text}",
        )

    preview_crop.short_description = "Последний кроп"

    def get_urls(self):
        """Добавляет маршруты для отдачи фото/кропов номеров через Django (из MinIO)."""
        urls = super().get_urls()
        custom = [
            path(
                "<int:object_id>/photo/",
                self.admin_site.admin_view(self.serve_photo, cacheable=True),
                name="plate-photo",
            ),
            path(
                "<int:object_id>/crop/",
                self.admin_site.admin_view(self.serve_crop, cacheable=True),
                name="plate-crop",
            ),
        ]
        return custom + urls

    def serve_photo(self, request, object_id):
        """Отдаёт содержимое стабильного фото номера из MinIO как image/jpeg."""
        return self._serve_object(
            get_object_or_404(Plate, pk=object_id).photo_key,
            "Фото номера не найдено в хранилище.",
        )

    def serve_crop(self, request, object_id):
        """Отдаёт содержимое последнего кропа номера из MinIO как image/jpeg."""
        return self._serve_object(
            get_object_or_404(Plate, pk=object_id).last_crop_key,
            "Кроп номера не найден в хранилище.",
        )

    @staticmethod
    def _serve_object(object_key: str, missing_message: str) -> HttpResponse:
        """Возвращает JPEG-ответ из MinIO по object_key либо 404."""
        data = minio_adapter.read_object(object_key)
        if data is None:
            return HttpResponseNotFound(missing_message)
        return HttpResponse(data, content_type="image/jpeg")

    @admin.action(description="Разрешить выбранные номера")
    def mark_allowed(self, request, queryset):
        """Массово присваивает статус ALLOWED выбранным номерам."""
        queryset.update(status=Plate.Status.ALLOWED)

    @admin.action(description="Запретить выбранные номера")
    def mark_denied(self, request, queryset):
        """Массово присваивает статус DENIED выбранным номерам."""
        queryset.update(status=Plate.Status.DENIED)

    @admin.action(description="Сбросить статус выбранных (неизвестен)")
    def mark_unknown(self, request, queryset):
        """Массово сбрасывает статус выбранных номеров на UNKNOWN."""
        queryset.update(status=Plate.Status.UNKNOWN)


@admin.register(PlateDetection)
class PlateDetectionAdmin(admin.ModelAdmin):
    """Админка распознаваний: фильтры по камере и времени, поиск по номеру."""
    list_display = (
        "plate",
        "camera",
        "detection_confidence",
        "ocr_confidence",
        "detected_at",
    )
    list_filter = ("camera", "detected_at")
    search_fields = ("plate__plate_text",)
    readonly_fields = ("detected_at", "plate", "camera", "detection_confidence", "ocr_confidence")
    date_hierarchy = "detected_at"
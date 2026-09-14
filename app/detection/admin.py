"""Django admin: редактирование камер, номеров и распознаваний."""

from django.contrib import admin
from app.detection.models import Camera, Plate, PlateDetection


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
    """Админка номеров: фильтры по статусу, поиск, массовые действия, инлайн детекций."""
    list_display = (
        "plate_text",
        "status",
        "detection_count",
        "first_seen",
        "last_seen",
    )
    list_filter = ("status", "last_seen")
    search_fields = ("plate_text", "note")
    list_editable = ("status",)
    readonly_fields = ("first_seen", "last_seen", "detection_count")
    date_hierarchy = "last_seen"
    fieldsets = (
        (None, {"fields": ("plate_text", "status", "note")}),
        ("Статистика", {"fields": ("first_seen", "last_seen", "detection_count")}),
        ("Хранилище", {"fields": ("photo_key", "last_crop_key")}),
    )
    inlines = (PlateDetectionInline,)
    actions = ("mark_allowed", "mark_denied", "mark_unknown")

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
from django.contrib import admin
from app.detection.models import Camera, PlateDetection


@admin.register(Camera)
class CameraAdmin(admin.ModelAdmin):
    list_display = ("name", "location", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "location")


@admin.register(PlateDetection)
class PlateDetectionAdmin(admin.ModelAdmin):
    list_display = (
        "plate_text",
        "camera",
        "detection_confidence",
        "ocr_confidence",
        "detected_at",
    )
    list_filter = ("camera", "detected_at")
    search_fields = ("plate_text",)
    readonly_fields = ("detected_at",)
    date_hierarchy = "detected_at"

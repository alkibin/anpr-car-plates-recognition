from datetime import datetime, timedelta

from django.db.models import Count, Q
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET

from app.detection.models import Camera, Plate, PlateDetection
from app.storage.minio_adapter import build_crop_url

DEFAULT_LIMIT = 50
MAX_LIMIT = 200


def _int_param(request, name, default):
    try:
        return max(int(request.GET.get(name, default)), 0)
    except (TypeError, ValueError):
        return default


def _pagination(request):
    limit = min(_int_param(request, "limit", DEFAULT_LIMIT), MAX_LIMIT)
    offset = _int_param(request, "offset", 0)
    return limit, offset


def _page(count, limit, offset):
    return {
        "count": count,
        "limit": limit,
        "offset": offset,
        "next": min(offset + limit, count) if offset + limit < count else None,
    }


def _plate_dump(plate):
    return {
        "plate_text": plate.plate_text,
        "status": plate.status,
        "status_label": plate.get_status_display(),
        "first_seen": plate.first_seen.isoformat(),
        "last_seen": plate.last_seen.isoformat(),
        "detection_count": plate.detection_count,
        "crop_url": build_crop_url(plate.last_crop_key),
        "photo_url": plate.photo_url,
        "note": plate.note,
    }


def _detection_dump(d):
    return {
        "id": d.id,
        "plate": d.plate.plate_text,
        "camera": d.camera.name if d.camera else None,
        "camera_id": d.camera_id,
        "detection_confidence": round(d.detection_confidence, 3),
        "ocr_confidence": round(d.ocr_confidence, 3),
        "detected_at": d.detected_at.isoformat(),
        "crop_url": build_crop_url(d.crop_object_key),
    }


@require_GET
def plates(request):
    """Список номеров + агрегаты. ?status=&search=&limit=&offset="""
    qs = Plate.objects.all()
    status = request.GET.get("status")
    if status in Plate.Status.values:
        qs = qs.filter(status=status)
    search = request.GET.get("search", "").strip().upper()
    if search:
        qs = qs.filter(
            Q(plate_text__icontains=search) | Q(note__icontains=search)
        )
    limit, offset = _pagination(request)
    count = qs.count()
    items = list(qs.order_by("-last_seen")[offset : offset + limit])
    return JsonResponse({"results": [_plate_dump(p) for p in items], **_page(count, limit, offset)})


@require_GET
def plate_detail(request, plate_text: str):
    """Карточка номера + его последние распознавания. ?limit= (детекции)"""
    try:
        plate = Plate.objects.get(plate_text=plate_text.upper())
    except Plate.DoesNotExist:
        return JsonResponse({"error": "not found"}, status=404)

    limit, offset = _pagination(request)
    det_qs = plate.detections.select_related("camera").order_by("-detected_at")
    det_count = det_qs.count()
    dets = list(det_qs[offset : offset + limit])

    return JsonResponse(
        {
            **_plate_dump(plate),
            "detections": [_detection_dump(d) for d in dets],
            **_page(det_count, limit, offset),
        }
    )


@require_GET
def detections(request):
    """Лента распознаваний. ?camera_id=&plate=&from=&to=&limit=&offset="""
    qs = PlateDetection.objects.select_related("plate", "camera").all()
    camera_id = _int_param(request, "camera_id", 0)
    if camera_id:
        qs = qs.filter(camera_id=camera_id)
    plate = request.GET.get("plate", "").strip().upper()
    if plate:
        qs = qs.filter(plate__plate_text__icontains=plate)
    date_from = request.GET.get("from")
    date_to = request.GET.get("to")
    if date_from:
        qs = qs.filter(detected_at__gte=date_from)
    if date_to:
        qs = qs.filter(detected_at__lt=date_to)

    limit, offset = _pagination(request)
    count = qs.count()
    items = list(qs.order_by("-detected_at")[offset : offset + limit])
    return JsonResponse({"results": [_detection_dump(d) for d in items], **_page(count, limit, offset)})


@require_GET
def stats(request):
    """Общая статистика: всего, по статусам, за 24ч/1ч, по камерам."""
    now = timezone.now()
    day_ago = now - timedelta(hours=24)
    hour_ago = now - timedelta(hours=1)

    det_24h = PlateDetection.objects.filter(detected_at__gte=day_ago).count()
    det_1h = PlateDetection.objects.filter(detected_at__gte=hour_ago).count()

    by_status = {
        row["status"]: row["cnt"]
        for row in Plate.objects.values("status").annotate(cnt=Count("id"))
    }
    by_camera = [
        {"camera": row["camera__name"], "detections": row["cnt"]}
        for row in PlateDetection.objects.select_related("camera")
        .values("camera__name")
        .annotate(cnt=Count("id"))
    ]

    return JsonResponse(
        {
            "total_plates": Plate.objects.count(),
            "total_detections": PlateDetection.objects.count(),
            "detections_last_24h": det_24h,
            "detections_last_hour": det_1h,
            "plates_by_status": by_status,
            "detections_by_camera": by_camera,
            "generated_at": now.isoformat(),
        }
    )
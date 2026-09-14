"""Адаптер к MinIO: загрузка фото/кропов номеров и построение их URL."""

import io
import uuid
from datetime import datetime

from django.conf import settings
from minio import Minio
from minio.error import S3Error


def _client() -> Minio:
    """Создаёт клиент MinIO из настроек Django (endpoint, ключи, TLS)."""
    return Minio(
        settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE,
    )


def ensure_bucket() -> None:
    """Гарантирует существование бакета, создавая его при первом обращении."""
    client = _client()
    bucket = settings.MINIO_BUCKET
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)


def build_crop_url(object_key: str) -> str:
    """Строит публичный URL кропа в MinIO (без presign, для локальной разработки)."""
    if not object_key:
        return ""
    scheme = "https" if settings.MINIO_SECURE else "http"
    return f"{scheme}://{settings.MINIO_ENDPOINT}/{settings.MINIO_BUCKET}/{object_key}"


def plate_photo_key(plate_text: str) -> str:
    """Детерминированный object key фото номера — один на весь жизненный цикл."""
    return f"plates/photos/{plate_text}.jpg"


def store_plate_photo(image_bytes: bytes, plate_text: str) -> tuple[str, bool]:
    """Сохраняет фото номера, если его ещё нет в бакете.

    Возвращает (object_key, uploaded: bool) — uploaded=True, если фото записано
    только сейчас (первое распознавание), иначе (существующий ключ, False).
    """
    ensure_bucket()
    object_name = plate_photo_key(plate_text)
    if object_exists(object_name):
        return object_name, False
    client = _client()
    client.put_object(
        settings.MINIO_BUCKET,
        object_name,
        io.BytesIO(image_bytes),
        length=len(image_bytes),
        content_type="image/jpeg",
    )
    return object_name, True


def upload_plate_crop(image_bytes: bytes, plate_text: str) -> str:
    """Загружает обрезанный кадр номера в MinIO, возвращает object key."""
    ensure_bucket()
    object_name = (
        f"plates/{datetime.now().strftime('%Y/%m/%d')}/"
        f"{plate_text}_{uuid.uuid4().hex[:8]}.jpg"
    )
    client = _client()
    client.put_object(
        settings.MINIO_BUCKET,
        object_name,
        io.BytesIO(image_bytes),
        length=len(image_bytes),
        content_type="image/jpeg",
    )
    return object_name


def object_exists(object_key: str) -> bool:
    """Проверяет наличие объекта в бакете, возвращая False при ошибке S3."""
    if not object_key:
        return False
    try:
        client = _client()
        client.stat_object(settings.MINIO_BUCKET, object_key)
        return True
    except S3Error:
        return False


def read_object(object_key: str) -> bytes | None:
    """Возвращает содержимое объекта MinIO байтами (для показа в админке) или None, если объекта нет."""
    if not object_key:
        return None
    try:
        client = _client()
        response = client.get_object(settings.MINIO_BUCKET, object_key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()
    except S3Error:
        return None
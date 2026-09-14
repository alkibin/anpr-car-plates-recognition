"""Параметры конфигурации пайплайна ANPR (Pydantic-settings, читает .env)."""

import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Конфигурация пайплайна: RTSP, YOLO, OCR, Redis, MinIO и др."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    rtsp_url: str = "rtsp://localhost:8554/mystream"
    onvif_ip: str = ""
    onvif_port: int = 80
    onvif_user: str = "admin"
    onvif_password: str = "admin"
    database_url: str = "sqlite:///data/anpr.db"
    webhook_url: str = ""
    yolo_model: str = "yolov8n.pt"
    plate_model_path: str = "/Users/aleksanderkibin/.cache/huggingface/hub/models--Koushim--yolov8-license-plate-detection/snapshots/9aaa5cd490abe0c165882ba87f4f62658ab54d01/best.pt"
    ocr_engine: str = "easyocr"
    motion_threshold_area: int = 1500
    check_interval_sec: float = 1.0
    rtsp_transport: str = "tcp"
    plate_confidence: float = 0.6
    min_ocr_confidence: float = 0.3

    redis_host: str = "localhost"
    redis_port: int = 6379
    plate_dedup_ttl_seconds: int = 3600
    crop_upload_ttl_seconds: int = 86400

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "anpr-crops"
    minio_secure: bool = False


settings = Settings()
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = f"rtsp_transport;{settings.rtsp_transport}"

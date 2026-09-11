# ANPR Pet Project

Automatic Number Plate Recognition: RTSP → YOLO plate detection → OCR → PostgreSQL + MinIO, managed via Django admin.

## Quick Start

```bash
# 1. Inftastructure (PostgreSQL, MinIO, Redis, MediaMTX)
docker compose up -d

# 2. Run Django admin (host-side dev; http://localhost:8000/admin/)
.venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py createsuperuser
.venv/bin/python manage.py runserver

# 3. Push a sample feed to MediaMTX
./streaming/stream_to_mediamtx.sh streaming/cars.mp4

# 4. Run the recognition pipeline (RTSP → detect → OCR → PG + MinIO)
.venv/bin/python -m scripts.dev_loop
```

## Architecture

- **MediaMTX** — RTSP relay server
- **YOLOv8** — plate detection (`app/recognition/plate_detector.py`)
- **PaddleOCR** — text recognition (`app/recognition/ocr.py`)
- **PostgreSQL** — plate detections (`app/detection/models.py`)
- **MinIO** — crop images storage (console: localhost:9001)
- **Django admin** — control plane (localhost:8000/admin/)
- **Redis** — deduplication of recently seen plates

## Components

| Module | Purpose |
|---|---|
| `scripts/dev_loop.py` | Pipeline: motion → detection → OCR → dedup → save to PG + MinIO |
| `app/detection/` | Django models + admin (`Camera`, `PlateDetection`) |
| `app/storage/minio_adapter.py` | MinIO/S3 adapter for plate crops |
| `app/events/storage.py` | Redis plate-dedup store |
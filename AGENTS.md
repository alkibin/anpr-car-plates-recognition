# AGENTS.md

ANPR pet project — RTSP → YOLO plate detection → OCR → PostgreSQL (Django admin) + MinIO crop storage. FastAPI is secondary/deprecated for UI; Django admin is the control plane.

## Commands

```bash
# Infra (postgres, minio, redis, mediamtx)
docker compose up -d postgres minio redis mediamtx

# Django admin (dev server, http://localhost:8000/admin/)
.venv/bin/python manage.py runserver
# Docker runs migrate on start; superuser: admin/admin (created against local PG)

# Pipeline dev loop (RTSP → detect → OCR → save to PG + MinIO)
.venv/bin/python -m scripts.dev_loop

# Infra checks / management
.venv/bin/python manage.py migrate            # applies migrations
.venv/bin/python manage.py makemigrations     # new models → migration
.venv/bin/python manage.py test               # run tests (Django runner, uses test_anpr DB)
./streaming/stream_to_mediamtx.sh streaming/cars.mp4  # push looped feed

# REST API (new project: no DRF, plain Django JSON views)
GET /api/plates/                          # ?status=&search=&limit=&offset=
GET /api/plates/<plate_text>/             # plate + its detections; 404 if unknown
GET /api/detections/                      # ?plate=&camera_id=&from=&to=
GET /api/stats/                           # totals, by-status, by-camera, last 24h/1h
```

## Architecture

- **Django ORM is the ONLY data-access layer** — no SQLAlchemy. Models in `app/detection/models.py` (`Camera`, `Plate`, `PlateDetection`). `Plate` aggregates detections: status, first/last seen, count, stable `photo_key` (written once, key `plates/photos/{plate}.jpg`).
- Admin: `app/detection/admin.py`, Django project config in `app/settings.py`, entry `manage.py` (DB=PostgreSQL; `POSTGRES_HOST=postgres` in Docker, override to `localhost` for local runs via `.env`). Plate change form shows photo/crop previews served by Django views `<int:plate_id>/photo/` and `<int:plate_id>/crop/` (via `minio_adapter.read_object`), so MinIO bucket needs no public policy.
- Pipeline: `scripts/dev_loop.py` calls `django.setup()`, writes via ORM, saves crops via `app/storage/minio_adapter.py` (MinIO SDK). Redis dedup via `app/events/storage.py`.
- REST API: plain Django JSON views in `app/api/views.py` (no DRF). Tests in `app/detection/tests/`.
- FastAPI (`app/main.py` removed, `app/api/routes.py` removed) is legacy — do NOT reintroduce it.

## Config / runtime quirks

- Two config layers: `app/config.py` (pydantic-settings, pipeline values like RTSP/YOLO/Redis/MinIO) and Django `app/settings.py` (reads same `.env` via `dotenv.load_dotenv`).
- `.env` is gitignored; `POSTGRES_HOST`, `MINIO_ENDPOINT` default to docker service names (`postgres`, `minio:9000`) — set them to `localhost` for host-side dev (`scripts/dev_loop.py`, `manage.py`).
- MinIO bucket `anpr-crops` is created lazily by `ensure_bucket()` on first upload. S3 API port `9000`, console (Web UI) `9001`.
- Redis dedup TTL (`PLATE_DEDUP_TTL_SECONDS`) means a plate is written to PG at most once per TTL window.
- Crop upload throttle (`CROP_UPLOAD_TTL_SECONDS`, default 86400/24h) — `PlateDedupStore.should_upload_crop()` prevents repeated crop writes for the same plate.
- Migrations live at `app/detection/migrations/`.

## Conventions

- Binary artifacts: video (`streaming/*.mp4/.mov`), weights (`*.pt`), IDE dirs, `.env` are gitignored.
- Django app `app.detection` holds models/admin/migrations; new DB-backed features go there.
- Keep `__init__.py` in each subpackage.
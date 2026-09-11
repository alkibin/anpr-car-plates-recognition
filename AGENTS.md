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
./streaming/stream_to_mediamtx.sh streaming/cars.mp4  # push looped feed
```

## Architecture

- **Django ORM is the ONLY data-access layer** — no SQLAlchemy. Models in `app/detection/models.py` (`Camera`, `PlateDetection`).
- Admin: `app/detection/admin.py`, Django project config in `app/settings.py`, entry `manage.py` (DB=PostgreSQL; `POSTGRES_HOST=postgres` in Docker, override to `localhost` for local runs via `.env`).
- Pipeline: `scripts/dev_loop.py` calls `django.setup()`, writes via ORM, saves crops via `app/storage/minio_adapter.py` (MinIO SDK). Redis dedup via `app/events/storage.py`.
- FastAPI (`app/main.py`, `app/api/routes.py`) is legacy/unused — do NOT extend it.

## Config / runtime quirks

- Two config layers: `app/config.py` (pydantic-settings, pipeline values like RTSP/YOLO/Redis/MinIO) and Django `app/settings.py` (reads same `.env` via `dotenv.load_dotenv`).
- `.env` is gitignored; `POSTGRES_HOST`, `MINIO_ENDPOINT` default to docker service names (`postgres`, `minio:9000`) — set them to `localhost` for host-side dev (`scripts/dev_loop.py`, `manage.py`).
- MinIO bucket `anpr-crops` is created lazily by `ensure_bucket()` on first upload. S3 API port `9000`, console (Web UI) `9001`.
- Redis dedup TTL (`PLATE_DEDUP_TTL_SECONDS`) means a plate is written to PG at most once per TTL window.
- Migrations live at `app/detection/migrations/`.

## Conventions

- Binary artifacts: video (`streaming/*.mp4/.mov`), weights (`*.pt`), IDE dirs, `.env` are gitignored.
- Django app `app.detection` holds models/admin/migrations; new DB-backed features go there.
- Keep `__init__.py` in each subpackage.
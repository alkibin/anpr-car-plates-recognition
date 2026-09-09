# AGENTS.md

ANPR pet project — minimal FastAPI + YOLO + OCR scaffold. Mostly placeholder code at this stage.

## Commands

```bash
uvicorn app.main:app --reload   # run API locally on :8000
docker compose up -d            # run media server (RTSP) + app
./streaming/stream_to_mediamtx.sh streaming/cars.mp4   # push looped feed
```

## Repo gaps (do not reinvent — be aware)

- `README.md` says `cp .env.example .env`, but **`.env.example` does not exist**. `.env` itself is gitignored; a fresh clone has none. New setup relies on `app/config.py` defaults.
- `docker-compose.yml` `app.build` references a **missing `Dockerfile`**, and mounts `./mediamtx.yml` which **does not exist**. `docker compose up` will fail until these are added.
- Tests dir exists but is empty — no test runner configured.

## Config / runtime quirks

- `.env` is read by `app/config.py` (pydantic-settings, `env_file=".env"`). Keys mirror the `Settings` fields.
- `RTSP_URL` in `.env` uses host `mediamtx` (docker-compose service name). That host **only resolves when the app runs inside Docker**; running `uvicorn` on the host, the RTSP URL resolves to nothing. To test locally, override `RTSP_URL`/pass `rtsp://localhost:8554/stream`.
- Default SQLite DB path is `data/anpr.db`; `data/` and `*.db` are gitignored (created at runtime).

## Conventions

- Sources live under `app/` as packages: `app/video`, `app/onvif`, `app/recognition`, `app/events`, `app/api`. Entry point is `app/main.py`; API routes in `app/api/routes.py` are **not yet registered** on the FastAPI app.
- Binary artifacts committed to version control: only source code. Video files (`streaming/*.mp4`), model weights (`*.pt`), and IDE/venv files are gitignored.
- Keep placeholder files (`__init__.py`) in each subpackage.

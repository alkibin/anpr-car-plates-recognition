# ANPR Pet Project

Automatic Number Plate Recognition system using YOLO + OCR.

## Quick Start

```bash
cp .env.example .env
docker compose up -d
```

## Architecture

- **MediaMTX** — RTSP relay server
- **FastAPI** — REST + WebSocket API
- **YOLOv8** — plate detection
- **EasyOCR / PaddleOCR** — text recognition

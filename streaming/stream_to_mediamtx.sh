#!/bin/bash
set -e

RTSP_URL="rtsp://localhost:8554/mystream"
VIDEO_FILE="$(dirname "$0")/dashcam1.mp4"

echo "Streaming $VIDEO_FILE to $RTSP_URL (Ctrl+C to stop)"

ffmpeg -re -stream_loop -1 -i "$VIDEO_FILE" \
  -c:v copy \
  -c:a aac -b:a 128k \
  -f rtsp -rtsp_transport tcp \
  "$RTSP_URL"
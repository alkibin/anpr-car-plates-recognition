import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")
import django

django.setup()

from app.config import settings  # ВАЖНО: импорт раньше cv2/reader — выставляет env var

import cv2

import time
import logging

from django.utils import timezone

from app.video.motion import MotionDetector
from app.recognition.plate_detector import PlateDetector
from app.recognition.ocr import PlateOCR

logging.basicConfig(level=logging.INFO)


from app.events.storage import PlateDedupStore

from app.recognition.tracker import PlateTracker

from app.video.threaded_reader import ThreadedRTSPReader

from app.detection.models import Camera, Plate, PlateDetection
from app.storage import minio_adapter


def save_detection(plate_text: str, detection_conf: float, ocr_conf: float, crop_bytes: bytes):
    camera = Camera.objects.filter(is_active=True).first()
    object_key = minio_adapter.upload_plate_crop(crop_bytes, plate_text)

    plate, _ = Plate.objects.get_or_create(
        plate_text=plate_text,
        defaults={"last_seen": timezone.now()},
    )
    plate.seen_again(last_crop_key=object_key)

    PlateDetection.objects.create(
        plate=plate,
        camera=camera,
        detection_confidence=detection_conf,
        ocr_confidence=ocr_conf,
        crop_object_key=object_key,
    )
    print(f"[DB] сохранено {plate_text} в PostgreSQL, crop: {object_key}")


def main():
    motion_detector = MotionDetector(threshold_area=settings.motion_threshold_area)
    plate_detector = PlateDetector(settings.plate_model_path, confidence=settings.plate_confidence)
    ocr = PlateOCR()
    dedup_store = PlateDedupStore(host=settings.redis_host, port=settings.redis_port, ttl_seconds=settings.plate_dedup_ttl_seconds)
    tracker = PlateTracker(iou_threshold=0.3, track_timeout_sec=3.0)

    reader = ThreadedRTSPReader(settings.rtsp_url)
    reader.start()

    os.makedirs("scripts/files", exist_ok=True)

    try:
        while True:
            frame = reader.get_latest_frame()
            if frame is None:
                time.sleep(0.1)
                continue
            if motion_detector.has_motion(frame):
                boxes = plate_detector.detect(frame)
                if not boxes:
                    continue

                for box in boxes:
                    det_conf = box[4]
                    crop = plate_detector.add_padding(frame, box)
                    for final_text, rec_scores, plate in ocr.read([crop]):
                        if not dedup_store.is_new(final_text):
                            print(f"[SKIP] {final_text} уже был обработан недавно")
                            continue

                        dedup_store.mark_seen(final_text)
                        ocr_conf = float(rec_scores[0]) if rec_scores else 0.0
                        print(f"[PLATE][FINAL] {final_text} (ocr_conf={ocr_conf:.2f}, det_conf={det_conf:.2f})")

                        ok, buf = cv2.imencode(".jpg", plate)
                        if ok:
                            save_detection(
                                final_text,
                                detection_conf=det_conf,
                                ocr_conf=ocr_conf,
                                crop_bytes=buf.tobytes(),
                            )

            time.sleep(settings.check_interval_sec)
    except KeyboardInterrupt:
        print("Остановлено")
    finally:
        reader.stop()


if __name__ == "__main__":
    main()
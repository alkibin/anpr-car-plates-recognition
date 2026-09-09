import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import cv2

from app.config import settings  # ВАЖНО: импорт раньше cv2/reader — выставляет env var

import time
import logging

from app.video.motion import MotionDetector
from app.recognition.plate_detector import PlateDetector
from app.recognition.ocr import PlateOCR

logging.basicConfig(level=logging.INFO)


from app.events.storage import PlateDedupStore

from app.recognition.tracker import PlateTracker

from app.video.threaded_reader import ThreadedRTSPReader


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

                cropped_boxes = [plate_detector.add_padding(frame, box) for box in boxes]

                for final_text, avg_conf, crop in ocr.read(cropped_boxes):
                    if not dedup_store.is_new(final_text):
                        print(f"[SKIP] {final_text} уже был обработан недавно")
                        continue

                    dedup_store.mark_seen(final_text)
                    print(f"[PLATE][FINAL] {final_text} (avg_conf={max(avg_conf):.2f})")

                    # if finished_track.best_crop is not None:
                    filename = f"scripts/files/{final_text}_{max(avg_conf):.2f}.jpg"
                    cv2.imwrite(filename, crop)

            time.sleep(settings.check_interval_sec)
    except KeyboardInterrupt:
        print("Остановлено")
    finally:
        reader.stop()


if __name__ == "__main__":
    main()
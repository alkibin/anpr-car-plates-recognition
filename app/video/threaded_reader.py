import os
os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "rtsp_transport;tcp")

import cv2
import logging
import threading
import time

logger = logging.getLogger(__name__)


class ThreadedRTSPReader:
    """
    Читает кадры из RTSP в отдельном фоновом потоке непрерывно,
    отбрасывая устаревшие кадры. Основной поток забирает только
    самый свежий доступный кадр через get_latest_frame().
    """

    def __init__(self, url: str, max_consecutive_failures: int = 5, reconnect_delay_sec: float = 1.0):
        self.url = url
        self.max_consecutive_failures = max_consecutive_failures
        self.reconnect_delay_sec = reconnect_delay_sec

        self._lock = threading.Lock()
        self._latest_frame = None
        self._running = False
        self._failure_count = 0

        self.cap = None
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)

    def _connect(self):
        self.cap = cv2.VideoCapture(self.url, cv2.CAP_FFMPEG)
        if not self.cap.isOpened():
            raise ConnectionError(f"Не удалось подключиться к потоку: {self.url}")
        logger.info("Подключение к потоку установлено: %s", self.url)
        self._failure_count = 0

    def start(self):
        self._running = True
        self._thread.start()

    def _capture_loop(self):
        self._connect()
        while self._running:
            ok, frame = self.cap.read()

            if not ok:
                self._failure_count += 1
                logger.warning("Не удалось прочитать кадр (%d/%d)", self._failure_count, self.max_consecutive_failures)

                if self._failure_count >= self.max_consecutive_failures:
                    logger.warning("Слишком много ошибок подряд, переподключаюсь к потоку")
                    self.cap.release()
                    time.sleep(self.reconnect_delay_sec)
                    try:
                        self._connect()
                    except ConnectionError:
                        logger.error("Не удалось переподключиться, повтор через %ss", self.reconnect_delay_sec)
                        time.sleep(self.reconnect_delay_sec)
                continue

            self._failure_count = 0
            with self._lock:
                self._latest_frame = frame

    def get_latest_frame(self):
        with self._lock:
            return self._latest_frame.copy() if self._latest_frame is not None else None

    def stop(self):
        self._running = False
        self._thread.join(timeout=2)
        self.cap.release()
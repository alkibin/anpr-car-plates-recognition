import cv2
import logging

logger = logging.getLogger(__name__)


class RTSPReader:
    """Обёртка над cv2.VideoCapture для чтения кадров из RTSP-потока."""

    def __init__(self, url: str):
        self.url = url
        self.cap = cv2.VideoCapture(url)
        if not self.cap.isOpened():
            raise ConnectionError(f"Не удалось подключиться к потоку: {url}")
        logger.info("Подключение к потоку установлено: %s", url)

    def read_frame(self):
        """Возвращает кадр (numpy array) или None, если чтение не удалось."""
        ok, frame = self.cap.read()
        if not ok:
            logger.warning("Не удалось прочитать кадр из потока")
            return None
        return frame

    def release(self):
        self.cap.release()
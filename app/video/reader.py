import cv2


class RTSPReader:
    def __init__(self, url: str):
        self.url = url
        self.cap = cv2.VideoCapture(url)

    def read(self):
        return self.cap.read()

    def release(self):
        self.cap.release()

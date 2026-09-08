import cv2


class MotionDetector:
    def __init__(self):
        self.bg = cv2.createBackgroundSubtractorMOG2()

    def detect(self, frame):
        mask = self.bg.apply(frame)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        return len(contours) > 0

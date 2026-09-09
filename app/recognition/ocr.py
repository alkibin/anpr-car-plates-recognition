import re
import math

import numpy as np
from paddleocr import PaddleOCR



LETTER_TO_DIGIT = {"O": "0", "D": "0", "I": "1", "Z": "2", "S": "5", "B": "8"}
DIGIT_TO_LETTER = {"0": "O", "1": "T", "8": "B", "6": "O"}

FULL_PATTERN = re.compile(r'^[A-Z0-9]{6,8}$', re.IGNORECASE)  # всего 6-8 символов
FULL_SQUARE_PATTERN = re.compile(r'^[A-Z0-9]{7,9}$', re.IGNORECASE)  # всего 7-9 символов
BODY_PATTERN = re.compile(r'^[A-Z0-9]{5,6}$', re.IGNORECASE)  # 5-6 символов
SQUARE_BODY_PATTERN = re.compile(r'^[A-Z0-9]{6}$', re.IGNORECASE)  # ровно 6 символов
REGION_PATTERN = re.compile(r'^[A-Z0-9]{2,3}$', re.IGNORECASE)


class PlateOCR:

    def __init__(self):
        self.ocr = PaddleOCR(
            text_recognition_model_name="PP-OCRv4_mobile_rec",
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            lang="en",
            ocr_version="PP-OCRv4",
            # text_det_limit_side_len=320,
        )

    def read(self, plates: list[np.ndarray]):
        results = []

        for plate in plates:
            result = self.ocr.predict(plate)
            if not result or not result[0].get("rec_texts"):
                continue

            texts = result[0]["rec_texts"]
            conf = result[0]["rec_scores"]
            box = result[0]["rec_boxes"]

            body_text = ""
            region_text = ""
            is_full_matched = False

            for i, text in enumerate(texts):
                cleaned_text = self._clean(text)

                if FULL_PATTERN.match(cleaned_text) or FULL_SQUARE_PATTERN.match(cleaned_text):
                    cleaned_text = self._fix_positional(cleaned_text)
                    results.append((cleaned_text, conf, plate))
                    is_full_matched = True
                    break
                if BODY_PATTERN.match(cleaned_text) or SQUARE_BODY_PATTERN.match(cleaned_text):
                    body_text = self._fix_positional(cleaned_text)

                if REGION_PATTERN.match(cleaned_text):
                    region_text = cleaned_text

            if is_full_matched:
                continue

            if not body_text or not region_text:
                continue
            results.append((body_text + region_text, conf, plate))

        return results

    @staticmethod
    def _clean(text: str) -> str:
        return text.upper().replace(" ", "").replace(".", "").replace("-", "")

    @staticmethod
    def _fix_positional(text: str) -> str:
        """Заменить цифры на буквы и наоборот на правильных местах номера."""
        if len(text) not in (8, 9):
            return text

        chars = list(text)
        letter_positions = [0, 4, 5]
        digit_positions = [1, 2, 3, 7, 8] + list(range(6, len(chars)))

        for i in letter_positions:
            if i < len(chars) and chars[i] in DIGIT_TO_LETTER:
                chars[i] = DIGIT_TO_LETTER[chars[i]]
        for i in digit_positions:
            if i < len(chars) and chars[i] in LETTER_TO_DIGIT:
                chars[i] = LETTER_TO_DIGIT[chars[i]]
        return "".join(chars)



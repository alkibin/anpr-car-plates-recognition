class OCREngine:
    def __init__(self, engine: str = "easyocr"):
        self.engine = engine
        if engine == "easyocr":
            import easyocr
            self.reader = easyocr.Reader(["en"])
        else:
            self.reader = None

    def recognize(self, image) -> str:
        if self.engine == "easyocr" and self.reader:
            results = self.reader.readtext(image)
            return " ".join([r[1] for r in results])
        return ""

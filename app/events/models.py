"""Pydantic-модель события распознавания номера."""

from datetime import datetime
from pydantic import BaseModel


class RecognitionEvent(BaseModel):
    """Событие распознавания номера: текст, уверенность, время, кадр и камера."""
    id: int | None = None
    plate_text: str
    confidence: float
    timestamp: datetime = datetime.now()
    frame_path: str = ""
    camera_id: str = ""

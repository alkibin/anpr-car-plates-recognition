from datetime import datetime
from pydantic import BaseModel


class RecognitionEvent(BaseModel):
    id: int | None = None
    plate_text: str
    confidence: float
    timestamp: datetime = datetime.now()
    frame_path: str = ""
    camera_id: str = ""

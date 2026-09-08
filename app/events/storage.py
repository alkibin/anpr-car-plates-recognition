import sqlite3
from app.events.models import RecognitionEvent


class EventStorage:
    def __init__(self, db_path: str = "data/anpr.db"):
        self.conn = sqlite3.connect(db_path)
        self._init_db()

    def _init_db(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plate_text TEXT,
                confidence REAL,
                timestamp TEXT,
                frame_path TEXT,
                camera_id TEXT
            )
        """)
        self.conn.commit()

    def save(self, event: RecognitionEvent):
        self.conn.execute(
            "INSERT INTO events (plate_text, confidence, timestamp, frame_path, camera_id) VALUES (?, ?, ?, ?, ?)",
            (event.plate_text, event.confidence, event.timestamp.isoformat(), event.frame_path, event.camera_id),
        )
        self.conn.commit()

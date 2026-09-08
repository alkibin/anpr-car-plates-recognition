from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    rtsp_url: str = "rtsp://localhost:8554/stream"
    onvif_ip: str = ""
    onvif_port: int = 80
    onvif_user: str = "admin"
    onvif_password: str = "admin"
    database_url: str = "sqlite:///data/anpr.db"
    webhook_url: str = ""
    yolo_model: str = "yolov8n.pt"
    ocr_engine: str = "easyocr"

    class Config:
        env_file = ".env"


settings = Settings()

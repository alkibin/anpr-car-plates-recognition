"""Клиент для работы с IP-камерами по протоколу ONVIF."""


class ONVIFClient:
    """Управляет IP-камерой: обнаружение, RTSP-поток и подписка на события."""

    def __init__(self, ip: str, port: int, user: str, password: str):
        """Сохраняет параметры подключения к ONVIF-камере."""
        self.ip = ip
        self.port = port
        self.user = user
        self.password = password

    def discover(self):
        """Находит устройства на сети по параметрам подключения (заглушка)."""
        pass

    def get_stream_uri(self) -> str:
        """Формирует RTSP-URI видеопотока камеры."""
        return f"rtsp://{self.ip}:554/stream"

    def subscribe_events(self):
        """Подписывается на события камеры (заглушка)."""
        pass
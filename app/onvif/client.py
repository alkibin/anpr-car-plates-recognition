class ONVIFClient:
    def __init__(self, ip: str, port: int, user: str, password: str):
        self.ip = ip
        self.port = port
        self.user = user
        self.password = password

    def discover(self):
        pass

    def get_stream_uri(self) -> str:
        return f"rtsp://{self.ip}:554/stream"

    def subscribe_events(self):
        pass

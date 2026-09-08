import httpx
from app.events.models import RecognitionEvent


class WebhookSender:
    def __init__(self, url: str):
        self.url = url

    async def send(self, event: RecognitionEvent):
        if self.url:
            async with httpx.AsyncClient() as client:
                await client.post(self.url, json=event.model_dump(mode="json"))

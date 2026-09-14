"""Отправка событий распознавания во внешние вебхуки (async HTTP)."""

import httpx
from app.events.models import RecognitionEvent


class WebhookSender:
    """Отправляет события распознавания номеров во внешний сервис по URL."""

    def __init__(self, url: str):
        """Сохраняет URL вебхука для последующей отправки событий."""
        self.url = url

    async def send(self, event: RecognitionEvent):
        """Асинхронно POST-ом доставляет событие на вебхук (если URL задан)."""
        if self.url:
            async with httpx.AsyncClient() as client:
                await client.post(self.url, json=event.model_dump(mode="json"))
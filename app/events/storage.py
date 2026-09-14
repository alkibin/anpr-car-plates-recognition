"""Redis-хранилище для дедупликации уже распознанных номеров."""

import redis


class PlateDedupStore:
    """
    Хранилище уже увиденных номеров в Redis.
    Ключ — сам номер, TTL — чтобы через какое-то время номер снова
    считался "новым" (машина может уехать и вернуться завтра).
    """

    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0, ttl_seconds: int = 3600):
        """Подключается к Redis и сохраняет TTL для ключей «виденных» номеров."""
        self.client = redis.Redis(host=host, port=port, db=db, decode_responses=True)
        self.ttl_seconds = ttl_seconds

    def is_new(self, plate_text: str) -> bool:
        """True, если номер ранее не встречался (или его TTL истёк)."""
        return self.client.get(self._key(plate_text)) is None

    def mark_seen(self, plate_text: str) -> None:
        """Помечает номер как увиденный, обновляя TTL его Redis-ключа."""
        self.client.set(self._key(plate_text), "1", ex=self.ttl_seconds)

    @staticmethod
    def _key(plate_text: str) -> str:
        """Строит Redis-ключ для заданного номера."""
        return f"seen_plate:{plate_text}"

    def should_upload_crop(self, plate_text: str, ttl_seconds: int = 86400) -> bool:
        """True, если кроп ещё не загружался за последние ttl_seconds.

        Каждый вызов с уникальным ttl_seconds создаёт отдельный ключ,
        поэтому дефолтные 24 ч (86400 с) не пересекаются с TTL основного
        ключа дедупликации seen_plate.
        """
        key = f"crop_throttle:{plate_text}"
        if self.client.get(key) is not None:
            return False
        self.client.set(key, "1", ex=ttl_seconds)
        return True
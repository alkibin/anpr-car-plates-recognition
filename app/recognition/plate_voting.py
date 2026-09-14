"""Голосование по распознанным вариантам номера за небольшое окно кадров."""

from collections import Counter


class PlateVotingBuffer:
    """
    Копит распознанные варианты номера за короткое окно времени
    (пока машина в кадре) и на выходе отдаёт наиболее частый вариант.
    Простая версия без полноценного object tracking —
    группировка по географической близости bbox между кадрами.
    """

    def __init__(self, max_votes: int = 5):
        """Сохраняет размер окна и обнуляет список голосов."""
        self.max_votes = max_votes
        self.votes: list[tuple[str, float]] = []

    def add(self, text: str, confidence: float) -> None:
        """Добавляет вариант номера и вытесняет старейший голос при переполнении."""
        self.votes.append((text, confidence))
        if len(self.votes) > self.max_votes:
            self.votes.pop(0)

    def best_guess(self) -> tuple[str, float] | None:
        """Возвращает самый частый вариант номера и его среднюю уверенность."""
        if not self.votes:
            return None
        texts = [t for t, _ in self.votes]
        most_common_text, count = Counter(texts).most_common(1)[0]
        avg_conf = sum(c for t, c in self.votes if t == most_common_text) / count
        return most_common_text, avg_conf
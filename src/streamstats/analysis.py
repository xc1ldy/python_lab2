from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime

from streamstats.models import Event, Level

ERROR_LEVELS = frozenset({Level.ERROR, Level.CRITICAL})
TOP_ERROR_SOURCES = 5


@dataclass
class StreamStats:
    """Один объект накапливает статистику по всем событиям"""

    total: int = 0
    by_level: Counter[Level] = field(default_factory=Counter)
    by_source: Counter[str] = field(default_factory=Counter)
    error_sources: Counter[str] = field(default_factory=Counter)
    first_timestamp: datetime | None = None
    last_timestamp: datetime | None = None
    skipped_lines: int = 0

    def add(self, event: Event) -> None:
        """
        Обработка одного события, сохраняем только счетчики, а не сами события
        Args:
            event: событие
        Raises: None
        Returns: счетчики события
        """
        self.total += 1
        self.by_level[event.level] += 1
        self.by_source[event.source] += 1
        if event.level in ERROR_LEVELS:
            self.error_sources[event.source] += 1
        if self.first_timestamp is None or event.timestamp < self.first_timestamp:
            self.first_timestamp = event.timestamp
        if self.last_timestamp is None or event.timestamp > self.last_timestamp:
            self.last_timestamp = event.timestamp

    def consume(self, events: Iterable[Event]) -> None:
        """
        Обработать все события по очереди
        Args:
            events: события
        Raises: None
        Returns: счетчики событий
        """
        for event in events:
            self.add(event)

    def record_skipped(self) -> None:
        """
        Обработать пропущенную ошибочную строку
        Args: None
        Raises: None
        Returns: счетчик пропущенных строк
        """
        self.skipped_lines += 1

    def top_error_sources(
        self, limit: int = TOP_ERROR_SOURCES
    ) -> list[tuple[str, int]]:
        """
        Топ источников ERROR/CRITICAL
        Args:
            limit: количество источников для учета
        Raises: None
        Returns: топ источников
        """
        ranked = sorted(
            self.error_sources.items(), key=lambda item: (-item[1], item[0])
        )
        return ranked[:limit]

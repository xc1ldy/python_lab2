import logging
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

from streamstats.errors import CLIConfigError, InvalidEventError
from streamstats.models import Event, Level
from streamstats.parsers import get_parser

logger = logging.getLogger(__name__)

ERROR_LEVELS = frozenset({Level.ERROR, Level.CRITICAL})
TOP_ERROR_SOURCES = 5


class ErrorSource(NamedTuple):
    """Источник ошибки ERROR или CRITICAL и количество CRITICAL"""

    source: str
    total: int
    critical: int


@dataclass
class StreamStats:
    """Один объект накапливает статистику по всем событиям"""

    total: int = 0
    by_level: Counter[Level] = field(default_factory=Counter)
    by_source: Counter[str] = field(default_factory=Counter)
    error_sources: Counter[str] = field(default_factory=Counter)
    critical_sources: Counter[str] = field(default_factory=Counter)
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
            if event.level == Level.CRITICAL:
                self.critical_sources[event.source] += 1
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

    def top_error_sources(self, limit: int = TOP_ERROR_SOURCES) -> list[ErrorSource]:
        """
        Топ источников ERROR/CRITICAL
        Args:
            limit: количество источников для учета
        Raises: None
        Returns: топ источников
        """
        sources = (
            ErrorSource(source, count, self.critical_sources[source])
            for source, count in self.error_sources.items()
        )
        ranked = sorted(
            sources, key=lambda item: (-item.critical, -item.total, item.source)
        )
        return ranked[:limit]


def analyze_files(
    paths: Sequence[Path], fmt: str, *, skip_invalid: bool = False
) -> StreamStats:
    """
     Прочитать все файлы и получить общую статистику
     Args:
         paths: пути к файлам
         fmt: формат (один для всех файлов)
         skip_invalid: пропускать пустые строки или нет
    Raises: описывает ошибку в зависимости от того с какой ошибкой падает
    Returns: статистику
    """
    parser = get_parser(fmt)
    stats = StreamStats()

    def skip(error: InvalidEventError) -> None:
        logger.warning("Skipping invalid line: %s", error)
        stats.record_skipped()

    on_error = skip if skip_invalid else None
    for path in paths:
        try:
            stats.consume(parser(path, on_error))
        except UnicodeDecodeError as exc:
            raise InvalidEventError(f"{path}: file is not valid UTF-8") from exc
        except OSError as exc:
            message = f"{path}: {exc.strerror or type(exc).__name__}"
            raise CLIConfigError(message) from exc
    return stats

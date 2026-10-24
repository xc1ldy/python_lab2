import json
from datetime import datetime
from pathlib import Path
from typing import TypedDict

from streamstats.analysis import StreamStats
from streamstats.models import Level


class TopErrorSource(TypedDict):
    source: str
    count: int
    critical: int


class Report(TypedDict):
    total: int
    by_level: dict[str, int]
    by_source: dict[str, int]
    top_error_sources: list[TopErrorSource]
    first_timestamp: str | None
    last_timestamp: str | None
    skipped_lines: int


def _format_timestamp(value: datetime | None) -> str | None:
    """
    Если есть события, то возращает время
    Args:
        value: время
    Raises: None
    Returns: время если есть события, иначе None
    """
    return None if value is None else value.isoformat()


def build_report(stats: StreamStats) -> Report:
    """
    Собрать структуру отчета из статистики
    Args:
        stats: статистика
    Raises: None
    Returns: отчет
    """
    by_source = sorted(stats.by_source.items(), key=lambda item: (-item[1], item[0]))

    return {
        "total": stats.total,
        "by_level": {level.value: stats.by_level[level] for level in Level},
        "by_source": dict(by_source),
        "top_error_sources": [
            {
                "source": item.source,
                "count": item.total,
                "critical": item.critical,
            }
            for item in stats.top_error_sources()
        ],
        "first_timestamp": _format_timestamp(stats.first_timestamp),
        "last_timestamp": _format_timestamp(stats.last_timestamp),
        "skipped_lines": stats.skipped_lines,
    }


def render_report(report: Report) -> str:
    """
    Обернуть отчет в json
    Args:
        report: отчет
    Raises: None
    Returns: отчет в json
    """
    return json.dumps(report, ensure_ascii=False, indent=2)


def write_report(report: Report, path: Path) -> None:
    """
    Записать отчет в файл
    Args:
        report: отчет
        path: путь к файлу для записи
    Raises: OSError, ловится в _emit
    Returns: None
    """
    path.write_text(render_report(report) + "\n", encoding="utf-8")

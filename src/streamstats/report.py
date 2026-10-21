import json
from datetime import datetime
from pathlib import Path

from streamstats.analysis import StreamStats
from streamstats.models import Level


def _format_timestamp(value: datetime | None) -> str | None:
    """
    Если есть события, то возращает время
    Args:
        value: время
    Raises: None
    Returns: время если есть события, иначе None
    """
    return None if value is None else value.isoformat()


def build_report(stats: StreamStats) -> dict[str, object]:
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
            {"source": source, "count": count}
            for source, count in stats.top_error_sources()
        ],
        "first_timestamp": _format_timestamp(stats.first_timestamp),
        "last_timestamp": _format_timestamp(stats.last_timestamp),
        "skipped_lines": stats.skipped_lines,
    }


def render_report(report: dict[str, object]) -> str:
    """
    Обернуть отчет в json
    Args:
        report: отчет
    Raises: None
    Returns: отчет в json
    """
    return json.dumps(report, ensure_ascii=False, indent=2)


def write_report(report: dict[str, object], path: Path) -> None:
    """
    Записать отчет в файл
    Args:
        report: отчет
        path: путь к файлу для записи
    Raises: None
    Returns: отчет, записанный в файл
    """
    path.write_text(render_report(report) + "\n", encoding="utf-8")

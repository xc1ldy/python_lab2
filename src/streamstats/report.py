import json
from datetime import datetime
from pathlib import Path

from streamstats.analysis import StreamStats
from streamstats.models import Level


def _format_timestamp(value: datetime | None) -> str | None:
    return None if value is None else value.isoformat()


def build_report(stats: StreamStats) -> dict[str, object]:
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
    return json.dumps(report, ensure_ascii=False, indent=2)


def write_report(report: dict[str, object], path: Path) -> None:
    path.write_text(render_report(report) + "\n", encoding="utf-8")

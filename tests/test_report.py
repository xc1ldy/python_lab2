from streamstats.analysis import StreamStats
from streamstats.models import Event
from streamstats.report import build_report

LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


def make_event(level: str, source: str, timestamp: str) -> Event:
    raw = {"timestamp": timestamp, "level": level, "source": source, "message": "m"}
    return Event.model_validate(raw)


def test_empty_stats_gives_zero_report() -> None:
    assert build_report(StreamStats()) == {
        "total": 0,
        "by_level": dict.fromkeys(LEVELS, 0),
        "by_source": {},
        "top_error_sources": [],
        "first_timestamp": None,
        "last_timestamp": None,
        "skipped_lines": 0,
    }


def test_report_content_and_order() -> None:
    stats = StreamStats()
    stats.consume(
        [
            make_event("INFO", "db", "2026-09-01T10:00:00+00:00"),
            make_event("ERROR", "api", "2026-09-01T12:00:00+00:00"),
            make_event("CRITICAL", "api", "2026-09-02T00:00:00+00:00"),
        ]
    )
    stats.record_skipped()

    report = build_report(stats)
    assert list(report["by_level"]) == LEVELS
    assert report["by_level"] == {
        "DEBUG": 0,
        "INFO": 1,
        "WARNING": 0,
        "ERROR": 1,
        "CRITICAL": 1,
    }
    assert list(report["by_source"].items()) == [("api", 2), ("db", 1)]
    assert report["top_error_sources"] == [{"source": "api", "count": 2, "critical": 1}]
    assert report["first_timestamp"] == "2026-09-01T10:00:00+00:00"
    assert report["last_timestamp"] == "2026-09-02T00:00:00+00:00"
    assert (report["total"], report["skipped_lines"]) == (3, 1)

import json
from pathlib import Path

import pytest

from streamstats.analysis import StreamStats, analyze_files
from streamstats.errors import CLIConfigError
from streamstats.models import Event, Level

TS = "2026-09-01T12:00:00+00:00"


def make_event(level: str, source: str, timestamp: str = TS) -> Event:
    raw = {"timestamp": timestamp, "level": level, "source": source, "message": "m"}
    return Event.model_validate(raw)


def write_jsonl(tmp_path: Path, name: str, *events: tuple[str, str] | str) -> Path:
    lines = []
    for event in events:
        if isinstance(event, str):
            lines.append(event)
        else:
            level, source = event
            data = {"timestamp": TS, "level": level, "source": source, "message": "m"}
            lines.append(json.dumps(data))
    path = tmp_path / name
    path.write_bytes("".join(line + "\n" for line in lines).encode("utf-8"))
    return path


def test_counts_event_by_level_and_source() -> None:
    stats = StreamStats()
    stats.consume(
        [
            make_event("ERROR", "api"),
            make_event("ERROR", "db"),
            make_event("INFO", "api"),
            make_event("DEBUG", "web"),
        ]
    )

    assert stats.total == 4
    assert stats.by_level == {Level.ERROR: 2, Level.INFO: 1, Level.DEBUG: 1}
    assert stats.by_source == {"api": 2, "db": 1, "web": 1}


def test_top_error_sources_ranks_critical_first() -> None:
    stats = StreamStats()
    stats.consume(
        [make_event("ERROR", "noisy")] * 5
        + [make_event("CRITICAL", "fatal-b"), make_event("CRITICAL", "fatal-a")]
        + [make_event("CRITICAL", "mixed")]
        + [make_event("ERROR", "mixed")] * 2
        + [make_event("INFO", "chatty")] * 10
    )

    assert stats.top_error_sources() == [
        ("mixed", 3, 1),
        ("fatal-a", 1, 1),
        ("fatal-b", 1, 1),
        ("noisy", 5, 0),
    ]


def test_top_error_is_limited_to_five() -> None:
    stats = StreamStats()
    stats.consume([make_event("ERROR", f"source-{number}") for number in range(7)])
    assert len(stats.top_error_sources()) == 5


def test_analyze_files_merges_several_files(tmp_path: Path) -> None:
    first = write_jsonl(tmp_path, "first.jsonl", ("ERROR", "api"), ("INFO", "db"))
    second = write_jsonl(tmp_path, "second.jsonl", ("ERROR", "api"))
    stats = analyze_files([first, second], "jsonl")
    assert stats.by_source == {"api": 2, "db": 1}


def test_skip_invalid_counts_bad_lines(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    path = write_jsonl(
        tmp_path, "events.jsonl", ("ERROR", "api"), "this is not json", ("INFO", "db")
    )
    stats = analyze_files([path], "jsonl", skip_invalid=True)
    assert stats.skipped_lines == 1
    warnings = [record for record in caplog.records if record.levelname == "WARNING"]
    assert len(warnings) == 1
    assert f"{path}:2:" in warnings[0].getMessage()


def test_missing_file_raises_config_error(tmp_path: Path) -> None:
    with pytest.raises(CLIConfigError):
        analyze_files([tmp_path / "missing.jsonl"], "jsonl")

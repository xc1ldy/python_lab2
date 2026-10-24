import json
from pathlib import Path

import pytest

from streamstats.errors import (
    EmptyFileError,
    InvalidEventError,
    InvalidTimestampError,
    UnsupportedFormatError,
)
from streamstats.parsers import get_parser

FORMATS = ["jsonl", "csv"]
TS = "2026-09-01T12:00:00+00:00"
CSV_HEADER = "timestamp,level,source,message\n"
BAD_LINES = {"jsonl": "this is not json\n", "csv": "only,three,fields\n"}
EMPTY_FILES = [(fmt, text) for fmt in FORMATS for text in ["", "\n   \n\n"]]


def write(tmp_path: Path, fmt: str, content: str | bytes) -> Path:
    path = tmp_path / f"events.{fmt}"
    path.write_bytes(content.encode("utf-8") if isinstance(content, str) else content)
    return path


def good_line(fmt: str, *, source: str = "api", message: str = "boom") -> str:
    if fmt == "jsonl":
        data = {"timestamp": TS, "level": "ERROR", "source": source, "message": message}
        return json.dumps(data, ensure_ascii=False) + "\n"
    return f"{TS},ERROR,{source},{message}\n"


def build(fmt: str, *lines: str) -> str:
    return (CSV_HEADER if fmt == "csv" else "") + "".join(lines)


@pytest.mark.parametrize("fmt", FORMATS)
def test_reads_valid_events(fmt: str, tmp_path: Path) -> None:
    text = build(fmt, good_line(fmt, source="api"), good_line(fmt, source="db"))
    events = list(get_parser(fmt)(write(tmp_path, fmt, text), None))
    assert [event.source for event in events] == ["api", "db"]


@pytest.mark.parametrize("fmt, content", EMPTY_FILES)
def test_empty_file_raises_in_both_modes(
    fmt: str, content: str, tmp_path: Path
) -> None:
    path = write(tmp_path, fmt, content)
    parser = get_parser(fmt)
    with pytest.raises(EmptyFileError):
        list(parser(path, None))
    with pytest.raises(EmptyFileError):
        list(parser(path, lambda error: None))


@pytest.mark.parametrize("fmt, bad_line_no", [("jsonl", 3), ("csv", 4)])
def test_bad_line_stops_processing_by_default(
    fmt: str, bad_line_no: int, tmp_path: Path
) -> None:
    text = build(fmt, good_line(fmt), "\n", BAD_LINES[fmt], good_line(fmt))
    path = write(tmp_path, fmt, text)
    events = get_parser(fmt)(path, None)
    next(events)
    with pytest.raises(InvalidEventError) as exc_info:
        next(events)

    assert f"{path}:{bad_line_no}" in str(exc_info.value)


@pytest.mark.parametrize("fmt", FORMATS)
def test_skip_mode_reports_bad_line(fmt: str, tmp_path: Path) -> None:
    text = build(fmt, good_line(fmt), BAD_LINES[fmt])
    errors: list[InvalidEventError] = []

    events = list(get_parser(fmt)(write(tmp_path, fmt, text), errors.append))
    assert len(events) == 1
    assert len(errors) == 1


def test_bad_timestamp_raises_timestamp_error(tmp_path: Path) -> None:
    line = good_line("jsonl").replace(TS, "вчера")
    with pytest.raises(InvalidTimestampError):
        list(get_parser("jsonl")(write(tmp_path, "jsonl", line), None))


def test_missing_timestamp_is_not_a_timestamp_error(tmp_path: Path) -> None:
    line = json.dumps({"level": "ERROR", "source": "api", "message": "boom"}) + "\n"

    with pytest.raises(InvalidEventError) as exc_info:
        list(get_parser("jsonl")(write(tmp_path, "jsonl", line), None))

    assert not isinstance(exc_info.value, InvalidTimestampError)


def test_csv_missing_column_is_fatal_even_in_skip_mode(tmp_path: Path) -> None:
    path = write(tmp_path, "csv", f"timestamp,level,source\n{TS},ERROR,api\n")
    errors: list[InvalidEventError] = []
    with pytest.raises(InvalidEventError):
        list(get_parser("csv")(path, errors.append))

    assert errors == []


def test_unknown_format_is_rejected() -> None:
    with pytest.raises(UnsupportedFormatError):
        get_parser("xml")

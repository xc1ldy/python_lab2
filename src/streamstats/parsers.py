import csv
import json
from collections.abc import Callable, Iterator
from pathlib import Path

from pydantic import ValidationError

from streamstats.errors import (
    EmptyFileError,
    InvalidEventError,
    InvalidTimestampError,
    UnsupportedFormatError,
)
from streamstats.models import Event

OnError = Callable[[InvalidEventError], None]
ParserFunc = Callable[[Path, OnError | None], Iterator[Event]]

ENCODING = "utf-8"
REQUIRED_COLUMNS = ("timestamp", "level", "source", "message")

def _describe(exc: ValidationError) -> str:
    parts: list[str] = []
    for error in exc.errors():
        field = ".".join(str(item) for item in error["loc"]) or "event"
        parts.append(f"{field}: {error['msg']}")
    return "; ".join(parts)


def _validate_event(raw: object, path: Path, line_no: int) -> Event:
    try:
        return Event.model_validate(raw)
    except ValidationError as exc:
        message = f"{path}:{line_no}: {_describe(exc)}"
        if any(
            error["loc"] == ("timestamp",) and error["type"] != "missing"
            for error in exc.errors()
        ):
            raise InvalidTimestampError(message) from exc
        raise InvalidEventError(message) from exc


def _parse_jsonl_line(line: str, path: Path, line_no: int) -> Event:
    try:
        raw = json.loads(line)
    except json.JSONDecodeError as exc:
        message = f"{path}:{line_no}: Invalid JSON: {exc.msg}"
        raise InvalidEventError(message) from exc
    return _validate_event(raw, path, line_no)


def _is_blank_row(row: list[str]) -> bool:
    if not row:
        return True
    return len(row) == 1 and not row[0].strip()


def _read_header(row: list[str], path: Path, line_no: int) -> list[str]:
    header = [name.strip() for name in row]
    missing = [name for name in REQUIRED_COLUMNS if name not in header]
    if missing:
        message = f"{path}:{line_no}: missing columns {', '.join(missing)}"
        raise InvalidEventError(message)
    return header


def _parse_csv_row(
        row: list[str], header: list[str], path: Path, line_no: int
) -> Event:
    if len(row) != len(header):
        message = f"{path}:{line_no}: expected {len(header)} fields, got {len(row)}"
        raise InvalidEventError(message)
    return _validate_event(dict(zip(header, row, strict=True)), path, line_no)


def _parse_jsonl(path: Path, on_error: OnError | None = None) -> Iterator[Event]:
    has_content = False
    with (path.open(encoding=ENCODING) as file):
        for line_no, line in enumerate(file, start=1):
            if not line.strip():
                continue
            has_content = True
            try:
                event = _parse_jsonl_line(line, path, line_no)
            except InvalidEventError as exc:
                if on_error is None:
                    raise
                on_error(exc)
                continue
            yield event
    if not has_content:
        raise EmptyFileError(f"{path}: file is empty")


def parse_csv(path: Path, on_error: OnError | None = None) -> Iterator[Event]:
    header: list[str] | None = None
    with path.open(encoding=ENCODING, newline="") as file:
        reader = csv.reader(file)
        for row in reader:
            if _is_blank_row(row):
                continue
            line_no = reader.line_num
            if header is None:
                header = _read_header(row, path, line_no)
                continue
            try:
                event = _parse_csv_row(row, header, path, line_no)
            except InvalidEventError as exc:
                if on_error is None:
                    raise
                on_error(exc)
                continue
            yield event
        if header is None:
            raise EmptyFileError(f"{path}: file is empty")


PARSERS: dict[str, ParserFunc] = {"csv": parse_csv, "jsonl": _parse_jsonl}


def get_parser(fmt: str) -> ParserFunc:
    try:
        return PARSERS[fmt]
    except KeyError as exc:
        supported = ", ".join(sorted(PARSERS))
        message = f"Unsupported format: {fmt!r}. Supported formats: {supported}"
        raise UnsupportedFormatError(message) from exc

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
    """
    Создание описания ошибок pydantic
    Args:
        exc: входящие ошибки
    Returns: описание ошибок
    """
    parts: list[str] = []
    for error in exc.errors():
        field = ".".join(str(item) for item in error["loc"]) or "event"
        parts.append(f"{field}: {error['msg']}")
    return "; ".join(parts)


def _validate_event(raw: object, path: Path, line_no: int) -> Event:
    """
    Валидация события
    Args:
        raw: событие
        path: путь к файлу
        line_no: номер строки
    Raises: ошибка формата времени, если он не соблюден,
            в остальных случая ошибка формата события
    Returns: валидированное событие
    """
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
    """
    Парс одной непустой строки jsonl
    Args:
        line: строка jsonl
        path: путь к файлу
        line_no: номер строки
    Raises: если падает, то ошибка формата события
    Returns: валидированное событие
    """
    try:
        raw = json.loads(line)
    except json.JSONDecodeError as exc:
        message = f"{path}:{line_no}: Invalid JSON: {exc.msg}"
        raise InvalidEventError(message) from exc
    return _validate_event(raw, path, line_no)


def _is_blank_row(row: list[str]) -> bool:
    """
    Проверка пустой строки
    Args:
        row: строка для проверки
    Returns: True если пустая строка, False иначе
    """
    if not row:
        return True
    return len(row) == 1 and not row[0].strip()


def _read_header(row: list[str], path: Path, line_no: int) -> list[str]:
    """
    Валидация заголовка csv
    Args:
        row: строка
        path: путь к файлу
        line_no: номер строки
    Raises: если в заголовке отсутствуют нужные колонки, то ошибка формата события
    Returns: заголовок
    """
    header = [name.strip() for name in row]
    missing = [name for name in REQUIRED_COLUMNS if name not in header]
    if missing:
        message = f"{path}:{line_no}: missing columns {', '.join(missing)}"
        raise InvalidEventError(message)
    return header


def _parse_csv_row(
    row: list[str], header: list[str], path: Path, line_no: int
) -> Event:
    """
    Парс непустой строки csv
    Args:
        row: строка
        header: заголовок
        path: путь к файлу
        line_no: номер строки
    Raises: если длина некорректна, то ошибка формата события
    Returns: валидированное событие
    """
    if len(row) != len(header):
        message = f"{path}:{line_no}: expected {len(header)} fields, got {len(row)}"
        raise InvalidEventError(message)
    return _validate_event(dict(zip(header, row, strict=True)), path, line_no)


def _parse_jsonl(path: Path, on_error: OnError | None = None) -> Iterator[Event]:
    """
    Лениво читать события jsonl
    Args:
        path: путь к файлу
        on_error:
        без on_error - встречаем ошибочную строку -> падает с ошибкой формата события
        c on_error - запоминаем ошибку, читаем дальше
    Raises: файл без непустых строк падает с ошибкой пустого файла
    Returns: список событий
    """
    has_content = False
    with path.open(encoding=ENCODING) as file:
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
    """
    Лениво читать события csv
    Args:
        path: путь к файлу
        on_error:
        без on_error - встречаем ошибочную строку -> падает с ошибкой формата события
        c on_error - запоминаем ошибку, читаем дальше
    Raises: ошибка заголовка не пропускается даже с on_error,
            падает с ошибкой пустого файла
    Returns: список событий
    """
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
    """
    Выбор парсера в зависимости от формата
    Args:
        fmt: формат парсера
    Raises: если неподдерживаемый парсер, то падает с ошибкой неподдерживаемого формата
    Returns: парсер
    """
    try:
        return PARSERS[fmt]
    except KeyError as exc:
        supported = ", ".join(sorted(PARSERS))
        message = f"Unsupported format: {fmt!r}. Supported formats: {supported}"
        raise UnsupportedFormatError(message) from exc

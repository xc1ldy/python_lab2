# streamstats

Потоковый анализатор файлов событий. Читает CSV и JSONL построчно (файл не загружается в память целиком) и формирует JSON-отчёт со статистикой.

## Требования

- Python 3.14 или новее
- [uv](https://docs.astral.sh/uv/)

## Установка

```bash
uv sync
```

## Запуск

```bash
uv run python -m streamstats analyze INPUT [INPUT ...] --format csv|jsonl --output REPORT.json
uv run python -m streamstats analyze INPUT --format jsonl --skip-invalid
uv run python -m streamstats --help
```

| Параметр | Описание |
|---|---|
| `INPUT` | Один или несколько входных файлов (все в одном формате) |
| `--format` | `csv` или `jsonl` (обязателен, строчными буквами) |
| `--output` | Файл для отчёта. Без него отчёт печатается в stdout |
| `--skip-invalid` | Пропускать ошибочные строки вместо остановки |

## Входные данные

Кодировка UTF-8 (BOM допускается). Обязательные поля события:

| Поле | Правило |
|---|---|
| `timestamp` | Строка ISO 8601 |
| `level` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` (точное совпадение регистра) |
| `source` | Непустая строка (пробелы по краям обрезаются) |
| `message` | Строка (может быть пустой) |

CSV: первая непустая строка это заголовок, дополнительные колонки игнорируются. JSONL: один JSON-объект на строку.

## Отчёт

```json
{
  "total": 3,
  "by_level": {"DEBUG": 0, "INFO": 1, "WARNING": 0, "ERROR": 1, "CRITICAL": 1},
  "by_source": {"api": 2, "db": 1},
  "top_error_sources": [{"source": "api", "count": 2, "critical": 1}],
  "first_timestamp": "2024-05-01T10:00:00+00:00",
  "last_timestamp": "2024-05-02T00:00:00+00:00",
  "skipped_lines": 0
}
```

- `by_level` содержит все пять уровней, включая нулевые.
- `by_source` отсортирован по убыванию числа событий, при равенстве по имени.
- `top_error_sources`: до 5 источников событий ERROR и CRITICAL. CRITICAL важнее: сначала больше CRITICAL, затем больше ошибок всего (`count`), затем имя. `critical` это число CRITICAL среди `count`.
- Если событий нет, метки равны `null`, `by_source` и топ пусты.

## Обработка ошибок

- **По умолчанию** первая ошибочная строка останавливает обработку: в stderr выводится `Error: файл:строка: причина`, код выхода 2, отчёт не создаётся.
- **С `--skip-invalid`** строка пропускается, в лог пишется WARNING (stderr), число пропущенных попадает в `skipped_lines`.
- Пустые строки пропускаются всегда и пропущенными не считаются. Запись CSV из пустых полей (`,,,`) пустой строкой не считается.
- Ошибка заголовка CSV (нет обязательной колонки) и файл не в UTF-8 фатальны даже с `--skip-invalid`.
- Файл без единой непустой строки это ошибка (`EmptyFileError`) в обоих режимах.
- Любая ошибка проекта (`StreamStatsError`: неподдерживаемый формат, неверное событие, неверная метка, пустой файл, ошибка конфигурации CLI, например файл не найден) даёт код выхода 2.

## Принятые решения

- Время приводится к UTC: метка без пояса считается UTC. Дата без времени (`2026-09-01`) допустима.
- `InvalidTimestampError` наследуется от `InvalidEventError`; `EmptyFileError` от `StreamStatsError` напрямую, чтобы `--skip-invalid` его не проглатывал.
- Источники `API` и `api` считаются разными.
- Память зависит от числа разных источников, а не от размера файла.

## Структура

```text
src/streamstats/
  __main__.py   CLI (Typer)
  models.py     Event, Level (Pydantic)
  parsers.py    парсеры CSV и JSONL, реестр форматов
  analysis.py   накопление статистики, analyze_files
  report.py     построение и запись JSON-отчёта
  errors.py     исключения
tests/
```

## Проверка

```bash
uv run pytest
uv run ruff check .
uv run mypy src
uv run python -m streamstats --help
```
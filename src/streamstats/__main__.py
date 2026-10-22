import logging
from pathlib import Path
from typing import Annotated

import typer

from streamstats.analysis import analyze_files
from streamstats.errors import CLIConfigError, StreamStatsError
from streamstats.parsers import PARSERS
from streamstats.report import build_report, render_report, write_report

EXIT_ERROR = 2

app = typer.Typer(
    help="Потоковый анализатор событий файлов CSV и JSONL",
    no_args_is_help=True,
)


def _emit(report: dict[str, object], output: Path | None) -> None:
    """
    Вывод отчета в stdout или запись в файл
    Args:
        report: отчет
        output: путь к файлу для вывода либо None, для вывода в stdout
    Raises: сообщение ошибки если не удается записать
    Returns: None
    """
    if output is None:
        typer.echo(render_report(report))
        return
    try:
        write_report(report, output)
    except OSError as exc:
        message = f"{output}: {exc.strerror or type(exc).__name__}"
        raise CLIConfigError(message) from exc


@app.callback()
def main() -> None:
    """Потоковый анализатор файлов событий"""


@app.command()
def analyze(
    inputs: Annotated[list[Path], typer.Argument(help="Входные файлы")],
    fmt: Annotated[
        str,
        typer.Option("--format", help=f"Формат: {', '.join(sorted(PARSERS))}"),
    ],
    output: Annotated[
        Path | None,
        typer.Option(
            "--output", help="Файл отчета json (по умолчанию запись в stdout)"
        ),
    ] = None,
    skip_invalid: Annotated[
        bool,
        typer.Option("--skip-invalid", help="Пропускать ошибочные строки"),
    ] = False,
) -> None:
    """
    Проанализировать файлы событий и сформировать отчет
    Args:
        inputs: входные файлы
        fmt: формат ввода
        output: место вывода
        skip_invalid: флаг пропуска ошибочных строк
    Raises: падает с общей ошибкой, а выдает конкретное сообщение ошибки
    Returns: None
    """
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
    try:
        stats = analyze_files(inputs, fmt, skip_invalid=skip_invalid)
        _emit(build_report(stats), output)
    except StreamStatsError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(EXIT_ERROR) from exc


if __name__ == "__main__":
    app()

import pytest

from streamstats.errors import (
    CLIConfigError,
    EmptyFileError,
    InvalidEventError,
    InvalidTimestampError,
    StreamStatsError,
    UnsupportedFormatError,
)

ALL_ERRORS = [
    UnsupportedFormatError,
    InvalidEventError,
    InvalidTimestampError,
    CLIConfigError,
    EmptyFileError,
]


def test_base_error() -> None:
    assert issubclass(StreamStatsError, Exception)


@pytest.mark.parametrize("error_class", ALL_ERRORS)
def test_every_error_inherits_from_base(error_class: type[Exception]) -> None:
    assert issubclass(error_class, StreamStatsError)


@pytest.mark.parametrize("error_class", ALL_ERRORS)
def test_cli_boundary_catches_every_error(error_class: type[Exception]) -> None:
    with pytest.raises(StreamStatsError) as exc_info:
        raise error_class("file.jsonl:3 message")

    assert str(exc_info.value) == "file.jsonl:3 message"


def test_invalid_timestamp_is_invalid_event() -> None:
    assert issubclass(InvalidTimestampError, InvalidEventError)


def test_invalid_timestamp_is_caught_as_invalid_event() -> None:
    with pytest.raises(InvalidEventError):
        raise InvalidTimestampError("invalid timestamp")


def test_invalid_error_is_not_invalid_timestamp() -> None:
    assert not issubclass(InvalidEventError, InvalidTimestampError)


@pytest.mark.parametrize(
    "error_class", [UnsupportedFormatError, CLIConfigError, EmptyFileError]
)
def test_file_level_errors_are_not_invalid_event(error_class: type[Exception]) -> None:
    assert not issubclass(error_class, InvalidEventError)

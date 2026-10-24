import pytest

from streamstats.errors import (
    CLIConfigError,
    EmptyFileError,
    InvalidEventError,
    InvalidTimestampError,
    StreamStatsError,
    UnsupportedFormatError,
)

@pytest.mark.parametrize(
    "error_class",
    [
        UnsupportedFormatError,
        InvalidEventError,
        InvalidTimestampError,
        CLIConfigError,
        EmptyFileError,
    ]
)
def test_every_error_inherits_from_base(error_class: type[Exception]) -> None:
    assert issubclass(error_class, StreamStatsError)


def test_invalid_timestamp_is_invalid_event() -> None:
    assert issubclass(InvalidTimestampError, InvalidEventError)


def test_empty_file_is_not_invalid_event() -> None:
    assert not issubclass(EmptyFileError, InvalidEventError)

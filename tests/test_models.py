from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from streamstats.models import Event

VALID = {
    "timestamp": "2026-09-01T12:00:00+00:00",
    "level": "ERROR",
    "source": "api",
    "message": "boom",
}
REQUIRED_FIELDS = list(VALID)


def make_event(**overrides: object) -> Event:
    return Event.model_validate({**VALID, **overrides})


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("2026-09-01T12:00:00+03:00", datetime(2026, 9, 1, 9, 0, 0, tzinfo=UTC)),
        ("2026-09-01T12:00Z", datetime(2026, 9, 1, 12, 0, 0, tzinfo=UTC)),
        ("2026-09-01T12:00", datetime(2026, 9, 1, 12, 0, 0, tzinfo=UTC)),
    ],
)
def test_timestamp_is_normalized_to_utc(raw: str, expected: datetime) -> None:
    timestamp = make_event(timestamp=raw).timestamp

    assert timestamp == expected
    assert timestamp.utcoffset() == timedelta(0)


@pytest.mark.parametrize("raw", ["вчера", "2026-09-01T00:00:00", 1714564800])
def test_invalid_timestamp_is_rejected(raw: object) -> None:
    with pytest.raises(ValidationError):
        make_event(timestamp=raw)


@pytest.mark.parametrize("level", ["error", "FATAL"])
def test_level_must_match_exactly(level: str) -> None:
    with pytest.raises(ValidationError):
        make_event(level=level)


def test_source_is_stripped() -> None:
    assert make_event(source="  api  ").source == "api"


@pytest.mark.parametrize("source", ["", "   "])
def test_blank_source_is_rejected(source: str) -> None:
    with pytest.raises(ValidationError):
        make_event(source=source)

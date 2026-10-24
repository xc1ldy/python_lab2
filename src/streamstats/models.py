import re
from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator


class Level(StrEnum):
    """Допустимые уровни важности события"""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Event(BaseModel):
    """Одно событие"""

    model_config = ConfigDict(frozen=True)

    timestamp: datetime
    level: Level
    source: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    message: str

    @field_validator("timestamp", mode="before")
    @classmethod
    def _normalize_timestamp(cls, value: object) -> datetime:
        if not isinstance(value, str):
            raise ValueError("Timestamp must be an ISO 8601 string")
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", value):
            return datetime.fromisoformat(value).replace(tzinfo=UTC)
        has_timezone = value.endswith("Z") or bool(
            re.search(r"[+-]\d{2}:\d{2}$", value)
        )
        if not has_timezone:
            raise ValueError("Timestamp must include a timezone")

        normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
        return datetime.fromisoformat(normalized).astimezone(UTC)

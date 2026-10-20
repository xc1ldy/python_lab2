from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator


class Level(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Event(BaseModel):
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
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)
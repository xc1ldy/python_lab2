class StreamStatsError(Exception):
    """Main error"""


class UnsupportedFormatError(StreamStatsError):
    """Invalid format"""


class InvalidEventError(StreamStatsError):
    """Invalid event"""


class InvalidTimestampError(StreamStatsError):
    """Invalid time format"""


class CLIConfigError(StreamStatsError):
    """CLI config error"""
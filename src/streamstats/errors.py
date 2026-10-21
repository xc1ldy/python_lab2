class StreamStatsError(Exception):
    """Основная ошибка"""


class EmptyFileError(StreamStatsError):
    """Ошибка пустого файла"""


class UnsupportedFormatError(StreamStatsError):
    """Неподдерживаемый формат"""


class InvalidEventError(StreamStatsError):
    """Недопустимое событие"""


class InvalidTimestampError(InvalidEventError):
    """Недопустимый формат времени"""


class CLIConfigError(StreamStatsError):
    """Ошибка конфига CLI"""

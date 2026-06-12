from __future__ import annotations


class HeddleError(Exception):
    code = "HEDDLE_ERROR"


class BadRevisionError(HeddleError):
    code = "BAD_REVISION"


class NotIngestedError(HeddleError):
    code = "NOT_INGESTED"


class UnknownEntityError(HeddleError):
    code = "UNKNOWN_ENTITY"


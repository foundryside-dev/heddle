from __future__ import annotations

from typing import Any


class HeddleError(Exception):
    code = "heddle_error"
    rejected_field: str | None = None
    retryability = "fatal"
    hint = "Inspect the request and retry after correcting the rejected input."

    def to_error_data(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "schema": "heddle.error.v1",
            "error_code": self.code,
            "retryability": self.retryability,
            "hint": self.hint,
        }
        if self.rejected_field is not None:
            data["rejected_field"] = self.rejected_field
        return data


class BadRevisionError(HeddleError):
    code = "invalid_rev_range"
    rejected_field = "rev_range"
    retryability = "retry_with_changes"
    hint = "Provide a git revision range that resolves in this repository."


class NotIngestedError(HeddleError):
    code = "repo_not_ingested"
    retryability = "retry_after_dependency"
    hint = "Run heddle backfill for the repository before requesting this view."


class UnknownEntityError(HeddleError):
    code = "unknown_entity"
    rejected_field = "entity_key_id"
    retryability = "retry_with_changes"
    hint = "Use an entity_key_id returned by changed, timeline, or blast_radius."

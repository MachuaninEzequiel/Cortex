"""Base pydantic models for canonical frontmatter."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from cortex.documentation.doc_type import VALID_STATUSES, DocType

# Allowed values.
_VAULT_SCOPES = frozenset({"local", "enterprise"})
_CLASSIFICATIONS = frozenset({"public", "internal", "confidential"})

# Fingerprint must be 64-char lowercase hex (SHA-256).
_FINGERPRINT_PATTERN = r"^[a-f0-9]{64}$"

# Email regex - pragmatic, not RFC-perfect.
_EMAIL_PATTERN = r"^[\w.+-]+@[\w-]+\.[\w.-]+$"

# Team slug: lowercase alphanumeric + dashes.
_TEAM_PATTERN = r"^[a-z0-9-]+$"


class CommonFrontmatter(BaseModel):
    """Canonical frontmatter shared by all DocTypes.

    Subclasses override ``doc_type`` with a fixed value and add
    type-specific fields.
    """

    model_config = ConfigDict(frozen=True, validate_assignment=True, extra="allow")

    schema_version: int = 1
    doc_type: DocType
    title: str = Field(min_length=1)
    created_at: datetime
    updated_at: datetime
    tags: list[str] = Field(default_factory=list)
    status: str
    links: list[str] = Field(default_factory=list)
    vault_scope: str = "local"
    fingerprint: str = Field(min_length=64, max_length=64, pattern=_FINGERPRINT_PATTERN)

    @field_validator("created_at", "updated_at")
    @classmethod
    def _validate_tz_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("datetime must be timezone-aware")
        return v

    @field_validator("vault_scope")
    @classmethod
    def _validate_vault_scope(cls, v: str) -> str:
        if v not in _VAULT_SCOPES:
            raise ValueError(
                f"vault_scope must be one of {sorted(_VAULT_SCOPES)}, got {v!r}"
            )
        return v

    @model_validator(mode="after")
    def _validate_dates_order(self) -> CommonFrontmatter:
        if self.updated_at < self.created_at:
            raise ValueError("updated_at must be >= created_at")
        return self

    @model_validator(mode="after")
    def _validate_status_for_doc_type(self) -> CommonFrontmatter:
        valid = VALID_STATUSES.get(self.doc_type)
        if valid is not None and self.status not in valid:
            raise ValueError(
                f"status {self.status!r} invalid for doc_type "
                f"{self.doc_type.value!r}. Valid: {sorted(valid)}"
            )
        return self


class AuditEvent(BaseModel):
    """A single entry in the audit_trail (enterprise only)."""

    model_config = ConfigDict(frozen=True)

    actor: str = Field(min_length=1)
    action: str = Field(min_length=1)
    timestamp: datetime
    reason: str | None = None

    @field_validator("timestamp")
    @classmethod
    def _validate_tz_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        return v


class EnterpriseFrontmatter(CommonFrontmatter):
    """Frontmatter required when ``vault_scope='enterprise'``.

    Adds 5 governance fields plus the audit trail.
    """

    owner: str = Field(pattern=_EMAIL_PATTERN)
    team: str = Field(pattern=_TEAM_PATTERN)
    classification: str = "internal"
    retention_days: int = Field(default=0, ge=0)
    audit_trail: list[AuditEvent] = Field(default_factory=list)

    @field_validator("classification")
    @classmethod
    def _validate_classification(cls, v: str) -> str:
        if v not in _CLASSIFICATIONS:
            raise ValueError(
                f"classification must be one of {sorted(_CLASSIFICATIONS)}, got {v!r}"
            )
        return v

    @model_validator(mode="after")
    def _validate_enterprise_scope(self) -> EnterpriseFrontmatter:
        if self.vault_scope != "enterprise":
            raise ValueError(
                "EnterpriseFrontmatter requires vault_scope='enterprise', "
                f"got {self.vault_scope!r}"
            )
        return self


__all__ = [
    "AuditEvent",
    "CommonFrontmatter",
    "EnterpriseFrontmatter",
]


# Re-export raw constants for downstream imports.
def _get_classifications() -> frozenset[str]:
    return _CLASSIFICATIONS


def _get_vault_scopes() -> frozenset[str]:
    return _VAULT_SCOPES

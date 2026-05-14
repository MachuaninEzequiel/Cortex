"""cortex.documentation.validation - Public validator for frontmatter.

Parses YAML frontmatter and validates it against the correct pydantic schema
based on ``doc_type`` and ``vault_scope``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from cortex.documentation.common import (
    parse_frontmatter_lenient,
    split_frontmatter_and_body,
    yaml_load_safe,
)
from cortex.documentation.doc_type import DocType
from cortex.documentation.errors import SchemaValidationError, UnknownDocTypeError
from cortex.documentation.schemas import (
    SCHEMA_BY_TYPE,
    SCHEMA_BY_TYPE_ENTERPRISE,
    CommonFrontmatter,
)


def validate_frontmatter(yaml_str: str) -> CommonFrontmatter:
    """Parse a YAML frontmatter string and validate against the canonical schema.

    Routes to the appropriate subclass of ``CommonFrontmatter`` (or
    ``EnterpriseFrontmatter``) based on ``doc_type`` and ``vault_scope``.

    Args:
        yaml_str: YAML text *without* the surrounding ``---`` delimiters.

    Returns:
        Validated frontmatter instance (subclass of ``CommonFrontmatter``).

    Raises:
        SchemaValidationError: if YAML is malformed, doc_type is missing,
            or any field fails validation.
        UnknownDocTypeError: if ``doc_type`` is not in the DocType enum.
    """
    try:
        raw = yaml_load_safe(yaml_str)
    except (yaml.YAMLError, ValueError) as e:
        raise SchemaValidationError(f"Invalid YAML: {e}") from e

    if not isinstance(raw, dict) or "doc_type" not in raw:
        raise SchemaValidationError("doc_type field is required in frontmatter")

    raw_doc_type = raw["doc_type"]
    if not isinstance(raw_doc_type, str):
        raise SchemaValidationError(
            f"doc_type must be a string, got {type(raw_doc_type).__name__}"
        )
    try:
        doc_type = DocType(raw_doc_type)
    except ValueError as e:
        raise UnknownDocTypeError(f"Unknown doc_type: {raw_doc_type!r}") from e

    scope = raw.get("vault_scope", "local")
    if scope == "enterprise":
        schema_cls: type[CommonFrontmatter] = SCHEMA_BY_TYPE_ENTERPRISE[doc_type]
    elif scope == "local":
        schema_cls = SCHEMA_BY_TYPE[doc_type]
    else:
        raise SchemaValidationError(
            f"vault_scope must be 'local' or 'enterprise', got {scope!r}"
        )

    try:
        return schema_cls.model_validate(raw)
    except ValidationError as e:
        raise SchemaValidationError(
            f"Frontmatter validation failed for {doc_type.value}: {e}"
        ) from e


def validate_path_frontmatter(path: Path) -> CommonFrontmatter:
    """Read a markdown file, extract its frontmatter, and validate.

    Convenience wrapper around ``validate_frontmatter``.

    Raises:
        SchemaValidationError: if file has no frontmatter or schema fails.
    """
    if not path.exists():
        raise SchemaValidationError(f"File not found: {path}")
    content = path.read_text(encoding="utf-8")
    fm_yaml, _ = split_frontmatter_and_body(content)
    if not fm_yaml:
        raise SchemaValidationError(f"No frontmatter in {path}")
    return validate_frontmatter(fm_yaml)

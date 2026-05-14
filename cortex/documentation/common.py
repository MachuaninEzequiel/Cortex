"""cortex.documentation.common - Shared helpers used across documentation layers.

All functions here are pure: no I/O, no global state mutation (except for
file reads in ``parse_frontmatter_lenient``).
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from pathlib import Path
from typing import Any

import yaml

# Slug regexes (compiled once, reused).
_SLUG_STRIP = re.compile(r"[^\w\s-]", flags=re.UNICODE)
_SLUG_SEP = re.compile(r"[\s_]+", flags=re.UNICODE)
_SLUG_COLLAPSE = re.compile(r"-+")

# Frontmatter delimiter: a line of exactly three dashes.
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


def slugify(value: str) -> str:
    """Convert a string to a filesystem-safe slug.

    - Normalize unicode to ASCII (strip accents).
    - Lowercase.
    - Strip non-alphanumeric except dash and space.
    - Replace spaces/underscores with dash.
    - Collapse repeated dashes.

    Examples:
        >>> slugify("Hello World")
        'hello-world'
        >>> slugify("Cafe & Sueño")
        'cafe-sueno'
        >>> slugify("")
        ''
    """
    if not value:
        return ""
    # Normalize unicode to ASCII (drop accents).
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    # Lowercase and strip special chars.
    cleaned = _SLUG_STRIP.sub("", ascii_value.strip().lower())
    # Replace whitespace/underscores with dash.
    slug = _SLUG_SEP.sub("-", cleaned)
    # Collapse repeated dashes and trim edges.
    slug = _SLUG_COLLAPSE.sub("-", slug).strip("-")
    return slug


def compute_fingerprint(content: str) -> str:
    """Compute SHA-256 hex digest of content. Returns 64-char lowercase hex.

    Determinism: same input -> same output, byte-for-byte.
    """
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def yaml_dump_safe(data: dict[str, Any]) -> str:
    """Dump dict to YAML with safe defaults.

    - default_flow_style=False (block style).
    - allow_unicode=True.
    - sort_keys=False (preserve insertion order).
    """
    return yaml.safe_dump(
        data,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )


def yaml_load_safe(text: str) -> dict[str, Any]:
    """Parse YAML safely. Returns empty dict for empty or whitespace-only input."""
    if not text or not text.strip():
        return {}
    result = yaml.safe_load(text)
    if result is None:
        return {}
    if not isinstance(result, dict):
        raise ValueError(f"Expected YAML mapping, got {type(result).__name__}")
    return result


def split_frontmatter_and_body(content: str) -> tuple[str, str]:
    """Split markdown content into ``(frontmatter_yaml, body)``.

    If the content does not start with a YAML frontmatter block, returns
    ``("", content)`` unchanged.

    The frontmatter delimiter is a line containing exactly three dashes.
    """
    if not content.startswith("---"):
        return "", content
    match = _FRONTMATTER_RE.match(content)
    if match is None:
        return "", content
    fm_yaml = match.group(1)
    body = content[match.end() :]
    return fm_yaml, body


def has_frontmatter(content: str) -> bool:
    """Return True if content starts with a valid frontmatter block."""
    if not content.startswith("---"):
        return False
    return _FRONTMATTER_RE.match(content) is not None


def parse_frontmatter_lenient(path: Path) -> dict[str, Any]:
    """Parse a markdown file's frontmatter without strict schema validation.

    Returns the raw dict. Used by migration tooling to read legacy notes.

    - If the file does not exist, returns ``{}``.
    - If the file has no frontmatter, returns ``{}``.
    - If the YAML is malformed, returns ``{}`` (does not raise).
    """
    if not path.exists():
        return {}
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    fm_yaml, _ = split_frontmatter_and_body(content)
    if not fm_yaml:
        return {}
    try:
        return yaml_load_safe(fm_yaml)
    except (yaml.YAMLError, ValueError):
        return {}

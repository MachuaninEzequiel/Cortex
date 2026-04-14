"""
cortex.semantic.markdown_parser
--------------------------------
Parses individual markdown files into SemanticDocument objects.

Extracts:
- YAML front-matter (title, tags)
- Obsidian-style wiki-links: [[note]]
- Inline #hashtags
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from cortex.models import SemanticDocument

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_WIKI_LINK_RE = re.compile(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]")
_HASHTAG_RE = re.compile(r"(?<!\w)#([A-Za-z][A-Za-z0-9_-]*)")


class MarkdownParser:
    """Parses a single markdown file into a SemanticDocument."""

    def parse(self, path: Path) -> SemanticDocument:
        """
        Parse a markdown file.

        Args:
            path: Absolute path to the ``.md`` file.

        Returns:
            Populated SemanticDocument.
        """
        raw = path.read_text(encoding="utf-8")
        frontmatter, body = self._split_frontmatter(raw)

        title = frontmatter.get("title") or path.stem.replace("_", " ").title()
        fm_tags: list[str] = frontmatter.get("tags") or []
        if isinstance(fm_tags, str):
            fm_tags = [fm_tags]

        inline_tags = _HASHTAG_RE.findall(body)
        tags = list(dict.fromkeys(fm_tags + inline_tags))  # dedup, preserve order

        wiki_links = _WIKI_LINK_RE.findall(body)
        clean_body = self._strip_frontmatter_block(raw)

        return SemanticDocument(
            path=str(path),
            title=title,
            content=clean_body,
            links=wiki_links,
            tags=tags,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _split_frontmatter(raw: str) -> tuple[dict, str]:
        match = _FRONTMATTER_RE.match(raw)
        if not match:
            return {}, raw
        try:
            data = yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError:
            data = {}
        body = raw[match.end():]
        return data, body

    @staticmethod
    def _strip_frontmatter_block(raw: str) -> str:
        return _FRONTMATTER_RE.sub("", raw).strip()

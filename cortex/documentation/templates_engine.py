"""cortex.documentation.templates_engine - Jinja2 renderer for canonical templates.

Templates live in ``cortex/documentation/templates/*.md.j2``. They render the
*body* of a markdown note; the frontmatter is built and prepended by the writer.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, TemplateError, select_autoescape

from cortex.documentation.errors import TemplateRenderError

TEMPLATES_DIR = Path(__file__).parent / "templates"


def _build_environment() -> Environment:
    """Construct the Jinja2 environment used to render canonical templates."""
    return Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(disabled_extensions=("md.j2",)),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )


_env = _build_environment()


def render_template(template_name: str, data: dict[str, Any]) -> str:
    """Render the named Jinja2 template with ``data`` as the context dict.

    Args:
        template_name: ej. ``"adr.md.j2"``.
        data: variables available to the template.

    Returns:
        Rendered markdown body (no frontmatter).

    Raises:
        TemplateRenderError: if the template is not found or rendering fails.
    """
    try:
        template = _env.get_template(template_name)
        return template.render(**data)
    except TemplateError as exc:
        raise TemplateRenderError(
            f"Failed to render {template_name}: {exc}"
        ) from exc

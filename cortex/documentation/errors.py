"""cortex.documentation.errors - Exception hierarchy for the documentation module."""

from __future__ import annotations


class DocumentationError(Exception):
    """Base error for cortex.documentation."""


class SchemaValidationError(DocumentationError):
    """Frontmatter does not validate against schema."""


class UnknownDocTypeError(DocumentationError):
    """doc_type value is not a member of the DocType enum."""


class RoutingError(DocumentationError):
    """RouteSpec resolution or path rendering failed."""


class DuplicateDocumentError(DocumentationError):
    """Document already exists at target path and overwrite=False."""


class TemplateRenderError(DocumentationError):
    """Jinja2 template render failed."""

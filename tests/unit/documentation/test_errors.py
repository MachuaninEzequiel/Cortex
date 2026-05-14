"""Tests for cortex.documentation.errors."""

from __future__ import annotations

import pytest

from cortex.documentation.errors import (
    DocumentationError,
    DuplicateDocumentError,
    RoutingError,
    SchemaValidationError,
    TemplateRenderError,
    UnknownDocTypeError,
)


def test_errors_inherit_from_documentation_error() -> None:
    assert issubclass(SchemaValidationError, DocumentationError)
    assert issubclass(UnknownDocTypeError, DocumentationError)
    assert issubclass(RoutingError, DocumentationError)
    assert issubclass(DuplicateDocumentError, DocumentationError)
    assert issubclass(TemplateRenderError, DocumentationError)


def test_errors_can_be_raised_and_caught() -> None:
    with pytest.raises(SchemaValidationError, match="bad fm"):
        raise SchemaValidationError("bad fm")
    with pytest.raises(UnknownDocTypeError):
        raise UnknownDocTypeError("nope")
    with pytest.raises(DocumentationError):
        raise RoutingError("missing placeholder")

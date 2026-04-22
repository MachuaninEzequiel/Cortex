"""
tests.test_doc_validator
------------------------
Tests for the document validation system.
"""

from __future__ import annotations

from pathlib import Path

from cortex.doc_validator import DocValidationIssue, DocValidationResult, DocValidator

# ------------------------------------------------------------------
# DocValidationResult tests
# ------------------------------------------------------------------

class TestDocValidationResult:
    def test_default_valid(self) -> None:
        result = DocValidationResult()
        assert result.is_valid is True

    def test_errors_filter(self) -> None:
        result = DocValidationResult(
            issues=[
                DocValidationIssue(file="a.md", field="x", message="err", severity="error"),
                DocValidationIssue(file="a.md", field="y", message="warn", severity="warning"),
            ]
        )
        assert len(result.errors) == 1
        assert len(result.warnings) == 1

    def test_to_dict(self) -> None:
        result = DocValidationResult(
            is_valid=False,
            issues=[DocValidationIssue(file="a.md", field="title", message="missing", severity="warning")],
            properties={"title": "Test"},
        )
        d = result.to_dict()
        assert d["is_valid"] is False
        assert d["error_count"] == 0
        assert d["warning_count"] == 1
        assert d["properties"]["title"] == "Test"


# ------------------------------------------------------------------
# DocValidator tests
# ------------------------------------------------------------------

class TestDocValidator:
    def test_valid_file(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        doc = vault / "test.md"
        doc.write_text(
            "---\ntitle: Test Note\ndate: 2026-04-13\ntags: [test]\n---\n# Test Note\n\nThis is a test."
        )

        validator = DocValidator(vault_path=vault)
        result = validator.validate_file(doc)

        assert result.is_valid is True
        assert len(result.errors) == 0
        assert "Test Note" in result.properties.get("title", "")

    def test_missing_frontmatter(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        doc = vault / "nofm.md"
        doc.write_text("# No Frontmatter\n\nThis has no frontmatter.")

        validator = DocValidator(vault_path=vault)
        result = validator.validate_file(doc)

        assert result.is_valid is True  # warnings don't invalidate
        assert len(result.warnings) > 0

    def test_invalid_yaml(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        doc = vault / "bad.md"
        doc.write_text("---\ntitle: [invalid\n---\n# Bad")

        validator = DocValidator(vault_path=vault)
        result = validator.validate_file(doc)

        assert result.is_valid is False
        assert len(result.errors) > 0

    def test_extract_wikilinks(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        doc = vault / "links.md"
        doc.write_text(
            "---\ntitle: Links\ndate: 2026-04-13\n---\n"
            "See [[Architecture]] and [[ADR-001|Decision]].\n"
            "![[image.png]]\n"
        )

        validator = DocValidator(vault_path=vault)
        result = validator.validate_file(doc)

        assert "Architecture" in result.wikilinks
        assert "ADR-001" in result.wikilinks
        assert "image.png" in result.embeds

    def test_file_not_found(self, tmp_path: Path) -> None:
        validator = DocValidator(vault_path=tmp_path)
        result = validator.validate_file(tmp_path / "nonexistent.md")

        assert result.is_valid is False
        assert len(result.errors) > 0

    def test_not_markdown(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        doc = vault / "image.png"
        doc.write_text("binary")

        validator = DocValidator(vault_path=vault)
        result = validator.validate_file(doc)

        assert len(result.warnings) > 0

    def test_validate_batch(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / "a.md").write_text("---\ntitle: A\ndate: 2026-04-13\n---\n# A")
        (vault / "b.md").write_text("---\ntitle: B\ndate: 2026-04-13\n---\n# B")

        validator = DocValidator(vault_path=vault)
        results = validator.validate_batch([vault / "a.md", vault / "b.md"])

        assert len(results) == 2
        assert all(r.is_valid for r in results)

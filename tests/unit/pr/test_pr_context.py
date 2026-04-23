"""Tests for PR context capture and documentation generation."""
from __future__ import annotations

# ---------------------------------------------------------------------------
# PRContext model tests
# ---------------------------------------------------------------------------

class TestPRContext:
    """Tests for the PRContext Pydantic model."""

    def test_basic_creation(self):
        from cortex.models import PRContext

        ctx = PRContext(
            title="Fix login bug",
            author="dev1",
            source_branch="fix/login",
            commit_sha="abc123",
        )

        assert ctx.title == "Fix login bug"
        assert ctx.author == "dev1"
        assert ctx.source_branch == "fix/login"
        assert ctx.target_branch == "main"  # default
        assert ctx.files_changed == []
        assert ctx.labels == []

    def test_hu_references_from_body(self):
        from cortex.models import PRContext

        ctx = PRContext(
            title="Implement HU-42",
            body="This PR addresses HU-42 and also references HU-100. Also related to #200.",
            author="dev1",
            source_branch="feature/hu-42",
            commit_sha="abc123",
        )

        refs = ctx.hu_references()
        assert "HU-42" in refs
        assert "HU-100" in refs
        assert "HU-200" in refs

    def test_has_db_changes(self):
        from cortex.models import PRContext

        ctx = PRContext(
            title="Add migration",
            author="dev1",
            source_branch="feature/db",
            commit_sha="abc123",
            files_changed=["migrations/001_add_users.sql", "src/app.js"],
        )

        assert ctx.has_db_changes()

        ctx2 = PRContext(
            title="Fix typo",
            author="dev1",
            source_branch="fix/typo",
            commit_sha="abc123",
            files_changed=["README.md"],
        )
        assert not ctx2.has_db_changes()

    def test_has_api_changes(self):
        from cortex.models import PRContext

        ctx = PRContext(
            title="Add endpoint",
            author="dev1",
            source_branch="feature/api",
            commit_sha="abc123",
            files_changed=["src/routes/users.js", "src/controllers/users.js"],
        )

        assert ctx.has_api_changes()

        ctx2 = PRContext(
            title="Fix CSS",
            author="dev1",
            source_branch="fix/css",
            commit_sha="abc123",
            files_changed=["src/styles/main.css"],
        )
        assert not ctx2.has_api_changes()

    def test_has_adr_label(self):
        from cortex.models import PRContext

        ctx = PRContext(
            title="Architecture change",
            author="dev1",
            source_branch="feature/arch",
            commit_sha="abc123",
            labels=["adr", "breaking"],
        )
        assert ctx.has_adr_label()

        ctx2 = PRContext(
            title="Small fix",
            author="dev1",
            source_branch="fix/small",
            commit_sha="abc123",
            labels=["bugfix"],
        )
        assert not ctx2.has_adr_label()


# ---------------------------------------------------------------------------
# PR Capture module tests
# ---------------------------------------------------------------------------

class TestPRCapture:
    """Tests for pr_capture module."""

    def test_capture_manual_basic(self):
        from cortex.pr_capture import capture_manual

        ctx = capture_manual(
            title="Fix login bug",
            author="dev1",
            branch="fix/login",
            commit="abc123",
            body="Fixed the refresh token issue",
        )

        assert ctx.title == "Fix login bug"
        assert ctx.author == "dev1"
        assert ctx.source_branch == "fix/login"
        assert ctx.body == "Fixed the refresh token issue"

    def test_capture_manual_with_labels(self):
        from cortex.pr_capture import capture_manual

        ctx = capture_manual(
            title="ADR: New DB schema",
            author="dev1",
            branch="feature/db",
            commit="abc123",
            labels=["adr", "database"],
        )

        assert "adr" in ctx.labels
        assert "database" in ctx.labels

    def test_save_and_load_context(self, tmp_path):
        from cortex.pr_capture import capture_from_json, capture_manual, save_context

        ctx = capture_manual(
            title="Test PR",
            author="dev1",
            branch="test",
            commit="abc123",
            labels=["test"],
        )

        path = save_context(ctx, tmp_path / "context.json")
        assert path.exists()

        loaded = capture_from_json(path)
        assert loaded.title == ctx.title
        assert loaded.author == ctx.author
        assert loaded.labels == ctx.labels

    def test_enrich_with_pipeline(self):
        from cortex.pr_capture import capture_manual, enrich_with_pipeline

        ctx = capture_manual(
            title="Test PR",
            author="dev1",
            branch="test",
            commit="abc123",
        )

        enriched = enrich_with_pipeline(
            ctx,
            lint_result="pass",
            audit_result="fail: 2 high vulnerabilities",
            test_result="pass",
        )

        assert enriched.lint_result == "pass"
        assert "fail" in enriched.audit_result
        assert enriched.test_result == "pass"
        # Original unchanged
        assert ctx.lint_result is None

    def test_detect_db_migrations(self):
        from cortex.pr_capture import _detect_db_migrations

        files = ["migrations/001.sql", "src/app.js", "schema.sql"]
        migrations = _detect_db_migrations(files)
        assert "migrations/001.sql" in migrations
        assert "schema.sql" in migrations
        assert "src/app.js" not in migrations

    def test_detect_api_changes(self):
        from cortex.pr_capture import _detect_api_changes

        files = ["src/routes/users.js", "src/controllers/auth.js", "README.md"]
        api = _detect_api_changes(files)
        assert "src/routes/users.js" in api
        assert "src/controllers/auth.js" in api
        assert "README.md" not in api


# ---------------------------------------------------------------------------
# DocGenerator tests
# ---------------------------------------------------------------------------

class TestDocGenerator:
    """Tests for doc_generator module."""

    def _make_ctx(self, **kwargs):
        from cortex.models import PRContext
        defaults = dict(
            title="Fix login bug",
            body="Fixed the refresh token issue",
            author="dev1",
            source_branch="fix/login",
            commit_sha="abc123def456",
            pr_number=42,
        )
        defaults.update(kwargs)
        return PRContext(**defaults)

    def test_generate_session(self, tmp_path):
        from cortex.doc_generator import DocGenerator

        ctx = self._make_ctx()
        gen = DocGenerator(vault_path=tmp_path)
        doc = gen.generate_session(ctx)

        assert doc.doc_type == "session"
        assert doc.vault_subfolder == "sessions"
        assert "Fix login bug" in doc.content
        assert "dev1" in doc.content
        assert ctx.commit_sha[:8] in doc.content

    def test_generate_session_with_pipeline_results(self, tmp_path):
        from cortex.doc_generator import DocGenerator

        ctx = self._make_ctx(
            lint_result="pass",
            audit_result="pass",
            test_result="pass",
        )
        gen = DocGenerator(vault_path=tmp_path)
        doc = gen.generate_session(ctx)

        assert "pass" in doc.content
        assert "Lint (SAST)" in doc.content
        assert "Audit (SCA)" in doc.content

    # ── Fallback mode tests (DocGenerator now only generates session notes) ──

    def test_fallback_generates_session_only(self, tmp_path):
        from cortex.doc_generator import DocGenerator

        ctx = self._make_ctx(
            title="Fallback test",
            body="Testing fallback mode.",
        )
        gen = DocGenerator(vault_path=tmp_path)
        docs = gen.generate_all(ctx)

        # In fallback mode, only session notes are generated
        assert len(docs) == 1
        assert docs[0].doc_type == "session"
        assert docs[0].vault_subfolder == "sessions"

    def test_fallback_session_has_warning(self, tmp_path):
        from cortex.doc_generator import DocGenerator

        ctx = self._make_ctx(
            title="Fallback warning test",
        )
        gen = DocGenerator(vault_path=tmp_path)
        doc = gen.generate_session(ctx)

        assert "fallback" in doc.content.lower()
        assert "[!warning]" in doc.content

    def test_write_docs_creates_files(self, tmp_path):
        from cortex.doc_generator import DocGenerator

        ctx = self._make_ctx(
            lint_result="pass",
            audit_result="pass",
            test_result="pass",
        )
        gen = DocGenerator(vault_path=tmp_path)
        docs = gen.generate_all(ctx)
        written = gen.write_docs(docs)

        for p in written:
            assert p.exists()
            assert p.read_text().strip()

    def test_generate_all_produces_session_at_minimum(self, tmp_path):
        from cortex.doc_generator import DocGenerator

        ctx = self._make_ctx()
        gen = DocGenerator(vault_path=tmp_path)
        docs = gen.generate_all(ctx)

        # At least a session note is always generated
        assert len(docs) >= 1
        assert any(d.doc_type == "session" for d in docs)

    def test_safe_filename(self, tmp_path):
        from cortex.doc_generator import DocGenerator

        gen = DocGenerator(vault_path=tmp_path)
        name = gen._safe_filename("Fix login bug! @#$%")
        assert name.endswith(".md")
        assert "fix-login-bug" in name
        assert "!" not in name
        assert "@" not in name

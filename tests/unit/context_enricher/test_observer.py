"""Tests for ContextObserver."""

from unittest.mock import MagicMock

import pytest

from cortex.context_enricher.observer import ContextObserver
from cortex.models import WorkContext


@pytest.fixture
def observer():
    return ContextObserver()


class TestObserverFromFiles:
    """Observer: manual file input."""

    def test_observe_from_files_basic(self, observer):
        work = observer.observe_from_files(
            files=["auth.py", "jwt.ts"],
            keywords=["token", "refresh"],
        )
        assert isinstance(work, WorkContext)
        assert work.source == "manual"
        assert "auth.py" in work.changed_files
        assert "token" in work.keywords

    def test_observe_from_files_with_pr_metadata(self, observer):
        work = observer.observe_from_files(
            files=["auth.py"],
            pr_title="Fix token expiry",
            pr_labels=["bugfix", "auth"],
        )
        assert work.pr_title == "Fix token expiry"
        assert "bugfix" in work.pr_labels

    def test_observe_from_files_generates_queries(self, observer):
        work = observer.observe_from_files(
            files=["auth.py", "jwt.ts"],
            keywords=["token", "refresh", "expiry"],
            pr_title="Fix token refresh bug",
        )
        assert len(work.search_queries) >= 3  # topic, files, keywords, pr_title


class TestObserverDomainDetection:
    """Observer: domain detection."""

    def test_detects_auth_domain(self, observer):
        work = observer.observe_from_files(
            files=["auth.py", "jwt.ts"],
            keywords=["token", "refresh", "authentication"],
        )
        assert work.detected_domain == "auth"
        assert work.domain_confidence > 0.5

    def test_no_domain_for_generic_files(self, observer):
        work = observer.observe_from_files(
            files=["utils.py", "helpers.js"],
            keywords=["stuff", "things"],
        )
        # May or may not have a domain, but confidence should be low
        assert work.domain_confidence < 0.5 or work.detected_domain is None


class TestObserverFromPR:
    """Observer: PR metadata input."""

    def test_observe_from_pr_basic(self, observer):
        mock_pr = MagicMock()
        mock_pr.files_changed = ["auth.py", "jwt.ts"]
        mock_pr.title = "Fix token refresh"
        mock_pr.body = "The refresh token was expiring too early"
        mock_pr.labels = ["bugfix"]

        work = observer.observe_from_pr(mock_pr)
        assert work.source == "pr"
        assert "auth.py" in work.changed_files
        assert work.pr_title == "Fix token refresh"

    def test_observe_from_pr_extracts_keywords(self, observer):
        mock_pr = MagicMock()
        mock_pr.files_changed = []
        mock_pr.title = "Fix authentication token"
        mock_pr.body = "Implement refresh token rotation"
        mock_pr.labels = []

        work = observer.observe_from_pr(mock_pr)
        # Should extract keywords from title + body
        assert len(work.keywords) > 0


class TestObserverCodeExtraction:
    """Observer: code extraction patterns."""

    def test_extract_imports(self, observer):
        content = """
import jwt
from flask import request, jsonify
from cryptography.fernet import Fernet
"""
        imports = observer._extract_imports(content)
        assert "jwt" in imports
        assert "flask" in imports
        assert "cryptography" in imports

    def test_extract_functions(self, observer):
        content = """
def create_token(user_id):
    pass

async function handle_request(req, res):
    pass

const validate = async (input) => {
    pass
}
"""
        funcs = observer._extract_functions(content)
        assert "create_token" in funcs
        assert "handle_request" in funcs

    def test_extract_classes(self, observer):
        content = """
class TokenManager:
    pass

export class AuthProvider {
    constructor() {}
}
"""
        classes = observer._extract_classes(content)
        assert "TokenManager" in classes
        assert "AuthProvider" in classes

    def test_extract_keywords_from_code(self, observer):
        content = """
const token = createRefreshToken(user);
const expiry = calculateExpiry(token);
validateTokenExpiry(token, expiry);
"""
        keywords = observer._extract_keywords(content)
        # Should find meaningful identifiers
        assert len(keywords) > 0

    def test_extract_text_keywords(self, observer):
        text = "Fix the authentication token that was expiring too early"
        keywords = observer._extract_text_keywords(text)
        assert "authentication" in keywords
        assert "token" in keywords
        assert "expiring" in keywords

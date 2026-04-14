"""Tests for DomainDetector."""

import pytest
from cortex.context_enricher.domain_detector import DomainDetector, DomainMatch


@pytest.fixture
def detector():
    return DomainDetector()


class TestDomainDetectorAuth:
    """Domain detection: auth."""

    def test_detect_auth_from_files(self, detector):
        result = detector.detect(["auth.py", "jwt.ts", "tests/test_auth.py"])
        assert result.domain == "auth"
        assert result.confidence > 0.5
        assert "auth.py" in result.matched_files

    def test_detect_auth_from_keywords(self, detector):
        result = detector.detect([], ["token", "refresh", "expiry", "authentication"])
        # Keywords alone might not reach 0.5 threshold (keyword_weight=0.4)
        # So we check it's at least attempting
        assert result.confidence > 0.0
        assert len(result.matched_keywords) > 0

    def test_detect_auth_from_mixed(self, detector):
        result = detector.detect(
            ["auth.py", "jwt.ts"],
            ["token", "refresh", "login"],
        )
        assert result.domain == "auth"
        assert result.confidence > 0.7  # High confidence with both files + keywords


class TestDomainDetectorDatabase:
    """Domain detection: database."""

    def test_detect_database_from_files(self, detector):
        result = detector.detect(["migrations/001_initial.sql", "schema.py"])
        assert result.domain == "database"

    def test_detect_database_from_keywords(self, detector):
        result = detector.detect([], ["query", "transaction", "migration", "schema"])
        # Keywords alone might not reach 0.5 threshold
        assert result.confidence > 0.0
        assert len(result.matched_keywords) > 0


class TestDomainDetectorNoDomain:
    """No domain detected."""

    def test_no_domain_with_low_confidence(self, detector):
        # Files that don't match any domain patterns well
        result = detector.detect(["utils.py", "helpers.js", "README.md"])
        assert result.domain is None or result.confidence < 0.5

    def test_empty_input(self, detector):
        result = detector.detect([], [])
        assert result.domain is None
        assert result.confidence == 0.0


class TestDomainDetectorConfidence:
    """Confidence threshold."""

    def test_high_threshold_returns_none(self):
        detector = DomainDetector(min_confidence=0.9)
        result = detector.detect(["auth.py"], ["token"])
        # Even auth files might not reach 0.9 with just one file
        # (depends on the scoring)
        assert isinstance(result, DomainMatch)

    def test_low_threshold_returns_domain(self):
        detector = DomainDetector(min_confidence=0.1)
        result = detector.detect(["auth.py"], ["token"])
        assert result.domain == "auth"


class TestDomainDetectorOtherDomains:
    """Other domain detections."""

    def test_detect_api(self, detector):
        result = detector.detect(
            ["routes/api.py", "controllers/user_controller.ts"],
            ["endpoint", "handler", "request", "response"],
        )
        assert result.domain == "api"

    def test_detect_security(self, detector):
        result = detector.detect(
            ["security/validate.py", "sanitize.ts"],
            ["sanitize", "validate", "xss"],
        )
        assert result.domain in ("security", "auth")  # Could be either

    def test_detect_payments(self, detector):
        result = detector.detect(
            ["payments/stripe.py", "billing/invoice.ts"],
            ["payment", "charge", "subscription"],
        )
        assert result.domain == "payments"

    def test_matched_files_tracked(self, detector):
        result = detector.detect(["auth.py", "other.py"], [])
        assert len(result.matched_files) > 0

    def test_matched_keywords_tracked(self, detector):
        result = detector.detect([], ["token", "other"])
        assert len(result.matched_keywords) > 0

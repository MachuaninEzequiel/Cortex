"""Tests for cortex.autopilot.detectors."""
from __future__ import annotations

import pytest

from cortex.autopilot.detectors.ambiguous import AmbiguousRequestDetector
from cortex.autopilot.detectors.base import resolve_detectors
from cortex.autopilot.detectors.default import (
    CodeChangeDetector,
    DocsOnlyDetector,
    LargeRefactorDetector,
    NoopDetector,
    QuestionOnlyDetector,
    SecuritySensitiveDetector,
)
from cortex.autopilot.models import DetectionRequest, DetectionResult


class TestAmbiguousRequestDetector:
    def test_no_request(self) -> None:
        d = AmbiguousRequestDetector()
        res = d.detect(DetectionRequest(user_request=None))
        assert res.task_type == "ambiguous"
        assert res.confidence == 0.9

    def test_short_vague_no_file(self) -> None:
        d = AmbiguousRequestDetector()
        res = d.detect(DetectionRequest(user_request="fix login"))
        assert res.task_type == "ambiguous"
        assert res.confidence == 0.7

    def test_specific_with_file(self) -> None:
        d = AmbiguousRequestDetector()
        res = d.detect(DetectionRequest(user_request="fix login.py auth bug"))
        assert res.task_type == "noop"

    def test_long_enough(self) -> None:
        d = AmbiguousRequestDetector()
        res = d.detect(DetectionRequest(user_request="improve the overall user experience of the login flow"))
        assert res.task_type == "noop"


class TestQuestionOnlyDetector:
    def test_pure_question(self) -> None:
        d = QuestionOnlyDetector()
        res = d.detect(DetectionRequest(user_request="How does the auth flow work?"))
        assert res.task_type == "question-only"
        assert res.confidence == 0.75

    def test_not_question_with_files(self) -> None:
        d = QuestionOnlyDetector()
        res = d.detect(DetectionRequest(user_request="How does auth work?", changed_files=["auth.py"]))
        assert res.task_type == "noop"

    def test_no_request(self) -> None:
        d = QuestionOnlyDetector()
        res = d.detect(DetectionRequest())
        assert res.task_type == "noop"


class TestDocsOnlyDetector:
    def test_docs_files_only(self) -> None:
        d = DocsOnlyDetector()
        res = d.detect(DetectionRequest(changed_files=["README.md", "CHANGELOG.md"]))
        assert res.task_type == "docs-only"
        assert res.confidence == 0.8

    def test_mixed_files(self) -> None:
        d = DocsOnlyDetector()
        res = d.detect(DetectionRequest(changed_files=["README.md", "app.py"]))
        assert res.task_type == "noop"

    def test_docs_keywords(self) -> None:
        d = DocsOnlyDetector()
        res = d.detect(DetectionRequest(user_request="update the readme"))
        assert res.task_type == "docs-only"

    def test_docs_keywords_with_code_intent(self) -> None:
        d = DocsOnlyDetector()
        res = d.detect(DetectionRequest(user_request="update the readme and fix the bug"))
        assert res.task_type == "noop"


class TestSecuritySensitiveDetector:
    def test_security_file(self) -> None:
        d = SecuritySensitiveDetector()
        res = d.detect(DetectionRequest(changed_files=["auth.py"]))
        assert res.task_type == "security"
        assert res.confidence == 0.8

    def test_security_request(self) -> None:
        d = SecuritySensitiveDetector()
        res = d.detect(DetectionRequest(user_request="Fix JWT token validation"))
        assert res.task_type == "security"
        assert res.confidence == 0.7

    def test_no_security(self) -> None:
        d = SecuritySensitiveDetector()
        res = d.detect(DetectionRequest(user_request="Add logging to app.py"))
        assert res.task_type == "noop"


class TestLargeRefactorDetector:
    def test_many_files(self) -> None:
        d = LargeRefactorDetector()
        res = d.detect(DetectionRequest(changed_files=[f"f{i}.py" for i in range(6)]))
        assert res.task_type == "deep-code"
        assert res.confidence == 0.65

    def test_refactor_keyword(self) -> None:
        d = LargeRefactorDetector()
        res = d.detect(DetectionRequest(user_request="Refactor the auth module"))
        assert res.task_type == "deep-code"

    def test_no_refactor(self) -> None:
        d = LargeRefactorDetector()
        res = d.detect(DetectionRequest(user_request="Fix typo"))
        assert res.task_type == "noop"


class TestCodeChangeDetector:
    def test_code_files(self) -> None:
        d = CodeChangeDetector()
        res = d.detect(DetectionRequest(changed_files=["app.py"]))
        assert res.task_type == "fast-code"

    def test_many_code_files(self) -> None:
        d = CodeChangeDetector()
        res = d.detect(DetectionRequest(changed_files=[f"f{i}.py" for i in range(4)]))
        assert res.task_type == "deep-code"

    def test_implement_keyword(self) -> None:
        d = CodeChangeDetector()
        res = d.detect(DetectionRequest(user_request="Implement user login"))
        assert res.task_type == "fast-code"


class TestResolveDetectors:
    def test_ambiguous_blocks(self) -> None:
        detectors = [AmbiguousRequestDetector(), CodeChangeDetector()]
        req = DetectionRequest(user_request="fix login")
        res = resolve_detectors(detectors, req)
        assert res.task_type == "ambiguous"

    def test_security_wins(self) -> None:
        detectors = [SecuritySensitiveDetector(), CodeChangeDetector()]
        req = DetectionRequest(changed_files=["auth.py"])
        res = resolve_detectors(detectors, req)
        assert res.task_type == "security"

    def test_highest_confidence_wins(self) -> None:
        detectors = [CodeChangeDetector(), DocsOnlyDetector()]
        req = DetectionRequest(changed_files=["README.md"])
        res = resolve_detectors(detectors, req)
        assert res.task_type == "docs-only"

    def test_tie_prefers_conservative(self) -> None:
        # Both have same confidence, but noop has lower complexity rank
        detectors = [NoopDetector(), CodeChangeDetector()]
        req = DetectionRequest(user_request="Implement user login")
        res = resolve_detectors(detectors, req)
        assert res.task_type == "fast-code"

    def test_no_confident_results(self) -> None:
        detectors = [NoopDetector()]
        req = DetectionRequest()
        res = resolve_detectors(detectors, req)
        assert res.task_type == "noop"

    def test_empty_detector_list(self) -> None:
        res = resolve_detectors([], DetectionRequest())
        assert res.task_type == "noop"

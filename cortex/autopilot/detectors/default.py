"""cortex.autopilot.detectors.default — Built-in detectors."""
from __future__ import annotations

from cortex.autopilot.models import DetectionRequest, DetectionResult


class CodeChangeDetector:
    """Detects tasks that involve code changes."""

    name = "code_change"

    CODE_EXTS = (".py", ".ts", ".js", ".jsx", ".tsx", ".go", ".rs", ".java", ".cpp", ".c", ".h")

    def detect(self, request: DetectionRequest) -> DetectionResult:
        if request.changed_files:
            code_files = [f for f in request.changed_files if any(f.endswith(ext) for ext in self.CODE_EXTS)]
            if code_files:
                count = len(code_files)
                if count > 3:
                    return DetectionResult(
                        task_type="deep-code",
                        confidence=0.6,
                        reason=f"{count} code files changed",
                        suggested_complexity="deep",
                    )
                return DetectionResult(
                    task_type="fast-code",
                    confidence=0.7,
                    reason=f"{count} code files changed",
                    suggested_complexity="fast",
                )

        if request.user_request:
            req_lower = request.user_request.lower()
            code_keywords = {"implement", "refactor", "add feature", "bugfix", "fix bug", "crear", "implementar"}
            if any(kw in req_lower for kw in code_keywords):
                return DetectionResult(
                    task_type="fast-code",
                    confidence=0.5,
                    reason="Code-related keywords detected in request",
                    suggested_complexity="fast",
                )

        return DetectionResult(
            task_type="noop",
            confidence=0.0,
            reason="No code changes detected",
            suggested_complexity="none",
        )


class DocsOnlyDetector:
    """Detects tasks that only touch documentation."""

    name = "docs_only"

    DOCS_EXTS = (".md", ".rst", ".txt", ".adoc")

    def detect(self, request: DetectionRequest) -> DetectionResult:
        if request.changed_files:
            docs_files = [f for f in request.changed_files if any(f.endswith(ext) for ext in self.DOCS_EXTS)]
            non_docs = [f for f in request.changed_files if f not in docs_files]
            if docs_files and not non_docs:
                return DetectionResult(
                    task_type="docs-only",
                    confidence=0.8,
                    reason=f"Only documentation files changed ({len(docs_files)})",
                    suggested_complexity="none",
                )

        if request.user_request:
            req_lower = request.user_request.lower()
            doc_keywords = {"document", "docs", "readme", "changelog", "guia", "guía", "manual"}
            if any(kw in req_lower for kw in doc_keywords):
                # Check for code keywords that would override
                code_keywords = {"implement", "fix", "refactor", "bug"}
                if not any(kw in req_lower for kw in code_keywords):
                    return DetectionResult(
                        task_type="docs-only",
                        confidence=0.6,
                        reason="Documentation keywords detected",
                        suggested_complexity="none",
                    )

        return DetectionResult(
            task_type="noop",
            confidence=0.0,
            reason="No documentation-only changes detected",
            suggested_complexity="none",
        )


class QuestionOnlyDetector:
    """Detects questions that do not require any file changes."""

    name = "question_only"

    QUESTION_STARTS = ("what", "how", "why", "when", "where", "who", "which", "can you", "could you", "explain", "describe")
    QUESTION_MARKERS = ("?", "what is", "how to", "how do", "how does")

    def detect(self, request: DetectionRequest) -> DetectionResult:
        if request.changed_files:
            return DetectionResult(
                task_type="noop",
                confidence=0.0,
                reason="Files changed — not a pure question",
                suggested_complexity="none",
            )

        if not request.user_request:
            return DetectionResult(
                task_type="noop",
                confidence=0.0,
                reason="No user request to evaluate",
                suggested_complexity="none",
            )

        req_lower = request.user_request.lower().strip()
        is_question = (
            req_lower.endswith("?")
            or any(req_lower.startswith(qs) for qs in self.QUESTION_STARTS)
            or any(qm in req_lower for qm in self.QUESTION_MARKERS)
        )

        if is_question:
            return DetectionResult(
                task_type="question-only",
                confidence=0.75,
                reason="Pure question without file changes",
                suggested_complexity="none",
            )

        return DetectionResult(
            task_type="noop",
            confidence=0.0,
            reason="Not detected as a question",
            suggested_complexity="none",
        )


class SecuritySensitiveDetector:
    """Detects changes in auth, crypto, permissions, or secrets."""

    name = "security_sensitive"

    SECURITY_FILES = {
        "auth", "authentication", "authorization", "login", "logout",
        "password", "secret", "key", "token", "jwt", "oauth",
        "crypto", "encrypt", "decrypt", "hash", "salt",
        "permission", "acl", "rbac", "role",
    }
    SECURITY_KEYWORDS = {
        "password", "secret", "token", "jwt", "encrypt", "hash",
        "permission", "role", "security", "vulnerability", "cve",
        "exploit", "csrf", "xss", "sql injection",
    }
    SECONDARY_KEYWORDS = {"auth", "login", "oauth"}

    def detect(self, request: DetectionRequest) -> DetectionResult:
        # Check changed files
        if request.changed_files:
            for f in request.changed_files:
                f_lower = f.lower()
                if any(kw in f_lower for kw in self.SECURITY_FILES):
                    return DetectionResult(
                        task_type="security",
                        confidence=0.8,
                        reason=f"Security-sensitive file: {f}",
                        suggested_complexity="deep",
                    )

        # Check user request
        if request.user_request:
            req_lower = request.user_request.lower()
            if any(kw in req_lower for kw in self.SECURITY_KEYWORDS):
                return DetectionResult(
                    task_type="security",
                    confidence=0.7,
                    reason="Security keywords in request",
                    suggested_complexity="deep",
                )
            if any(kw in req_lower for kw in self.SECONDARY_KEYWORDS):
                return DetectionResult(
                    task_type="security",
                    confidence=0.45,
                    reason="Secondary security keywords in request",
                    suggested_complexity="deep",
                )

        return DetectionResult(
            task_type="noop",
            confidence=0.0,
            reason="No security indicators detected",
            suggested_complexity="none",
        )


class LargeRefactorDetector:
    """Detects tasks that affect many files or modules (deep track)."""

    name = "large_refactor"

    REFACTOR_KEYWORDS = {"refactor", "rewrite", "rearchitecture", "migrate", "upgrade", "modernize"}
    DEEP_FILE_THRESHOLD = 5

    def detect(self, request: DetectionRequest) -> DetectionResult:
        if request.changed_files and len(request.changed_files) >= self.DEEP_FILE_THRESHOLD:
            return DetectionResult(
                task_type="deep-code",
                confidence=0.65,
                reason=f"{len(request.changed_files)} files changed — large scope",
                suggested_complexity="deep",
            )

        if request.user_request:
            req_lower = request.user_request.lower()
            if any(kw in req_lower for kw in self.REFACTOR_KEYWORDS):
                return DetectionResult(
                    task_type="deep-code",
                    confidence=0.55,
                    reason="Refactor keywords detected",
                    suggested_complexity="deep",
                )

        return DetectionResult(
            task_type="noop",
            confidence=0.0,
            reason="No large refactor indicators",
            suggested_complexity="none",
        )


class NoopDetector:
    """Fallback detector when nothing else matches."""

    name = "noop"

    def detect(self, request: DetectionRequest) -> DetectionResult:
        return DetectionResult(
            task_type="noop",
            confidence=0.0,
            reason="Noop fallback",
            suggested_complexity="none",
        )

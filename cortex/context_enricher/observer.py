"""
cortex.context_enricher.observer
---------------------------------
Observes what the agent is working on and produces a WorkContext.

Sources:
  - git diff (staged or unstaged changes)
  - PR metadata (title, body, labels, branch)
  - Manual input (explicit files + keywords)

Also extracts: keywords, imports, function/class names, domain,
and generates search queries for the ContextEnricher.
"""

from __future__ import annotations

import re
import subprocess
from typing import TYPE_CHECKING

from cortex.context_enricher.domain_detector import DomainDetector

if TYPE_CHECKING:
    from cortex.models import WorkContext


# Patterns for code extraction
_IMPORT_PATTERNS = [
    re.compile(r"^import\s+([\w.]+)", re.MULTILINE),
    re.compile(r"^from\s+([\w.]+)\s+import", re.MULTILINE),
    re.compile(r"^(?:const|let|var)\s+\w+\s*=\s*require\(['\"]([\w./-]+)['\"]\)", re.MULTILINE),
]

_FUNCTION_PATTERNS = [
    re.compile(r"def\s+(\w+)\s*\(", re.MULTILINE),
    re.compile(r"(?:async\s+)?function\s+(\w+)\s*\(", re.MULTILINE),
    re.compile(r"(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\(", re.MULTILINE),
    re.compile(r"(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?function\s*\*?\s*\("),
]

_CLASS_PATTERNS = [
    re.compile(r"class\s+(\w+)", re.MULTILINE),
    re.compile(r"(?:export\s+)?class\s+(\w+)", re.MULTILINE),
    re.compile(r"(?:const|let|var)\s+(\w+)\s*=\s*class\s*{"),
]

# Additional entity patterns for extraction
_ERROR_PATTERNS = [
    re.compile(r"(?:Error|Exception|TypeError|ValueError|KeyError|ReferenceError):\s*(.+)"),
    re.compile(r"throw\s+new\s+(\w+Error)\s*\("),
    re.compile(r"catch\s*\(\s*(\w+Error)"),
]

_ENDPOINT_PATTERNS = [
    re.compile(r"@app\.(?:route|get|post|put|delete|patch)\(['\"]([^\"']+)['\"]"),
    re.compile(r"router\.(?:get|post|put|delete|patch)\(['\"]([^\"']+)['\"]"),
]


class ContextObserver:
    """
    Observes what the agent is working on and produces a WorkContext.

    The WorkContext includes files, keywords, imports, domain,
    and search queries for multi-strategy enrichment.
    """

    def __init__(self) -> None:
        self._detector = DomainDetector()

    def observe_from_git(self, base_branch: str = "main") -> WorkContext:
        """
        Observe work context from git diff against base branch.

        Args:
            base_branch: Branch to diff against (default "main").

        Returns:
            WorkContext with files, keywords, domain, and queries.
        """

        changed_files = self._get_changed_files(base_branch)
        new_files = self._get_new_files(base_branch)
        deleted_files = self._get_deleted_files(base_branch)

        # Extract keywords from the actual diff content
        diff_content = self._get_diff_content(base_branch)
        keywords = self._extract_keywords(diff_content)
        imports = self._extract_imports(diff_content)
        functions = self._extract_functions(diff_content)
        classes = self._extract_classes(diff_content)

        return self._build_context(
            source="git_diff",
            changed_files=changed_files,
            new_files=new_files,
            deleted_files=deleted_files,
            keywords=keywords,
            imports=imports,
            function_names=functions,
            class_names=classes,
        )

    def observe_from_pr(self, pr_context: object) -> WorkContext:
        """
        Observe work context from a PR context object.

        Args:
            pr_context: A PRContext object with title, body, files, etc.

        Returns:
            WorkContext with PR metadata.
        """

        files = getattr(pr_context, "files_changed", [])
        title = getattr(pr_context, "title", "")
        body = getattr(pr_context, "body", "")
        labels = getattr(pr_context, "labels", [])

        # Extract keywords from title + body
        text = f"{title} {body}"
        keywords = self._extract_text_keywords(text)
        # Also add PR title as a keyword
        if title:
            keywords = list(dict.fromkeys([title.lower()] + keywords))

        return self._build_context(
            source="pr",
            changed_files=files,
            keywords=keywords,
            pr_title=title,
            pr_body=body,
            pr_labels=labels,
        )

    def observe_from_files(
        self,
        files: list[str],
        keywords: list[str] | None = None,
        imports: list[str] | None = None,
        function_names: list[str] | None = None,
        class_names: list[str] | None = None,
        pr_title: str | None = None,
        pr_body: str | None = None,
        pr_labels: list[str] | None = None,
    ) -> WorkContext:
        """
        Observe work context from explicit file list.

        Args:
            files: Files being worked on.
            keywords: Pre-extracted keywords.
            imports: Pre-extracted imports.
            function_names: Function names being modified.
            class_names: Class names being modified.
            pr_title: Optional PR title.
            pr_body: Optional PR body.
            pr_labels: Optional PR labels.

        Returns:
            WorkContext with the provided data.
        """

        kw = list(keywords or [])
        imp = list(imports or [])
        funcs = list(function_names or [])
        classes = list(class_names or [])
        labels = list(pr_labels or [])

        return self._build_context(
            source="manual",
            changed_files=list(files),
            keywords=kw,
            imports=imp,
            function_names=funcs,
            class_names=classes,
            pr_title=pr_title,
            pr_body=pr_body,
            pr_labels=labels,
        )

    # ------------------------------------------------------------------
    # Internal: git helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _run_git(*args: str) -> str:
        """Run a git command and return stdout."""
        try:
            result = subprocess.run(
                ["git"] + list(args),
                capture_output=True, text=True, timeout=10,
            )
            return result.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return ""

    def _get_changed_files(self, base_branch: str) -> list[str]:
        """Get list of changed files from git diff."""
        output = self._run_git("diff", "--name-only", base_branch)
        return [f for f in output.strip().split("\n") if f] if output else []

    def _get_new_files(self, base_branch: str) -> list[str]:
        """Get list of new (untracked + staged) files."""
        # Untracked
        output = self._run_git("ls-files", "--others", "--exclude-standard")
        untracked = [f for f in output.strip().split("\n") if f] if output else []
        # Staged new files
        output2 = self._run_git("diff", "--name-only", "--diff-filter=A", "--cached")
        staged = [f for f in output2.strip().split("\n") if f] if output2 else []
        return list(dict.fromkeys(untracked + staged))

    def _get_deleted_files(self, base_branch: str) -> list[str]:
        """Get list of deleted files from git diff."""
        output = self._run_git("diff", "--name-only", "--diff-filter=D", base_branch)
        return [f for f in output.strip().split("\n") if f] if output else []

    def _get_diff_content(self, base_branch: str) -> str:
        """Get the actual diff content (for keyword extraction)."""
        return self._run_git("diff", base_branch)

    # ------------------------------------------------------------------
    # Internal: code extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_imports(content: str) -> list[str]:
        """Extract import statements from content."""
        imports: set[str] = set()
        for pattern in _IMPORT_PATTERNS:
            for match in pattern.findall(content):
                if isinstance(match, tuple):
                    # Take first non-empty match
                    match = next((m for m in match if m), "")
                if match:
                    # Take only the top-level module
                    module = match.split(".")[0]
                    imports.add(module)
        return sorted(imports)

    @staticmethod
    def _extract_functions(content: str) -> list[str]:
        """Extract function/method names from content."""
        funcs: set[str] = set()
        for pattern in _FUNCTION_PATTERNS:
            matches = pattern.findall(content)
            for match in matches:
                if isinstance(match, tuple):
                    # Take first non-empty match from regex groups
                    match = next((m for m in match if m), "")
                else:
                    match = match
                if match and not any(kw in match.lower() for kw in ["if", "else", "for", "while"]):
                    funcs.add(match)
        return sorted(funcs)

    @staticmethod
    def _extract_classes(content: str) -> list[str]:
        """Extract class names from content."""
        classes: set[str] = set()
        for pattern in _CLASS_PATTERNS:
            matches = pattern.findall(content)
            for match in matches:
                if isinstance(match, tuple):
                    match = next((m for m in match if m), "")
                else:
                    match = match
                if match:
                    classes.add(match)
        return sorted(classes)

    @staticmethod
    def _extract_keywords(content: str) -> list[str]:
        """
        Extract meaningful keywords from code content.

        Looks for: identifiers, string literals with semantic meaning,
        and known domain terms.
        """
        # Extract identifiers (variable names, function calls, etc.)
        identifiers = re.findall(r"\b([a-zA-Z_]\w{3,})\b", content)

        # Filter common noise and keep meaningful terms
        noise = {
            "const", "let", "var", "function", "return", "import",
            "export", "from", "class", "def", "self", "args", "kwargs",
            "true", "false", "null", "none", "undefined", "typeof",
            "async", "await", "try", "catch", "throw", "new", "this",
            "if", "else", "for", "while", "switch", "case", "break",
            "type", "interface", "extends", "implements", "public",
            "private", "protected", "static", "readonly", "override",
        }

        # Count frequency (more frequent = more important)
        freq: dict[str, int] = {}
        for ident in identifiers:
            if ident.lower() not in noise:
                freq[ident] = freq.get(ident, 0) + 1

        # Keep top keywords (by frequency, max 15)
        sorted_keywords = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        return [kw for kw, _ in sorted_keywords[:15]]

    @staticmethod
    def _extract_text_keywords(text: str) -> list[str]:
        """Extract keywords from natural text (PR title/body)."""
        # Simple: split on spaces/punctuation, filter short words
        words = re.findall(r"\b([a-zA-Z][a-zA-Z-]{2,})\b", text)
        noise = {"the", "and", "for", "with", "this", "that", "from",
                 "have", "been", "are", "was", "not", "but", "what",
                 "all", "when", "there", "can", "your", "more", "will"}
        filtered = [w.lower() for w in words if w.lower() not in noise]
        # Keep unique, max 10
        return list(dict.fromkeys(filtered))[:10]

    # ------------------------------------------------------------------
    # Internal: build context with domain detection and queries
    # ------------------------------------------------------------------

    def _build_context(self, *, source: str, **kwargs) -> WorkContext:
        """
        Build a WorkContext with domain detection and search queries.

        Args:
            source: "git_diff", "pr", or "manual".
            **kwargs: All fields for WorkContext.
        """
        from cortex.models import WorkContext

        # Run domain detection
        files = kwargs.get("changed_files", [])
        keywords = kwargs.get("keywords", [])
        domain_match = self._detector.detect(files, keywords)

        kwargs["detected_domain"] = domain_match.domain
        kwargs["domain_confidence"] = domain_match.confidence

        # Build search queries (4 strategies)
        queries = self._build_queries(
            domain=domain_match.domain,
            files=files,
            keywords=keywords,
            pr_title=kwargs.get("pr_title"),
        )
        kwargs["search_queries"] = queries

        # Add any missing required fields with defaults
        kwargs.setdefault("function_names", [])
        kwargs.setdefault("class_names", [])
        kwargs.setdefault("imports", [])

        return WorkContext(source=source, **kwargs)

    @staticmethod
    def _build_queries(
        domain: str | None,
        files: list[str],
        keywords: list[str],
        pr_title: str | None,
    ) -> list[str]:
        """
        Build 4 search queries for multi-strategy enrichment.

        1. Topic query: domain-based (e.g. "authentication token refresh")
        2. File query: filenames as search terms (e.g. "auth.py jwt.py")
        3. Keyword query: extracted keywords (e.g. "token refresh expiry")
        4. PR title query: full PR title
        """
        queries: list[str] = []

        # 1. Topic query
        if domain:
            queries.append(f"{domain} {' '.join(keywords[:5])}")
        elif keywords:
            queries.append(" ".join(keywords[:5]))

        # 2. File query (take filenames, strip paths/extensions)
        if files:
            file_terms = [f.split("/")[-1].split(".")[0] for f in files[:8]]
            queries.append(" ".join(file_terms))

        # 3. Keyword query
        if keywords:
            queries.append(" ".join(keywords[:8]))

        # 4. PR title query
        if pr_title:
            queries.append(pr_title)

        return queries

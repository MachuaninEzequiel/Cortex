"""
cortex.context_enricher.domain_detector
----------------------------------------
Maps files and keywords to thematic domains (auth, database, api, etc.).

Uses pattern matching with weighted scoring:
  - File patterns (weight 0.6): filename/path contains domain keywords
  - Keyword patterns (weight 0.4): content/code contains domain keywords

Returns the best-matching domain only if confidence > threshold.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np
    from numpy.typing import NDArray


@dataclass
class DomainMatch:
    """Result of domain detection."""
    domain: str | None          # e.g. "auth", "database", None
    confidence: float           # 0.0 - 1.0
    matched_files: list[str]    # Files that matched
    matched_keywords: list[str]  # Keywords that matched
    method_used: str = "rules"  # "rules" or "embedding"


# Domain rules: file patterns and content keywords
DOMAIN_RULES: dict[str, dict[str, list[str]]] = {
    "auth": {
        "file_patterns": [
            "auth", "login", "logout", "session", "token", "jwt",
            "oauth", "password", "credential", "sso", "mfa", "2fa",
        ],
        "keywords": [
            "authenticate", "authentication", "authorization",
            "login", "logout", "token", "session", "credentiv2",
            "jwt", "oauth", "refresh_token", "access_token",
            "password_hash", "bcrypt", "secret",
        ],
    },
    "database": {
        "file_patterns": [
            "migration", "schema", "model", "repository", "db",
            "sql", "alembic", "sequelize", "prisma", "orm",
        ],
        "keywords": [
            "migration", "schema", "query", "transaction",
            "connection", "pool", "database", "table", "column",
            "index", "foreign_key", "constraint", "rollback",
        ],
    },
    "api": {
        "file_patterns": [
            "route", "endpoint", "controller", "handler", "api",
            "rest", "graphql", "grpc", "middleware", "router",
        ],
        "keywords": [
            "endpoint", "route", "handler", "request", "response",
            "status_code", "middleware", "json", "payload",
            "get", "post", "put", "delete", "patch",
        ],
    },
    "security": {
        "file_patterns": [
            "security", "vulnerability", "sanitize", "validation",
            "encrypt", "hash", "cors", "csrf", "xss",
        ],
        "keywords": [
            "sanitize", "validate", "encrypt", "hash",
            "vulnerability", "injection", "xss", "csrf",
            "cors", "csp", "rate_limit", "throttle",
        ],
    },
    "payments": {
        "file_patterns": [
            "payment", "billing", "invoice", "stripe", "checkout",
            "subscription", "pricing", "plan",
        ],
        "keywords": [
            "payment", "charge", "invoice", "subscription",
            "stripe", "billing", "refund", "currency",
            "plan", "pricing",
        ],
    },
    # NEW DOMAINS
    "ui": {
        "file_patterns": [
            "component", "view", "template", "html", "css", "jsx",
            "tsx", "svelte", "vue", "angular", "react",
        ],
        "keywords": [
            "render", "component", "props", "state", "stylesheet",
            "css", "scss", "styled", "ui", "ux", "interface",
        ],
    },
    "testing": {
        "file_patterns": [
            "test", "spec", "fixture", "mock", "stub",
        ],
        "keywords": [
            "test", "expect", "assert", "describe", "it",
            "jest", "mocha", "chai", "vitest", "playwright",
            "cypress", "selenium", "pytest", "unittest",
        ],
    },
    "infrastructure": {
        "file_patterns": [
            "docker", "k8s", "kubernetes", "terraform", "ansible",
            "deploy", "helm", "pulumi", "cloudformation",
        ],
        "keywords": [
            "deploy", "infrastructure", "cloud", "aws", "azure",
            "gcp", "container", "orchestration", "kubernetes",
            "terraform", "helm", "ansible", "pulumi",
        ],
    },
    "data": {
        "file_patterns": [
            "etl", "pipeline", "analytics", "report", "dashboard",
            "chart", "graph", "visualization", "powerbi", "tableau",
        ],
        "keywords": [
            "etl", "pipeline", "data", "analytics", "report",
            "dashboard", "visualization", "chart", "graph",
            "bi", "business intelligence", "sql", "nosql",
        ],
    },
    "i18n": {
        "file_patterns": [
            "locale", "translation", "i18n", "l10n",
        ],
        "keywords": [
            "i18n", "l10n", "translate", "locale", "language",
            "internationalization", "localization", "gettext",
            "polyglot", "format", "message",
        ],
    },
    "logging": {
        "file_patterns": [
            "logger", "log", "monitor", "alert", "metric",
        ],
        "keywords": [
            "log", "logging", "logger", "monitor", "metric",
            "alert", "trace", "debug", "info", "warn", "error",
            "fatal", "observability", "telemetry", "tracing",
        ],
    },
    "configuration": {
        "file_patterns": [
            "config", "env", "settings", "constants",
        ],
        "keywords": [
            "config", "configuration", "setting", "constant",
            "env", "environment", "variable", "yaml", "json",
            "ini", "toml", "properties", "dotenv",
        ],
    },
}

_FILE_WEIGHT = 0.6
_KEYWORD_WEIGHT = 0.4


class DomainDetector:
    """
    Detects the thematic domain from file paths and keywords.

    Uses pattern matching with weighted scoring (rules) and falls back
    to embedding-based similarity for ambiguous cases. Returns the best
    matching domain only if confidence exceeds the threshold.

    Args:
        min_confidence: Minimum confidence to return a domain (default 0.5).
        embedding_model: Embedding model to use for fallback (default: same as cortex).
    """

    def __init__(self, min_confidence: float = 0.5) -> None:
        self.min_confidence = min_confidence
        self._embedder = None
        self._domain_centroids = {}
        self._initialize_embedding_fallback()

    def _initialize_embedding_fallback(self) -> None:
        """Initialize embedding fallback for domain detection."""
        try:
            from cortex.episodic.embedder import Embedder
            self._embedder = Embedder(
                model_name="all-MiniLM-L6-v2",
                backend="local"
            )
            
            # Pre-compute domain centroids for embedding fallback
            domain_descriptions = {
                "auth": "authentication token jwt login session oauth password credential",
                "database": "migration schema query sql database table model repository",
                "api": "endpoint route handler controller request response status middleware",
                "security": "sanitize validate encrypt hash vulnerability injection xss csrf",
                "payments": "payment charge invoice subscription stripe billing refund currency",
                "ui": "component view template render css jsx tsx angular react svelte vue",
                "testing": "test expect assert describe it jest mocha chai vitest playwright cypress",
                "infrastructure": "deploy infrastructure cloud aws azure gcp container orchestration kubernetes terraform",
                "data": "etl pipeline analytics report dashboard chart graph visualization bi",
                "i18n": "translate locale language internationalization localization gettext polyglot",
                "logging": "log logging logger monitor metric alert trace debug info warn error",
                "configuration": "config configuration setting constant env environment variable yaml json",
            }
            
            for domain, description in domain_descriptions.items():
                self._domain_centroids[domain] = self._embedder.embed(description)
                
        except Exception:
            # Embedding fallback not available, will rely on rules only
            pass

    def _embedding_fallback(self, files: list[str], keywords: list[str]) -> tuple[str | None, float]:
        """Use embedding similarity as fallback when rules are inconclusive."""
        if not self._embedder or not self._domain_centroids:
            return None, 0.0
            
        try:
            # Create text from files and keywords
            file_text = " ".join([f.split("/")[-1].split(".")[0] for f in files])
            keyword_text = " ".join(keywords)
            text = f"{file_text} {keyword_text}".strip()
            
            if not text:
                return None, 0.0
                
            # Embed the query text
            query_vec = self._embedder.embed(text)
            
            # Find closest domain centroid
            best_domain = None
            best_sim = 0.0
            
            import numpy as np
            for domain, centroid in self._domain_centroids.items():
                # Cosine similarity
                sim = np.dot(query_vec, centroid) / (np.linalg.norm(query_vec) * np.linalg.norm(centroid))
                if sim > best_sim:
                    best_sim = sim
                    best_domain = domain
                    
            return best_domain, float(best_sim)
        except Exception:
            return None, 0.0

    def detect(
        self,
        files: list[str],
        keywords: list[str] | None = None,
    ) -> DomainMatch:
        """
        Detect the thematic domain from files and keywords.

        Uses pattern matching with weighted scoring (rules) and falls back
        to embedding-based similarity for ambiguous cases.

        Args:
            files: File paths (e.g. ["auth.py", "jwt.ts"]).
            keywords: Content/code keywords extracted from the work.

        Returns:
            DomainMatch with the best domain and confidence.
        """
        if not files and not keywords:
            return DomainMatch(domain=None, confidence=0.0, matched_files=[], matched_keywords=[])

        keywords = keywords or []
        
        # PHASE 1: Rules-based detection (fast, 90% of cases)
        file_scores: dict[str, float] = {}
        keyword_scores: dict[str, float] = {}

        # Score domains by file patterns
        for domain, rules in DOMAIN_RULES.items():
            patterns = rules["file_patterns"]
            matched = [
                f for f in files
                if any(p in f.lower() for p in patterns)
            ]
            if matched:
                # Score = fraction of files that matched
                file_scores[domain] = len(matched) / max(len(files), 1)

        # Score domains by keywords
        for domain, rules in DOMAIN_RULES.items():
            domain_keywords = rules["keywords"]
            matched = [
                kw for kw in keywords
                if any(dkw in kw.lower() for dkw in domain_keywords)
            ]
            if matched:
                # Score = fraction of keywords that matched
                keyword_scores[domain] = len(matched) / max(len(keywords), 1)

        # Combine scores
        all_domains = set(file_scores.keys()) | set(keyword_scores.keys())
        best_domain: str | None = None
        best_score = 0.0
        all_matched_files: list[str] = []
        all_matched_keywords: list[str] = []

        for domain in all_domains:
            file_score = file_scores.get(domain, 0.0)
            kw_score = keyword_scores.get(domain, 0.0)
            combined = (_FILE_WEIGHT * file_score) + (_KEYWORD_WEIGHT * kw_score)

            if combined > best_score:
                best_score = combined
                best_domain = domain
                # Collect matched items for explainability
                if domain in DOMAIN_RULES:
                    patterns = DOMAIN_RULES[domain]["file_patterns"]
                    all_matched_files = [
                        f for f in files
                        if any(p in f.lower() for p in patterns)
                    ]
                    domain_keywords = DOMAIN_RULES[domain]["keywords"]
                    all_matched_keywords = [
                        kw for kw in keywords
                        if any(dkw in kw.lower() for dkw in domain_keywords)
                    ]

        # If rules give good confidence (> 0.5), use them
        if best_score >= 0.5:
            return DomainMatch(
                domain=best_domain,
                confidence=best_score,
                matched_files=all_matched_files,
                matched_keywords=all_matched_keywords,
                method_used="rules"
            )
        
        # PHASE 2: Embedding fallback (slow, 10% of cases) for ambiguous cases
        if self._embedder and self._domain_centroids:
            embed_domain, embed_confidence = self._embedding_fallback(files, keywords)
            if embed_domain and embed_confidence > best_score:
                # Use embedding result if it's better than rules
                # Re-collect matched items for the chosen domain for explainability
                matched_files = []
                matched_keywords = []
                if embed_domain in DOMAIN_RULES:
                    patterns = DOMAIN_RULES[embed_domain]["file_patterns"]
                    matched_files = [
                        f for f in files
                        if any(p in f.lower() for p in patterns)
                    ]
                    domain_keywords = DOMAIN_RULES[embed_domain]["keywords"]
                    matched_keywords = [
                        kw for kw in keywords
                        if any(dkw in kw.lower() for dkw in domain_keywords)
                    ]
                
                return DomainMatch(
                    domain=embed_domain,
                    confidence=embed_confidence,
                    matched_files=matched_files,
                    matched_keywords=matched_keywords,
                    method_used="embedding"
                )
        
        # Only return domain if confidence is high enough
        if best_score < self.min_confidence:
            return DomainMatch(
                domain=None,
                confidence=best_score,
                matched_files=all_matched_files,
                matched_keywords=all_matched_keywords,
                method_used="rules" if best_score > 0 else "none"
            )

        return DomainMatch(
            domain=best_domain,
            confidence=best_score,
            matched_files=all_matched_files,
            matched_keywords=all_matched_keywords,
            method_used="rules"
        )

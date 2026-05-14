"""cortex.context_enricher.telemetry - Persistent observer for enrichment events.

Implements the Mecanismo 1 telemetry of the canonical-documentation initiative:
every call to ``ContextEnricher.enrich()`` produces an ``EnrichmentEvent``
appended to ``.cortex/enrichment-events.jsonl``. When the agent later cites an
item (via wiki-link or markdown link inside the session body) a ``CitationEvent``
is appended to the same file.

The session writer reads recent events to populate the ``cortex_telemetry``
frontmatter block on the session note.

The observer is non-blocking: persistence failures are logged but never abort
the enrichment pipeline.

This module is opt-in. ``ContextEnricher`` accepts ``observer=None`` and
behaves exactly as before when no observer is attached.
"""

from __future__ import annotations

import json
import logging
import re
import statistics
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cortex.models import EnrichedContext

logger = logging.getLogger(__name__)

# Wiki-link pattern: [[note]] or [[note|alias]] or [[note#section]].
_WIKI_LINK_RE = re.compile(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]")
# Markdown link to a vault path: [text](path.md) or [text](decisions/x.md).
_MD_LINK_RE = re.compile(r"\]\(([^)]+\.md)(?:#[^)]*)?\)")


# ---------------------------------------------------------------------------
# Event dataclasses (serialized to JSONL).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EnrichmentEvent:
    """A single enrichment invocation."""

    event_type: str  # "enrichment"
    run_id: str
    timestamp: str  # ISO 8601
    latency_ms: int | None
    total_searches: int
    total_raw_hits: int
    total_items: int
    total_chars: int
    within_budget: bool
    items_offered: list[dict[str, Any]]


@dataclass(frozen=True)
class CitationEvent:
    """An item that was actually cited by the agent."""

    event_type: str  # "citation"
    run_id: str
    timestamp: str
    source_id: str


# ---------------------------------------------------------------------------
# Persistent observer.
# ---------------------------------------------------------------------------


class PersistentObserver:
    """Append-only JSONL log of enrichment and citation events.

    Layout:
        ``<path>``  - JSONL file with one event per line.
                      Each event has ``event_type`` to discriminate.

    Args:
        telemetry_path: full path to the JSONL file
            (typically ``<workspace>/.cortex/enrichment-events.jsonl``).
        enabled: opt-out switch. When False, all operations become no-ops
            and the file is not created.
    """

    def __init__(self, telemetry_path: Path, *, enabled: bool = True) -> None:
        self._path = telemetry_path
        self._enabled = enabled
        if self._enabled:
            self._path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def path(self) -> Path:
        return self._path

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record_enrichment(
        self,
        ctx: "EnrichedContext",
        *,
        latency_ms: int | None = None,
    ) -> str:
        """Record an enrichment event. Returns the new ``run_id``.

        Returns ``""`` and does nothing if the observer is disabled.
        """
        if not self._enabled:
            return ""

        run_id = uuid.uuid4().hex[:12]
        items_offered = [
            {
                "source_id": item.source_id,
                "source": item.source,
                "score": item.score,
                "enriched_score": item.enriched_score,
                "matched_by": list(item.matched_by),
                "tags": list(item.tags),
                "files_mentioned": list(item.files_mentioned),
            }
            for item in ctx.items
        ]
        event = EnrichmentEvent(
            event_type="enrichment",
            run_id=run_id,
            timestamp=datetime.now(UTC).isoformat(),
            latency_ms=latency_ms,
            total_searches=ctx.total_searches,
            total_raw_hits=ctx.total_raw_hits,
            total_items=ctx.total_items,
            total_chars=ctx.total_chars,
            within_budget=ctx.within_budget,
            items_offered=items_offered,
        )
        self._append(event)
        return run_id

    def record_citation(self, run_id: str, source_id: str) -> None:
        """Record that the agent cited an item from ``run_id``.

        No-op when disabled or when ``run_id`` is empty (caller had no observer).
        """
        if not self._enabled or not run_id:
            return
        event = CitationEvent(
            event_type="citation",
            run_id=run_id,
            timestamp=datetime.now(UTC).isoformat(),
            source_id=source_id,
        )
        self._append(event)

    # ------------------------------------------------------------------
    # Reading / aggregation
    # ------------------------------------------------------------------

    def iter_events(self) -> list[dict[str, Any]]:
        """Load all events from disk. Returns ``[]`` on missing or unreadable file."""
        if not self._enabled or not self._path.exists():
            return []
        events: list[dict[str, Any]] = []
        try:
            with self._path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        logger.warning("Skipping malformed telemetry line: %r", line[:80])
        except OSError:
            return []
        return events

    def events_for_run(self, run_id: str) -> dict[str, Any]:
        """Return ``{"enrichment": <event>, "citations": [<event>, ...]}`` for a run."""
        enrichment: dict[str, Any] = {}
        citations: list[dict[str, Any]] = []
        for ev in self.iter_events():
            if ev.get("run_id") != run_id:
                continue
            if ev.get("event_type") == "enrichment":
                enrichment = ev
            elif ev.get("event_type") == "citation":
                citations.append(ev)
        return {"enrichment": enrichment, "citations": citations}

    def aggregate(self, *, since_days: int | None = None) -> dict[str, Any]:
        """Aggregate events to produce a memory-report payload.

        Args:
            since_days: if given, only include events newer than ``now - since_days``.

        Returns:
            Dict with global counts, by_strategy breakdown, hit rate, latencies, etc.
        """
        events = self.iter_events()

        cutoff: datetime | None = None
        if since_days is not None:
            cutoff = datetime.now(UTC) - timedelta(days=since_days)

        enrichments: list[dict[str, Any]] = []
        citations: list[dict[str, Any]] = []
        for ev in events:
            ts = _parse_ts(ev.get("timestamp"))
            if cutoff is not None and ts is not None and ts < cutoff:
                continue
            if ev.get("event_type") == "enrichment":
                enrichments.append(ev)
            elif ev.get("event_type") == "citation":
                citations.append(ev)

        # Index citations by (run_id, source_id) for fast lookup.
        cited_by_run: dict[str, set[str]] = defaultdict(set)
        for c in citations:
            cited_by_run[c["run_id"]].add(c["source_id"])

        total_offered = 0
        total_used = 0
        by_strategy_offered: Counter[str] = Counter()
        by_strategy_used: Counter[str] = Counter()
        latencies_ms: list[int] = []

        for ev in enrichments:
            run_id = ev["run_id"]
            offered = ev.get("items_offered", [])
            total_offered += len(offered)
            used_in_run = cited_by_run.get(run_id, set())
            total_used += len(used_in_run)
            for item in offered:
                for strategy in item.get("matched_by", []):
                    by_strategy_offered[strategy] += 1
                    if item["source_id"] in used_in_run:
                        by_strategy_used[strategy] += 1
            if ev.get("latency_ms") is not None:
                latencies_ms.append(int(ev["latency_ms"]))

        latency_summary: dict[str, float] = {}
        if latencies_ms:
            latencies_ms.sort()
            latency_summary = {
                "p50_ms": float(statistics.median(latencies_ms)),
                "p95_ms": float(_percentile(latencies_ms, 0.95)),
                "p99_ms": float(_percentile(latencies_ms, 0.99)),
            }

        return {
            "window_days": since_days,
            "enrichments": len(enrichments),
            "citations": len(citations),
            "items_offered": total_offered,
            "items_used": total_used,
            "hit_rate": (total_used / total_offered) if total_offered else 0.0,
            "by_strategy": {
                strategy: {
                    "offered": by_strategy_offered[strategy],
                    "used": by_strategy_used.get(strategy, 0),
                    "hit_rate": (
                        by_strategy_used.get(strategy, 0)
                        / by_strategy_offered[strategy]
                    )
                    if by_strategy_offered[strategy]
                    else 0.0,
                }
                for strategy in by_strategy_offered
            },
            "latency": latency_summary,
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _append(self, event: EnrichmentEvent | CitationEvent) -> None:
        try:
            line = json.dumps(event.__dict__, default=str)
            with self._path.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        except OSError as exc:  # pragma: no cover - defensive
            logger.warning("Telemetry append failed: %s", exc)


# ---------------------------------------------------------------------------
# Citation detection.
# ---------------------------------------------------------------------------


def detect_citations(body: str, items_offered: list[dict[str, Any]]) -> list[str]:
    """Detect which offered items were cited in the session body.

    A citation is one of:
        - A wiki-link ``[[<name>]]`` whose target matches an offered ``source_id``
          or its filename stem.
        - A markdown link ``[text](path.md)`` whose path matches an offered
          ``source_id`` (full path or just the filename).

    Returns the list of cited ``source_id`` values, deduplicated and ordered
    by first appearance in ``items_offered``.
    """
    if not body or not items_offered:
        return []

    wiki_targets = {match.strip() for match in _WIKI_LINK_RE.findall(body)}
    md_targets = {match.strip() for match in _MD_LINK_RE.findall(body)}

    cited: list[str] = []
    seen: set[str] = set()
    for item in items_offered:
        sid = item.get("source_id")
        if not sid or sid in seen:
            continue
        # Compare to multiple shapes the agent might use:
        # - full path (decisions/ADR-007-foo.md)
        # - full path without .md (decisions/ADR-007-foo) - common in wiki-links
        # - stem only (ADR-007-foo)
        # - filename (ADR-007-foo.md)
        path = Path(sid)
        stem = path.stem
        name = path.name
        posix_full = path.as_posix()
        posix_no_ext = (
            posix_full[:-3] if posix_full.endswith(".md") else posix_full
        )
        candidates = {sid, stem, name, posix_full, posix_no_ext}

        if candidates & wiki_targets or candidates & md_targets:
            cited.append(sid)
            seen.add(sid)
    return cited


# ---------------------------------------------------------------------------
# Helpers.
# ---------------------------------------------------------------------------


def _parse_ts(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        # Allow trailing Z (UTC) and naive parsing.
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _percentile(sorted_values: list[int], pct: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    k = (len(sorted_values) - 1) * pct
    lo = int(k)
    hi = min(lo + 1, len(sorted_values) - 1)
    frac = k - lo
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * frac


def make_observer(
    workspace_layout: Any | None = None,
    *,
    enabled: bool | None = None,
    config: dict | None = None,
    project_root: Path | None = None,
) -> "PersistentObserver":
    """Create a ``PersistentObserver`` from a ``WorkspaceLayout`` or path.

    Resolves the canonical telemetry path
    (``<workspace_root>/.cortex/enrichment-events.jsonl``) and honours an
    optional ``retrieval.telemetry`` config block:

    .. code-block:: yaml

        retrieval:
          telemetry:
            enabled: true
            path: .cortex/enrichment-events.jsonl

    Args:
        workspace_layout: any object exposing ``workspace_root: Path``.
            Typically the result of ``WorkspaceLayout.discover(...)``.
        enabled: explicit override. ``None`` -> read from config; if no config
            entry, default ``True``.
        config: parsed ``config.yaml`` dict. Used to read
            ``retrieval.telemetry.enabled`` and ``retrieval.telemetry.path``.
        project_root: fallback when ``workspace_layout`` is not provided.

    Returns:
        Configured ``PersistentObserver`` (which may be disabled).
    """
    # Resolve base directory.
    base: Path
    if workspace_layout is not None and hasattr(workspace_layout, "workspace_root"):
        base = Path(workspace_layout.workspace_root)
    elif project_root is not None:
        base = Path(project_root)
    else:
        base = Path.cwd()

    # Resolve config overrides.
    cfg_enabled: bool = True
    cfg_path: str = ".cortex/enrichment-events.jsonl"
    if config and isinstance(config, dict):
        telemetry_cfg = (config.get("retrieval") or {}).get("telemetry") or {}
        if isinstance(telemetry_cfg, dict):
            cfg_enabled = bool(telemetry_cfg.get("enabled", cfg_enabled))
            cfg_path = str(telemetry_cfg.get("path") or cfg_path)

    if enabled is None:
        enabled = cfg_enabled

    telemetry_path = (base / cfg_path).resolve()
    return PersistentObserver(telemetry_path, enabled=enabled)


__all__ = [
    "CitationEvent",
    "EnrichmentEvent",
    "PersistentObserver",
    "detect_citations",
    "make_observer",
]

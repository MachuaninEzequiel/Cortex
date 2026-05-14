"""cortex.documentation.routing - Canonical routing table for DocTypes.

The ``DOC_TYPE_ROUTING`` dict is the *single source of truth* for:
- which subfolder each DocType lives in,
- how filenames are rendered,
- which Jinja2 template renders the body,
- which writer function persists the note,
- whether the note is promotable to enterprise (and how),
- chunking and retrieval boost configuration,
- webgraph styling.

The ``writer`` field is filled in by Fase 03 (canonical writers). For Fase 02
it is set to ``None`` for the 9 new types; the 3 legacy types (session, spec,
hu) reference the legacy shim re-exported via ``cortex.documentation``.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from cortex.documentation.doc_type import DocType
from cortex.documentation.errors import RoutingError, UnknownDocTypeError

# Templates directory: created in Fase 03. Path is resolved at definition time
# so the routing table can reference it without requiring the files to exist yet.
TEMPLATES_DIR = Path(__file__).parent / "templates"


@dataclass(frozen=True)
class RouteSpec:
    """Routing specification for a single DocType."""

    doc_type: DocType

    # Storage
    subfolder: str
    filename_template: str

    # Rendering
    template_path: Path

    # Writing (filled by Fase 03)
    writer: Callable | None = None
    indexer: str = "auto"  # "auto" | "manual"

    # Enterprise
    promotable: bool = False
    promotion_mode: str = "as-is"  # "as-is" | "summarize" | "review-required"
    enterprise_subfolder: str | None = None

    # Retrieval
    retrieval_boost_per_intent: dict[str, float] = field(default_factory=dict)
    chunking_enabled: bool = True
    chunking_min_words: int = 500
    chunking_boundary: str = "h2"  # "h2" | "h3" | "paragraph"

    # Webgraph
    webgraph_color: str = "#cccccc"
    webgraph_shape: str = "rectangle"

    # Lifecycle
    requires_review_before_publish: bool = False
    auto_expire_days: int = 0  # 0 = never auto-expires


# ---------------------------------------------------------------------------
# Canonical routing table.
# ---------------------------------------------------------------------------

DOC_TYPE_ROUTING: dict[DocType, RouteSpec] = {
    DocType.SESSION: RouteSpec(
        doc_type=DocType.SESSION,
        subfolder="sessions",
        filename_template="{date}_{session_id}_{slug}.md",
        template_path=TEMPLATES_DIR / "session.md.j2",
        writer=None,  # Fase 04 migrates the legacy writer here
        indexer="auto",
        promotable=True,
        promotion_mode="summarize",
        enterprise_subfolder="sessions/{project_id}",
        retrieval_boost_per_intent={
            "history": 1.3,
            "recent": 1.5,
            "episodic": 1.4,
        },
        chunking_enabled=False,
        webgraph_color="#88aaff",
        webgraph_shape="rectangle",
    ),
    DocType.HANDOFF: RouteSpec(
        doc_type=DocType.HANDOFF,
        subfolder="handoffs",
        filename_template="{date}_{slug}.md",
        template_path=TEMPLATES_DIR / "handoff.md.j2",
        writer=None,  # Fase 03
        indexer="auto",
        promotable=False,
        enterprise_subfolder=None,
        retrieval_boost_per_intent={
            "recent": 2.0,
            "history": 1.0,
        },
        chunking_enabled=False,
        webgraph_color="#ffaa44",
        webgraph_shape="diamond",
        auto_expire_days=14,
    ),
    DocType.SPEC: RouteSpec(
        doc_type=DocType.SPEC,
        subfolder="specs",
        filename_template="{date}_{slug}.md",
        template_path=TEMPLATES_DIR / "spec.md.j2",
        writer=None,  # Fase 04
        indexer="auto",
        promotable=True,
        promotion_mode="as-is",
        enterprise_subfolder="specs/{project_id}",
        retrieval_boost_per_intent={
            "spec": 2.0,
            "requirements": 1.8,
            "implementation": 1.4,
        },
        chunking_enabled=True,
        chunking_min_words=500,
        webgraph_color="#88ddaa",
        webgraph_shape="rectangle",
    ),
    DocType.ADR: RouteSpec(
        doc_type=DocType.ADR,
        subfolder="decisions",
        filename_template="ADR-{number:03d}-{slug}.md",
        template_path=TEMPLATES_DIR / "adr.md.j2",
        writer=None,  # Fase 03
        indexer="auto",
        promotable=True,
        promotion_mode="as-is",
        enterprise_subfolder="decisions/{project_id}",
        retrieval_boost_per_intent={
            "decision": 2.0,
            "architecture": 1.5,
            "history": 1.2,
            "rationale": 1.8,
        },
        chunking_enabled=True,
        chunking_min_words=400,
        chunking_boundary="h2",
        webgraph_color="#cc66ff",
        webgraph_shape="hexagon",
    ),
    DocType.DECISION: RouteSpec(
        doc_type=DocType.DECISION,
        subfolder="decisions",
        filename_template="DEC-{date}-{slug}.md",
        template_path=TEMPLATES_DIR / "decision.md.j2",
        writer=None,  # Fase 03
        indexer="auto",
        promotable=True,
        promotion_mode="as-is",
        enterprise_subfolder="decisions/{project_id}",
        retrieval_boost_per_intent={
            "decision": 1.5,
            "history": 1.2,
        },
        chunking_enabled=False,
        webgraph_color="#aa88cc",
        webgraph_shape="hexagon",
    ),
    DocType.INCIDENT: RouteSpec(
        doc_type=DocType.INCIDENT,
        subfolder="incidents",
        filename_template="INC-{number:03d}-{date}-{slug}.md",
        template_path=TEMPLATES_DIR / "incident.md.j2",
        writer=None,  # Fase 03
        indexer="auto",
        promotable=True,
        promotion_mode="as-is",
        enterprise_subfolder="incidents/{project_id}",
        retrieval_boost_per_intent={
            "incident": 2.5,
            "recent": 2.0,
            "history": 1.5,
            "runbook": 1.3,
        },
        chunking_enabled=True,
        chunking_min_words=500,
        webgraph_color="#ff6666",
        webgraph_shape="diamond",
    ),
    DocType.POSTMORTEM: RouteSpec(
        doc_type=DocType.POSTMORTEM,
        subfolder="postmortems",
        filename_template="PM-{incident_number:03d}-{slug}.md",
        template_path=TEMPLATES_DIR / "postmortem.md.j2",
        writer=None,  # Fase 03
        indexer="auto",
        promotable=True,
        promotion_mode="as-is",
        enterprise_subfolder="postmortems/{project_id}",
        retrieval_boost_per_intent={
            "postmortem": 2.5,
            "incident": 2.0,
            "root-cause": 2.2,
            "history": 1.5,
        },
        chunking_enabled=True,
        chunking_min_words=500,
        webgraph_color="#aa4444",
        webgraph_shape="diamond",
        requires_review_before_publish=True,
    ),
    DocType.RUNBOOK: RouteSpec(
        doc_type=DocType.RUNBOOK,
        subfolder="runbooks",
        filename_template="RB-{slug}.md",
        template_path=TEMPLATES_DIR / "runbook.md.j2",
        writer=None,  # Fase 03
        indexer="auto",
        promotable=True,
        promotion_mode="review-required",
        enterprise_subfolder="runbooks/{project_id}",
        retrieval_boost_per_intent={
            "runbook": 2.5,
            "procedure": 2.0,
            "deploy": 1.8,
            "rollback": 1.8,
            "operations": 1.5,
        },
        chunking_enabled=True,
        chunking_min_words=400,
        chunking_boundary="h2",
        webgraph_color="#66cccc",
        webgraph_shape="rectangle",
        requires_review_before_publish=True,
        auto_expire_days=180,
    ),
    DocType.ARCHITECTURE: RouteSpec(
        doc_type=DocType.ARCHITECTURE,
        subfolder="architecture",
        filename_template="{slug}.md",
        template_path=TEMPLATES_DIR / "architecture.md.j2",
        writer=None,  # Fase 03
        indexer="auto",
        promotable=True,
        promotion_mode="as-is",
        enterprise_subfolder="architecture/{project_id}",
        retrieval_boost_per_intent={
            "architecture": 2.5,
            "design": 2.0,
            "decision": 1.5,
            "overview": 1.5,
        },
        chunking_enabled=True,
        chunking_min_words=500,
        chunking_boundary="h2",
        webgraph_color="#6688cc",
        webgraph_shape="rectangle",
    ),
    DocType.CHANGELOG: RouteSpec(
        doc_type=DocType.CHANGELOG,
        subfolder="changelog",
        filename_template="{version}.md",
        template_path=TEMPLATES_DIR / "changelog.md.j2",
        writer=None,  # Fase 03
        indexer="auto",
        promotable=True,
        promotion_mode="as-is",
        enterprise_subfolder="changelog/{project_id}",
        retrieval_boost_per_intent={
            "changelog": 1.5,
            "release": 1.5,
            "version": 1.5,
        },
        chunking_enabled=True,
        chunking_min_words=500,
        webgraph_color="#999999",
        webgraph_shape="rectangle",
    ),
    DocType.HU: RouteSpec(
        doc_type=DocType.HU,
        subfolder="hu",
        filename_template="HU-{external_id}.md",
        template_path=TEMPLATES_DIR / "hu.md.j2",
        writer=None,  # Fase 04
        indexer="auto",
        promotable=False,
        enterprise_subfolder=None,
        retrieval_boost_per_intent={
            "task": 1.3,
            "requirements": 1.4,
            "current-work": 1.5,
        },
        chunking_enabled=False,
        webgraph_color="#ccaa66",
        webgraph_shape="ellipse",
    ),
    DocType.GLOSSARY: RouteSpec(
        doc_type=DocType.GLOSSARY,
        subfolder="glossary",
        filename_template="{term_slug}.md",
        template_path=TEMPLATES_DIR / "glossary.md.j2",
        writer=None,  # Fase 03
        indexer="auto",
        promotable=True,
        promotion_mode="as-is",
        enterprise_subfolder="glossary",  # no project_id namespacing
        retrieval_boost_per_intent={
            "glossary": 2.0,
            "definition": 2.5,
            "term": 2.5,
        },
        chunking_enabled=False,
        webgraph_color="#cccc66",
        webgraph_shape="ellipse",
    ),
}


# ---------------------------------------------------------------------------
# Public operations.
# ---------------------------------------------------------------------------

_PLACEHOLDER_RE = re.compile(r"\{([^{}:!]+)(?::[^}]*)?\}")


def resolve_route(doc_type: DocType) -> RouteSpec:
    """Look up the canonical RouteSpec for a DocType.

    Raises:
        UnknownDocTypeError: if doc_type is not in the routing table.
    """
    if doc_type not in DOC_TYPE_ROUTING:
        raise UnknownDocTypeError(f"{doc_type!r} not in routing table")
    return DOC_TYPE_ROUTING[doc_type]


def render_filename(spec: RouteSpec, context: dict) -> str:
    """Render ``spec.filename_template`` with ``context``.

    Raises:
        RoutingError: if any placeholder is missing from ``context``.
    """
    required = set(_PLACEHOLDER_RE.findall(spec.filename_template))
    missing = required - set(context.keys())
    if missing:
        raise RoutingError(
            f"Missing placeholders for {spec.doc_type.value} filename: {sorted(missing)}"
        )
    try:
        return spec.filename_template.format(**context)
    except (KeyError, ValueError) as e:  # ValueError raised by format spec errors
        raise RoutingError(
            f"Failed to render filename for {spec.doc_type.value}: {e}"
        ) from e


def resolve_target_path(
    spec: RouteSpec,
    context: dict,
    vault_root: Path,
    vault_scope: str = "local",
    project_id: str | None = None,
) -> Path:
    """Resolve the absolute target path for a note inside the vault.

    Branches:
        - vault_scope='local': vault_root / spec.subfolder / filename
        - vault_scope='enterprise': vault_root / spec.enterprise_subfolder.format(project_id) / filename

    Raises:
        RoutingError: if vault_scope='enterprise' but spec has no
            enterprise_subfolder, or if project_id is required but missing.
    """
    if vault_scope == "enterprise":
        if not spec.enterprise_subfolder:
            raise RoutingError(
                f"{spec.doc_type.value} is not promotable (no enterprise_subfolder)"
            )
        if "{project_id}" in spec.enterprise_subfolder and not project_id:
            raise RoutingError(
                f"project_id required for enterprise scope of {spec.doc_type.value}"
            )
        subfolder = spec.enterprise_subfolder.format(project_id=project_id or "")
    elif vault_scope == "local":
        subfolder = spec.subfolder
    else:
        raise RoutingError(
            f"vault_scope must be 'local' or 'enterprise', got {vault_scope!r}"
        )

    filename = render_filename(spec, context)
    return vault_root / subfolder / filename


def list_all_routes() -> list[RouteSpec]:
    """Return all RouteSpecs in DOC_TYPE_ROUTING (declaration order)."""
    return list(DOC_TYPE_ROUTING.values())


def routes_by_subfolder() -> dict[str, list[RouteSpec]]:
    """Group RouteSpecs by their ``subfolder`` value.

    Note: ``decisions/`` hosts both ADR and DECISION; its value is a list of 2.
    """
    grouped: dict[str, list[RouteSpec]] = {}
    for spec in DOC_TYPE_ROUTING.values():
        grouped.setdefault(spec.subfolder, []).append(spec)
    return grouped

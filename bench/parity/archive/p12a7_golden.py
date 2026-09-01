#!/usr/bin/env python3
"""Golden P12A-7 — context extras (filters/presenter/domain_detector/
observer/telemetry).

Construye un reporte determinista de los escenarios S01–S27 y lo compara
byte-a-byte contra el checker Rust `p12a7_check`.

Normalizaciones pactadas:
- {{ROOT}} ruta temporal base
- {{RUN}}  run_id uuid4[:12] generado por el observer Python/Rust
- {{TS}}   timestamps ISO reales (datetime.now)
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import yaml  # noqa: E402

from cortex.context_enricher.domain_detector import DomainDetector  # noqa: E402
from cortex.context_enricher.filters import EnrichmentFilters, apply_filters  # noqa: E402
from cortex.context_enricher.observer import ContextObserver  # noqa: E402
from cortex.context_enricher.presenter import ContextPresenter  # noqa: E402
from cortex.context_enricher.telemetry import (  # noqa: E402
    PersistentObserver,
    detect_citations,
    make_observer,
)
from cortex.models import EnrichedContext, EnrichedItem, WorkContext  # noqa: E402

FIXED_NOW = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)

SAMPLE_CODE = """
import os
from pathlib import Path
const fs = require('fs')
def refresh_token(user):
    return validate(user)
async function loginRequest() {}
const logoutHandler = () => {}
class AuthService:
    def helper_fn(self): pass
export class Session {}
"""


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_item(i=0, **kw) -> EnrichedItem:
    base = dict(
        source="episodic", source_id=f"item-{i}", title=f"Item {i}",
        content=f"body {i}", score=0.5, enriched_score=0.6,
        matched_by=["topic_search"], files_mentioned=[], date=None, tags=[],
        doc_type=None, status=None, vault_scope="local",
        origin_project_id=None, matched_chunk_id=None,
        matched_section_title=None,
    )
    base.update(kw)
    return EnrichedItem(**base)


def make_bundle_items():
    return [
        make_item(1, source="episodic", title="Nota A",
                  content="contenido corto",
                  date=datetime(2026, 5, 1, 10, 30, tzinfo=UTC),
                  files_mentioned=["src/a.py", "src/b.py"],
                  tags=["rust", "core"], matched_by=["topic_search"]),
        make_item(2, source="semantic", title="ADR larga",
                  content="x" * 350 + " fin",
                  score=0.42, enriched_score=0.9,
                  matched_by=["topic_search", "files_search"],
                  files_mentioned=[], tags=["decisiones"],
                  doc_type="adr", status="accepted",
                  vault_scope="enterprise", origin_project_id="proj-x",
                  matched_chunk_id="chunk-9",
                  matched_section_title="Decisión"),
        make_item(3, source="episodic", title="Legacy",
                  content="y" * 150, enriched_score=0.75,
                  matched_by=["keyword_query"]),
    ]

def ids(items):
    return [x.source_id for x in items]


def normalize(text: str, root: Path) -> str:
    s = text.replace(str(root), "{{ROOT}}")
    import re

    s = re.sub(r"\brun_id\": \"[0-9a-f]{12}\"", 'run_id": "{{RUN}}"', s)
    # líneas etiquetadas run=<id>
    s = re.sub(r"^run=[0-9a-f]{12}$", "run={{RUN}}", s, flags=re.M)
    s = re.sub(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:\+00:00|Z)",
               "{{TS}}", s)
    if not s.endswith("\n"):
        s += "\n"
    return s


# ---------------------------------------------------------------------------
# Escenarios
# ---------------------------------------------------------------------------

def bundle_total_chars() -> int:
    return sum(len(x.content) for x in make_bundle_items())


def build_report(root: Path) -> str:
    blocks: list[str] = []

    def emit(name, fn):
        try:
            blocks.append(f"### {name}\nrc=0\n{fn()}")
        except Exception as exc:  # noqa: BLE001
            blocks.append(f"### {name}\nrc=1\nException: {type(exc).__name__}: {exc}")

    # ------------------------- FILTERS ------------------------------------
    def s01():
        items = [make_item(1), make_item(2)]
        out = []
        assert EnrichmentFilters().is_empty()
        f_none = apply_filters(items, None)
        f_empty = apply_filters(items, EnrichmentFilters())
        out.append(f"none={ids(f_none)}")
        out.append(f"empty={ids(f_empty)}")
        out.append(f"is_list={isinstance(f_none, list)}")
        return "\n".join(out)

    def s02():
        items = [
            make_item(1, doc_type="adr"),
            make_item(2, doc_type="session"),
            make_item(3),
        ]
        keep = apply_filters(items, EnrichmentFilters(doc_types=["adr"]))
        strict = apply_filters(
            items, EnrichmentFilters(doc_types=["adr"], strict=True))
        return f"keep={ids(keep)}\nstrict={ids(strict)}"

    def s03():
        items = [make_item(1, doc_type="adr"), make_item(2, doc_type="session")]
        out = apply_filters(items, EnrichmentFilters(exclude_doc_types=["adr"]))
        return f"out={ids(out)}"

    def s04():
        items = [
            make_item(1, status="accepted"),
            make_item(2, status="draft"),
            make_item(3),
        ]
        allowed = apply_filters(items, EnrichmentFilters(statuses_allowed=["accepted"]))
        excluded = apply_filters(items, EnrichmentFilters(statuses_excluded=["draft"]))
        return f"allowed={ids(allowed)}\nexcluded={ids(excluded)}"

    def s05():
        items = [
            make_item(1, tags=["rust", "core"]),
            make_item(2, tags=["rust"]),
            make_item(3, tags=["python"]),
        ]
        req = apply_filters(items, EnrichmentFilters(tags_required=["rust", "core"]))
        anyof = apply_filters(items, EnrichmentFilters(tags_any_of=["python", "core"]))
        excl = apply_filters(items, EnrichmentFilters(tags_excluded=["rust"]))
        return f"required={ids(req)}\nany_of={ids(anyof)}\nexcluded={ids(excl)}"

    def s06():
        items = [
            make_item(1, vault_scope="local"),
            make_item(2, vault_scope="enterprise"),
        ]
        local = apply_filters(items, EnrichmentFilters(vault_scope="local"))
        ent = apply_filters(items, EnrichmentFilters(vault_scope="enterprise"))
        both = apply_filters(items, EnrichmentFilters(vault_scope="all"))
        return f"local={ids(local)}\nent={ids(ent)}\nboth={ids(both)}"

    def s07b():
        # Ventana determinista: fechas relativas al AHORA real.
        now = datetime.now(UTC)
        items = [
            make_item(1, date=now - timedelta(days=400)),
            make_item(2, date=now - timedelta(days=1)),
            make_item(3),
            make_item(4, date=(now - timedelta(days=2)).replace(tzinfo=None)),
        ]
        f = apply_filters(items, EnrichmentFilters(max_age_days=30))
        zero = apply_filters(items, EnrichmentFilters(max_age_days=0))
        none_ = apply_filters(items, EnrichmentFilters(max_age_days=None))
        return (
            f"window={ids(f)}\nzero_noop={ids(zero)}\nnone_noop={ids(none_)}"
        )

    def s08():
        items = [
            make_item(1, origin_project_id="p1"),
            make_item(2, origin_project_id="p2"),
            make_item(3),
        ]
        proj = apply_filters(items, EnrichmentFilters(project_ids=["p1"]))
        combined_in = [
            make_item(9, doc_type="adr", status="accepted", tags=["t"],
                      vault_scope="local", origin_project_id="p1"),
            make_item(8, doc_type="adr", status="rejected", tags=["t"],
                      vault_scope="local", origin_project_id="p1"),
        ]
        snapshot = [x.source_id for x in combined_in]
        comb = apply_filters(
            combined_in,
            EnrichmentFilters(doc_types=["adr"], statuses_allowed=["accepted"],
                              tags_required=["t"], project_ids=["p1"]),
        )
        not_mutated = [x.source_id for x in combined_in] == snapshot
        return f"proj={ids(proj)}\ncombined={ids(comb)}\nnot_mutated={not_mutated}"

    # ------------------------- PRESENTER ----------------------------------
    def s09():
        ctx = EnrichedContext(
            work=WorkContext(source="manual"),
            items=make_bundle_items(),
            total_searches=3, total_raw_hits=9, total_items=3,
            total_chars=bundle_total_chars(),
            within_budget=True,
        )
        empty = EnrichedContext(work=WorkContext(source="manual"), items=[],
                                total_searches=1, total_raw_hits=0,
                                total_items=0, total_chars=0, within_budget=True)
        return (
            ContextPresenter.to_markdown(ctx) + "\n@@@\n" +
            ContextPresenter.to_markdown(empty))

    def s10():
        ctx = EnrichedContext(
            work=WorkContext(source="manual"),
            items=make_bundle_items(),
            total_searches=3, total_raw_hits=9, total_items=3,
            total_chars=bundle_total_chars(),
            within_budget=True,
        )
        empty = EnrichedContext(work=WorkContext(source="manual"), items=[],
                                total_searches=1, total_raw_hits=0,
                                total_items=0, total_chars=0, within_budget=True)
        return (
            ContextPresenter.to_compact(ctx) + "\n@@@\n" +
            ContextPresenter.to_compact(empty))

    def s11():
        ctx = EnrichedContext(
            work=WorkContext(source="manual"),
            items=make_bundle_items(),
            total_searches=3, total_raw_hits=9, total_items=3,
            total_chars=bundle_total_chars(),
            within_budget=True,
        )
        empty = EnrichedContext(work=WorkContext(source="manual"), items=[],
                                total_searches=1, total_raw_hits=0,
                                total_items=0, total_chars=0, within_budget=False)
        return (
            ContextPresenter.to_json(ctx) + "\n@@@\n" +
            ContextPresenter.to_json(empty))

    def s12():
        ctx = EnrichedContext(
            work=WorkContext(source="manual"),
            items=make_bundle_items(),
            total_searches=3, total_raw_hits=9, total_items=3,
            total_chars=bundle_total_chars(),
            within_budget=True,
        )
        empty = EnrichedContext(work=WorkContext(source="manual"), items=[],
                                total_searches=1, total_raw_hits=0,
                                total_items=0, total_chars=0, within_budget=True)
        return (
            ContextPresenter.to_markdown_grouped(ctx) + "\n@@@\n" +
            ContextPresenter.to_compact_grouped(ctx) + "\n@@@\n" +
            ContextPresenter.to_markdown_grouped(empty))

    # ------------------------- DOMAIN DETECTOR ----------------------------
    def detector_lines(d: DomainDetector, cases):
        lines = []
        for files, kws in cases:
            r = d.detect(list(files), list(kws))
            lines.append(
                f"{list(files)}|{list(kws)} -> domain={r.domain} "
                f"conf={round(r.confidence, 6)} method={r.method_used} "
                f"mf={r.matched_files} mk={r.matched_keywords}")
        return "\n".join(lines)

    def s13():
        d = DomainDetector()
        return detector_lines(d, [
            (["auth.py", "jwt.ts", "tests/test_auth.py"], []),
            ([], ["token", "refresh", "expiry", "authentication"]),
            (["auth.py", "jwt.ts"], ["token", "refresh", "login"]),
            (["migrations/001_initial.sql", "schema.py"], []),
        ])

    def s14():
        d = DomainDetector()
        return detector_lines(d, [
            (["routes/api.py", "controllers/user_controller.ts"],
             ["endpoint", "handler", "request", "response"]),
            (["payments/stripe.py", "billing/invoice.ts"],
             ["payment", "charge", "subscription"]),
            (["auth.py", "other.py"], []),
            ([], ["token", "other"]),
        ])

    def s15():
        d_default = DomainDetector()
        d_high = DomainDetector(min_confidence=0.9)
        d_low = DomainDetector(min_confidence=0.1)
        lines = [detector_lines(d_default, [(["utils.py", "helpers.js", "README.md"], []),
                                            ([], ["token"])])]
        r_high = d_high.detect(["auth.py"], ["token"])
        lines.append(f"high: domain={r_high.domain} method={r_high.method_used}")
        r_low = d_low.detect(["auth.py"], ["token"])
        lines.append(f"low: domain={r_low.domain} conf={round(r_low.confidence, 6)}")
        r_empty = d_default.detect([], [])
        lines.append(
            f"empty: domain={r_empty.domain} conf={r_empty.confidence} method={r_empty.method_used}")
        return "\n".join(lines)

    # ------------------------- OBSERVER -----------------------------------
    def s16():
        obs = ContextObserver()
        wc = obs.observe_from_files(["src/auth.py", "src/db.py"])
        wc2 = obs.observe_from_files(
            ["src/x.py"], keywords=["cache", "redis"],
            function_names=["get_cache"], pr_title="Add cache layer",
            pr_body="", pr_labels=["perf"])
        return "\n".join([
            f"source={wc.source}",
            f"changed={wc.changed_files}",
            f"new={wc.new_files}",
            f"deleted={wc.deleted_files}",
            f"domain={wc.detected_domain} conf={round(wc.domain_confidence, 6)}",
            f"queries={wc.search_queries}",
            f"pr_title={wc2.pr_title}",
            f"labels={wc2.pr_labels}",
            f"funcs={wc2.function_names}",
        ])

    def s17():
        obs = ContextObserver()
        pr = SimpleNamespace(
            files_changed=["services/token_service.py"],
            title="Fix auth token refresh",
            body="Refresh tokens expire early. The login flow breaks.",
            labels=["backend", "auth"])
        wc = obs.observe_from_pr(pr)
        return "\n".join([
            f"source={wc.source}",
            f"changed={wc.changed_files}",
            f"keywords={wc.keywords}",
            f"pr_labels={wc.pr_labels}",
            f"queries={wc.search_queries}",
            f"domain={wc.detected_domain} conf={round(wc.domain_confidence, 6)}",
        ])

    def s18():
        code = SAMPLE_CODE
        return "\n".join([
            f"imports={ContextObserver._extract_imports(code)}",
            f"functions={ContextObserver._extract_functions(code)}",
            f"classes={ContextObserver._extract_classes(code)}",
            f"text_kw={ContextObserver._extract_text_keywords('Fixing the authentication flow with refresh tokens')}",
        ])

    def self_code():
        return type(self_sample)()

    def s19():
        import os

        repo = root / "gitrepo"
        if repo.exists():
            shutil.rmtree(repo)
        repo.mkdir(parents=True)
        env_cmds = [
            ["git", "init", "-q", "-b", "main", "."],
            ["git", "config", "user.email", "t@t.io"],
            ["git", "config", "user.name", "T"],
        ]
        for c in env_cmds:
            subprocess.run(c, cwd=repo, check=True, capture_output=True)
        (repo / "mod_base.py").write_text("value = 1\n", encoding="utf-8")
        (repo / "old_feature.py").write_text("legacy = True\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-qm", "init"], cwd=repo, check=True,
                       capture_output=True)
        # cambios: modificar, borrar, nuevo untracked, nuevo staged
        (repo / "mod_base.py").write_text("value = 2\n", encoding="utf-8")
        (repo / "old_feature.py").unlink()
        (repo / "auth_login.py").write_text("token = 'x'\n", encoding="utf-8")
        (repo / "utils_new.py").write_text("helper()\n", encoding="utf-8")
        subprocess.run(["git", "add", "auth_login.py"], cwd=repo, check=True,
                       capture_output=True)

        prev_cwd = os.getcwd()
        os.chdir(repo)
        try:
            obs = ContextObserver()
            wc = obs.observe_from_git("main")
        finally:
            os.chdir(prev_cwd)
        return "\n".join([
            f"source={wc.source}",
            f"changed={sorted(wc.changed_files)}",
            f"new={sorted(wc.new_files)}",
            f"deleted={sorted(wc.deleted_files)}",
            f"imports={wc.imports}",
            f"domain={wc.detected_domain} conf={round(wc.domain_confidence, 6)}",
            f"n_queries={len(wc.search_queries)}",
        ])

    # ------------------------- TELEMETRY ----------------------------------
    def s20():
        p = root / "t20" / "events.jsonl"
        obs = PersistentObserver(p, enabled=False)
        ctx = _ctx_for_telemetry(2)
        rid = obs.record_enrichment(ctx)
        return f"run={rid!r}\nexists={p.exists()}"

    def s21():
        p = root / "t21" / "sub" / "events.jsonl"
        obs = PersistentObserver(p)
        ctx = _ctx_for_telemetry(2)
        run = obs.record_enrichment(ctx, latency_ms=120)
        obs.record_citation(run, "item-0")
        line1, line2 = p.read_text(encoding="utf-8").strip().split("\n")
        e1, e2 = json.loads(line1), json.loads(line2)
        return "\n".join([
            f"len_run={len(run)}",
            f"e1_keys={sorted(e1.keys())}",
            f"e1_offered={json.dumps(e1['items_offered'], sort_keys=True)}",
            f"e1_latency={e1['latency_ms']}",
            f"e1_totals={e1['total_searches']},{e1['total_raw_hits']},{e1['total_items']},{e1['total_chars']},{e1['within_budget']}",
            f"e2={e2['event_type']},{e2['source_id']},run_match={e2['run_id'] == run}",
        ])

    def s22():
        p = root / "t22" / "events.jsonl"
        obs = PersistentObserver(p, enabled=False)
        obs.record_citation("runid123", "item-0")
        obs2 = PersistentObserver(root / "t22b" / "events.jsonl")
        obs2.record_citation("", "item-0")
        return f"no_file={(not p.exists()) and (not (root / 't22b' / 'events.jsonl').exists())}"

    def s23():
        d = root / "t23"
        d.mkdir(parents=True, exist_ok=True)
        obs = PersistentObserver(d / "missing.jsonl")
        empty_events = obs.iter_events()
        f = d / "malformed.jsonl"
        good = ('{"event_type": "citation", "run_id": "abc123def456", '
                '"timestamp": "2026-06-01T00:00:00+00:00", "source_id": "x"}')
        f.write_text(good + "\n{{BROKEN\n\n" + good + "\n", encoding="utf-8")
        obs2 = PersistentObserver(f)
        evs = obs2.iter_events()
        return f"missing={empty_events}\ncount={len(evs)}"

    def s24():
        p = root / "t24" / "events.jsonl"
        p.parent.mkdir(parents=True, exist_ok=True)
        now_iso = datetime.now(UTC).isoformat()
        p.write_text(
            json.dumps({"event_type": "enrichment", "run_id": "runA", "timestamp": now_iso,
                        "latency_ms": 100, "total_searches": 2, "total_raw_hits": 5,
                        "total_items": 2, "total_chars": 200, "within_budget": True,
                        "items_offered": [
                            {"source_id": "i1", "source": "episodic", "score": 0.5,
                             "enriched_score": 0.6, "matched_by": ["topic_search"],
                             "tags": [], "files_mentioned": []},
                            {"source_id": "i2", "source": "semantic", "score": 0.4,
                             "enriched_score": 0.55, "matched_by": ["files_search"],
                             "tags": [], "files_mentioned": []}]}) + "\n" +
            json.dumps({"event_type": "citation", "run_id": "runA", "timestamp": now_iso,
                        "source_id": "i2"}) + "\n" +
            json.dumps({"event_type": "citation", "run_id": "runB", "timestamp": now_iso,
                        "source_id": "zz"}) + "\n",
            encoding="utf-8")
        obs = PersistentObserver(p)
        grouped = obs.events_for_run("runA")
        return json.dumps(grouped, sort_keys=False)

    def s25():
        p = root / "t25" / "events.jsonl"
        p.parent.mkdir(parents=True, exist_ok=True)
        now = datetime.now(UTC)
        lines = []
        lats = [100, 200, 300, 400, 500]
        ages = [0, 1, 2, 3, 40]
        for i, (lat, age) in enumerate(zip(lats, ages)):
            lines.append(json.dumps({
                "event_type": "enrichment", "run_id": f"r{i}",
                "timestamp": (now - timedelta(days=age)).isoformat(),
                "latency_ms": lat, "total_searches": 1, "total_raw_hits": 2,
                "total_items": 1, "total_chars": 100, "within_budget": True,
                "items_offered": [
                    {"source_id": f"s{i}", "source": "episodic", "score": 0.5,
                     "enriched_score": 0.6, "matched_by": ["topic_search"],
                     "tags": [], "files_mentioned": []},
                    {"source_id": f"s{i}", "source": "episodic", "score": 0.5,
                     "enriched_score": 0.6, "matched_by": ["files_search"],
                     "tags": [], "files_mentioned": []},
                ]}))
        # citas: sólo r1 usa su ítem; evento viejo (r4) fuera de ventana 7d
        lines.append(json.dumps({"event_type": "citation", "run_id": "r1",
                                 "timestamp": now.isoformat(), "source_id": "s1"}))
        p.write_text("\n".join(lines) + "\n", encoding="utf-8")
        obs = PersistentObserver(p)
        agg_all = obs.aggregate()
        agg_win = obs.aggregate(since_days=7)
        return (f"all={json.dumps(_agg_stable(agg_all))}\n"
                f"win={json.dumps(_agg_stable(agg_win))}")

    def _agg_stable(a):
        return {
            "window_days": a["window_days"], "enrichments": a["enrichments"],
            "citations": a["citations"], "items_offered": a["items_offered"],
            "items_used": a["items_used"],
            "hit_rate": round(a["hit_rate"], 6),
            "by_strategy": {k: {"offered": v["offered"], "used": v["used"],
                                "hit_rate": round(v["hit_rate"], 6)}
                            for k, v in a["by_strategy"].items()},
            "latency": {k: round(v, 6) for k, v in a["latency"].items()},
        }

    def s26():
        offered = [
            {"source_id": "decisions/ADR-007.md"},
            {"source_id": "sessions/2026_note"},
            {"source_id": "glossary/term.md"},
        ]
        body_wiki_full = "ver [[decisions/ADR-007]]"
        body_wiki_stem = "[[ADR-007]] ok [[2026_note]]"
        body_md = "[texto](glossary/term.md)"
        body_alias = "[[term|alias]] y [[ADR-007#sección]]"
        return "\n".join([
            f"wiki_full={detect_citations(body_wiki_full, offered)}",
            f"wiki_stem={detect_citations(body_wiki_stem, offered)}",
            f"md_link={detect_citations(body_md, offered)}",
            f"alias={detect_citations(body_alias, offered)}",
            f"empty_body={detect_citations('', offered)}",
            f"no_offered={detect_citations('[[x]]', [])}",
            f"no_match={detect_citations('[[nope]]', offered)}",
            f"dedup={detect_citations('[[ADR-007]] otra vez [[decisions/ADR-007]]', offered)}",
        ])

    def s27():
        ws = root / "ws27"
        default_obs = make_observer(project_root=ws)
        off_obs = make_observer(project_root=ws, enabled=False)
        cfg_obs = make_observer(
            project_root=ws,
            config={"retrieval": {"telemetry": {"enabled": True,
                                                "path": "custom/events.jsonl"}}})
        cfg_disabled = make_observer(
            project_root=ws,
            config={"retrieval": {"telemetry": {"enabled": False}}},
            enabled=True)
        layout = SimpleNamespace(workspace_root=ws / "alt")
        layout_obs = make_observer(layout)
        return "\n".join([
            f"default={default_obs.path.name} enabled={default_obs.enabled}",
            f"off_enabled={off_obs.enabled}",
            f"cfg={cfg_obs.path.relative_to(ws)} enabled={cfg_obs.enabled}",
            f"override={cfg_disabled.path.name} enabled={cfg_disabled.enabled}",
            f"layout={layout_obs.path.relative_to(root)}",
        ])

    for name, fn in [
        ("S01 filters noop", s01),
        ("S02 doc_types strict", s02),
        ("S03 exclude_doc_types", s03),
        ("S04 statuses", s04),
        ("S05 tags AND/OR/exclude", s05),
        ("S06 vault_scope", s06),
        ("S07 max_age ventana", s07b),
        ("S08 project_ids + combined", s08),
        ("S09 markdown", s09),
        ("S10 compact", s10),
        ("S11 json", s11),
        ("S12 grouped", s12),
        ("S13 dominio auth/db", s13),
        ("S14 dominio api/payments/matched", s14),
        ("S15 umbrales y embedding", s15),
        ("S16 observe_from_files", s16),
        ("S17 observe_from_pr", s17),
        ("S18 extractores", s18),
        ("S19 observe_from_git", s19),
        ("S20 observer disabled", s20),
        ("S21 record enrichment+citation", s21),
        ("S22 citation noop", s22),
        ("S23 iter malformed/missing", s23),
        ("S24 events_for_run", s24),
        ("S25 aggregate", s25),
        ("S26 detect_citations", s26),
        ("S27 make_observer", s27),
    ]:
        emit(name, fn)

    return normalize("\n".join(blocks), root)


def _ctx_for_telemetry(n: int) -> EnrichedContext:
    work = WorkContext(source="manual", changed_files=[], keywords=[], search_queries=[])
    items = [
        make_item(i, matched_by=["topic_search"], tags=["test"])
        for i in range(n)
    ]
    return EnrichedContext(
        work=work, items=items, total_searches=1, total_raw_hits=n,
        total_items=n, total_chars=n * 100, within_budget=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["build", "verify"])
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    golden = out_dir / "golden_p12a7.txt"

    tmp = Path(tempfile.mkdtemp(prefix="p12a7_oracle_"))
    try:
        # Cada corrida en subdirectorio fresco: los escenarios escriben
        # archivos y el estado previo rompería la 2ª medición.
        first = build_report(tmp / "run1")
        second = build_report(tmp / "run2")
        if first != second:
            print("❌ ORÁCULO NO DETERMINISTA")
            import difflib

            for line in difflib.unified_diff(
                first.splitlines(), second.splitlines(), "1ª", "2ª", lineterm=""
            ):
                print(line)
            return 1
        print("✅ ORÁCULO DETERMINISTA")
        if args.command == "build":
            golden.write_text(first, encoding="utf-8")
            print(f"[OK] escrito {golden}")
            return 0
        expected = golden.read_text(encoding="utf-8")
        if first == expected:
            print("[PASS] golden_p12a7.txt")
            return 0
        print("[FAIL]")
        import difflib

        for line in difflib.unified_diff(
            expected.splitlines(), first.splitlines(), "py-guardado", "py-rerun",
            lineterm=""
        ):
            print(line)
        return 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())

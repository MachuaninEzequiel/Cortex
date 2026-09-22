#!/usr/bin/env python3
"""
Cortex BlackBox Probe - Metrics Analysis Engine
===============================================
Motor analítico que procesa los eventos brutos de MCP y Git recolectados durante
la semana, generando estadísticas científicas equivalentes a las del reporte ConaISI:
- Latencias p50/p90/p99 de herramientas MCP.
- Curva de acumulación y volumen de tokens de contexto.
- Ratio de distractores y ruido cognitivo.
- Tasa de cumplimiento de ADRs vs Deriva arquitectónica.
- Cumplimiento del ciclo Sandwich (Top, Middle, Bottom).
"""

from __future__ import annotations

import json
import math
import statistics
import time
from pathlib import Path
from typing import Any, Dict, List

PROBE_DIR = Path(__file__).resolve().parent
DATA_DIR = PROBE_DIR / "data"
MCP_EVENTS_FILE = DATA_DIR / "mcp_events.jsonl"
GIT_EVENTS_FILE = DATA_DIR / "git_events.jsonl"
SUMMARY_FILE = DATA_DIR / "telemetry_summary.json"


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    records = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except Exception:
                    pass
    return records


def calculate_percentiles(values: List[float]) -> Dict[str, float]:
    if not values:
        return {"min": 0.0, "p50": 0.0, "p90": 0.0, "p99": 0.0, "max": 0.0, "mean": 0.0}
    s = sorted(values)
    n = len(s)
    def p(pct: float) -> float:
        k = (n - 1) * (pct / 100.0)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return s[int(k)]
        d0 = s[int(f)] * (c - k)
        d1 = s[int(c)] * (k - f)
        return round(d0 + d1, 2)

    return {
        "min": round(s[0], 2),
        "p50": p(50),
        "p90": p(90),
        "p99": p(99),
        "max": round(s[-1], 2),
        "mean": round(statistics.mean(values), 2)
    }


def analyze_mcp_events(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not events:
        return {"total_calls": 0, "by_tool": {}, "latency_ms": {}, "tokens": {}}

    tool_counts: Dict[str, int] = {}
    tool_latencies: Dict[str, List[float]] = {}
    all_latencies: List[float] = []

    total_context_tokens = 0
    total_payload_chars = 0
    total_docs_returned = 0
    errors_count = 0

    all_returned_docs = set()

    for ev in events:
        t = ev.get("tool", "unknown")
        dur = ev.get("duration_ms", 0.0)
        tok = ev.get("context_tokens_est", 0)
        chars = ev.get("payload_chars", 0)
        docs_count = ev.get("docs_returned_count", 0)
        docs_sample = ev.get("docs_sample", [])

        tool_counts[t] = tool_counts.get(t, 0) + 1
        tool_latencies.setdefault(t, []).append(dur)
        all_latencies.append(dur)

        total_context_tokens += tok
        total_payload_chars += chars
        total_docs_returned += docs_count

        for d in docs_sample:
            all_returned_docs.add(d)

        if not ev.get("success", True):
            errors_count += 1

    by_tool_stats = {}
    for t, lats in tool_latencies.items():
        by_tool_stats[t] = {
            "calls": len(lats),
            "pct_of_total": round((len(lats) / len(events)) * 100.0, 1),
            "latency": calculate_percentiles(lats)
        }

    return {
        "total_calls": len(events),
        "error_rate_pct": round((errors_count / len(events)) * 100.0, 2),
        "latency_global_ms": calculate_percentiles(all_latencies),
        "by_tool": by_tool_stats,
        "tokens": {
            "total_context_tokens_est": total_context_tokens,
            "avg_tokens_per_call": round(total_context_tokens / len(events), 1) if events else 0,
            "total_payload_chars": total_payload_chars,
            "total_docs_returned": total_docs_returned,
            "unique_docs_cited": len(all_returned_docs)
        }
    }


def analyze_git_events(events: List[Dict[str, Any]], mcp_stats: Dict[str, Any]) -> Dict[str, Any]:
    if not events:
        return {"total_commits": 0, "by_condition": {}, "adr_compliance": {}}

    cortex_count = 0
    raw_count = 0
    arch_commits = 0
    compliant_commits = 0
    drift_commits = 0

    touched_files_set = set()

    for ev in events:
        cond = ev.get("condition", "raw_unassisted")
        if cond == "cortex_assisted":
            cortex_count += 1
        else:
            raw_count += 1

        for f in ev.get("files_sample", []):
            touched_files_set.add(f)

        adr = ev.get("adr_compliance", {})
        if adr.get("touches_architecture", False):
            arch_commits += 1
            if adr.get("compliant", True):
                compliant_commits += 1
            else:
                drift_commits += 1

    # Ratio de distractores: documentos citados por Cortex vs archivos realmente tocados
    unique_cited = mcp_stats.get("tokens", {}).get("unique_docs_cited", 0)
    distractor_pct = 0.0
    if unique_cited > 0:
        # Documentos que fueron entregados en contexto pero nunca fueron modificados
        distractor_pct = round(max(0.0, (1.0 - (len(touched_files_set) / max(1, unique_cited)))) * 100.0, 1)

    compliance_rate_pct = round((compliant_commits / arch_commits) * 100.0, 1) if arch_commits > 0 else 100.0

    return {
        "total_commits": len(events),
        "by_condition": {
            "cortex_assisted": cortex_count,
            "raw_unassisted": raw_count,
            "cortex_usage_pct": round((cortex_count / len(events)) * 100.0, 1)
        },
        "adr_compliance": {
            "architectural_commits": arch_commits,
            "compliant_commits": compliant_commits,
            "drift_commits": drift_commits,
            "compliance_rate_pct": compliance_rate_pct,
            "drift_rate_pct": round(100.0 - compliance_rate_pct, 1)
        },
        "distractor_ratio_est_pct": distractor_pct,
        "unique_files_touched": len(touched_files_set)
    }


def generate_metrics_summary() -> Dict[str, Any]:
    mcp_events = load_jsonl(MCP_EVENTS_FILE)
    git_events = load_jsonl(GIT_EVENTS_FILE)

    mcp_analysis = analyze_mcp_events(mcp_events)
    git_analysis = analyze_git_events(git_events, mcp_analysis)

    # Identificar timestamps de inicio y fin
    all_timestamps = [e.get("timestamp", 0) for e in mcp_events + git_events if e.get("timestamp")]
    start_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(min(all_timestamps))) if all_timestamps else "N/A"
    end_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(max(all_timestamps))) if all_timestamps else "N/A"

    summary = {
        "probe_version": "1.0.0",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "period": {
            "start": start_iso,
            "end": end_iso,
            "total_events": len(mcp_events) + len(git_events)
        },
        "mcp_telemetry": mcp_analysis,
        "git_and_drift_telemetry": git_analysis
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    return summary


if __name__ == "__main__":
    s = generate_metrics_summary()
    print("Resumen de telemetría calculado exitosamente.")
    print(f"Total llamadas MCP: {s['mcp_telemetry']['total_calls']}")
    print(f"Total commits Git: {s['git_and_drift_telemetry']['total_commits']}")

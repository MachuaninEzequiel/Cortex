#!/usr/bin/env python3
"""
Cortex BlackBox Probe - Export & Packaging Utility
==================================================
Ejecuta la consolidación de métricas, redacta un reporte ejecutivo en Markdown
y genera un archivo ZIP sellado listo para enviar al equipo de investigación.
"""

from __future__ import annotations

import json
import shutil
import sys
import time
import zipfile
from pathlib import Path

PROBE_DIR = Path(__file__).resolve().parent
DATA_DIR = PROBE_DIR / "data"
REPORT_MD_FILE = PROBE_DIR / "telemetry_weekly_report.md"

# Importar motor de métricas
sys.path.insert(0, str(PROBE_DIR))
from metrics_engine import generate_metrics_summary


def generate_markdown_report(summary: dict) -> str:
    mcp = summary.get("mcp_telemetry", {})
    git = summary.get("git_and_drift_telemetry", {})
    period = summary.get("period", {})

    lat = mcp.get("latency_global_ms", {})
    tok = mcp.get("tokens", {})
    by_tool = mcp.get("by_tool", {})
    cond = git.get("by_condition", {})
    adr = git.get("adr_compliance", {})

    md = f"""# 📊 Reporte Semanal de Telemetría Cortex

- **Generado:** {summary.get('generated_at', 'N/A')}
- **Período Registrado:** {period.get('start', 'N/A')} ➔ {period.get('end', 'N/A')}
- **Eventos Totales Analizados:** {period.get('total_events', 0)} ({mcp.get('total_calls', 0)} llamadas MCP, {git.get('total_commits', 0)} commits)

---

## 1. Rendimiento del Servidor MCP y Latencias

- **Llamadas Totales:** {mcp.get('total_calls', 0)}
- **Tasa de Errores:** {mcp.get('error_rate_pct', 0.0)}%
- **Latencia Global (ms):**
  - **Mínima:** {lat.get('min', 0.0)} ms
  - **Mediana (p50):** {lat.get('p50', 0.0)} ms
  - **Percentil 90 (p90):** {lat.get('p90', 0.0)} ms
  - **Percentil 99 (p99):** {lat.get('p99', 0.0)} ms
  - **Máxima:** {lat.get('max', 0.0)} ms

### Desglose por Herramienta
| Herramienta | Invocaciones | % del Total | p50 (ms) | p90 (ms) |
| :--- | :--- | :--- | :--- | :--- |
"""
    for tool_name, t_stat in sorted(by_tool.items(), key=lambda x: x[1]['calls'], reverse=True):
        t_lat = t_stat.get("latency", {})
        md += f"| `{tool_name}` | {t_stat.get('calls')} | {t_stat.get('pct_of_total')}% | {t_lat.get('p50')} ms | {t_lat.get('p90')} ms |\n"

    md += f"""
---

## 2. Volumen de Contexto y Ruido Cognitivo

- **Tokens de Contexto Inyectados (Est.):** {tok.get('total_context_tokens_est', 0):,} tokens
- **Promedio de Tokens por Consulta:** {tok.get('avg_tokens_per_call', 0):,} tokens
- **Documentos/Fragmentos Recuperados:** {tok.get('total_docs_returned', 0)}
- **Documentos Únicos Citados:** {tok.get('unique_docs_cited', 0)}
- **Ratio Estimado de Distractores / Ruido:** {git.get('distractor_ratio_est_pct', 0.0)}% *(Documentos inyectados pero nunca modificados en commits posteriores)*

---

## 3. Actividad Git y Cumplimiento de ADRs

- **Total de Commits Realizados:** {git.get('total_commits', 0)}
- **Condición de Trabajo:**
  - **Asistido por Cortex:** {cond.get('cortex_assisted', 0)} ({cond.get('cortex_usage_pct', 0.0)}%)
  - **Sin Cortex (RAW):** {cond.get('raw_unassisted', 0)}
- **Gobernanza Arquitectónica (ADRs):**
  - **Commits con impacto en arquitectura:** {adr.get('architectural_commits', 0)}
  - **Cumplimiento estricto de ADRs:** {adr.get('compliant_commits', 0)} ({adr.get('compliance_rate_pct', 100.0)}%)
  - **Deriva Arquitectónica (*Drift*):** {adr.get('drift_commits', 0)} ({adr.get('drift_rate_pct', 0.0)}%)

---
*Reporte generado automáticamente por Cortex BlackBox Probe v1.0.0*
"""
    return md


def main():
    print("=====================================================")
    print("📦 Cortex BlackBox Probe - Generando Exportación...")
    print("=====================================================")

    # 1. Compilar métricas
    summary = generate_metrics_summary()

    # 2. Generar reporte Markdown
    report_md = generate_markdown_report(summary)
    with open(REPORT_MD_FILE, "w", encoding="utf-8") as f:
        f.write(report_md)

    # 3. Crear archivo ZIP
    timestamp_str = time.strftime("%Y%m%d_%H%M%S")
    env_label = summary.get("mcp_telemetry", {}).get("environment", "telemetry")
    zip_name = f"cortex_telemetry_{timestamp_str}.zip"
    zip_path = PROBE_DIR / zip_name

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        if (DATA_DIR / "telemetry_summary.json").exists():
            zf.write(DATA_DIR / "telemetry_summary.json", arcname="telemetry_summary.json")
        if REPORT_MD_FILE.exists():
            zf.write(REPORT_MD_FILE, arcname="telemetry_weekly_report.md")
        if (DATA_DIR / "mcp_events.jsonl").exists():
            zf.write(DATA_DIR / "mcp_events.jsonl", arcname="data/mcp_events.jsonl")
        if (DATA_DIR / "git_events.jsonl").exists():
            zf.write(DATA_DIR / "git_events.jsonl", arcname="data/git_events.jsonl")
        if (PROBE_DIR / "config.json").exists():
            zf.write(PROBE_DIR / "config.json", arcname="config.json")

    print("\n✅ Resumen de Métricas Generado:")
    print(f"   - Llamadas MCP capturadas: {summary['mcp_telemetry']['total_calls']}")
    print(f"   - Tokens de contexto estimados: {summary['mcp_telemetry']['tokens']['total_context_tokens_est']:,}")
    print(f"   - Latencia mediana (p50): {summary['mcp_telemetry']['latency_global_ms']['p50']} ms")
    print(f"   - Commits registrados: {summary['git_and_drift_telemetry']['total_commits']}")
    print(f"   - Tasa de cumplimiento ADR: {summary['git_and_drift_telemetry']['adr_compliance']['compliance_rate_pct']}%")

    print("\n📦 Paquete ZIP sellado:")
    print(f"   -> {zip_path.resolve()}")
    print("\n👉 Este archivo ZIP es el que debes entregar para la comparación.")
    print("=====================================================")


if __name__ == "__main__":
    main()

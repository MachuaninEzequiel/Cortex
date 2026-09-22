#!/usr/bin/env python3
"""Generador de figuras académicas para el experimento Tripartito de 18 Turnos (ConaISI 2026).

Lee `experiments/data/tripartite_18turns_metrics.json` y genera:
  1. fig6_tripartite_18turn_token_trajectory.png (Curva de 3 vías de acumulación)
  2. fig7_cognitive_thinking_waste_tripartite.png (Desperdicio de tokens de razonamiento)
  3. fig8_adr_compliance_and_drift.png (Cumplimiento de diseño y tasa de deriva)
  4. table3_tripartite_18turn_summary.md & .tex (Tablas formales de 18 turnos)
"""

from __future__ import annotations

import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

DATA_PATH = Path("/home/chucho/Cortex/experiments/data/tripartite_18turns_metrics.json")
OUT_DIR = Path("/home/chucho/Cortex/experiments/figures")
TABLES_DIR = Path("/home/chucho/Cortex/experiments/data")

def load_data():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def generate_tripartite_charts():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    metrics = load_data()

    raw_m = [m for m in metrics if m["condition"] == "raw"]
    base_m = [m for m in metrics if m["condition"] == "baseline"]
    jev_m = [m for m in metrics if m["condition"] == "jev"]

    turns = [m["turn_id"] for m in raw_m]
    names = [m["turn_name"] for m in raw_m]

    cum_raw = [m["cumulative_tokens"] for m in raw_m]
    cum_base = [m["cumulative_tokens"] for m in base_m]
    cum_jev = [m["cumulative_tokens"] for m in jev_m]

    th_raw = [m["thinking_tokens_est"] for m in raw_m]
    th_base = [m["thinking_tokens_est"] for m in base_m]
    th_jev = [m["thinking_tokens_est"] for m in jev_m]

    plt.rcParams.update({
        "font.family": "serif",
        "font.size": 11,
        "axes.labelsize": 12,
        "axes.titlesize": 13,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "figure.dpi": 300,
    })

    # -------------------------------------------------------------
    # Gráfico 6: Trayectoria de Acumulación Tripartita (18 Turnos)
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(10, 6))

    ax.plot(turns, cum_raw, marker="^", linewidth=2.4, color="#7F8C8D", linestyle="--", label="RAW (Sin Cortex - Amnesia + Sin compactación)")
    ax.plot(turns, cum_base, marker="o", linewidth=2.4, color="#E74C3C", label="Cortex Baseline (BM25 Directo - Sin JEV)")
    ax.plot(turns, cum_jev, marker="s", linewidth=2.6, color="#27AE60", label="Cortex + JEV (JevDD - Gating + Compaction + Pack v2)")

    ax.fill_between(turns, cum_jev, cum_raw, color="#2ECC71", alpha=0.15, label="Ahorro Neto vs. Raw Agent")

    ax.set_xlabel("Turnos Consecutivos en la Sesión Prolongada")
    ax.set_ylabel("Tokens Acumulados en la Ventana de Contexto")
    ax.set_title("Dinámica Temporal de Contexto: Comparativa Tripartita en 18 Turnos")
    ax.set_xticks(turns)
    ax.legend(loc="upper left", frameon=True)
    ax.grid(True, linestyle="--", alpha=0.5)

    # Anotaciones de divergencia final
    final_raw = cum_raw[-1]
    final_jev = cum_jev[-1]
    saved_tokens = final_raw - final_jev
    saved_pct = (saved_tokens / final_raw) * 100.0

    ax.annotate(f"JEV vs RAW: -{saved_pct:.1f}%\n({saved_tokens:,} tokens ahorrados)",
                xy=(turns[-1], final_jev),
                xytext=(-140, 50),
                textcoords="offset points",
                arrowprops=dict(arrowstyle="->", color="#1E8449", lw=1.6),
                fontsize=9.5, fontweight="bold", color="#1E8449",
                bbox=dict(boxstyle="round,pad=0.4", fc="white", ec="#27AE60", lw=1.2))

    plt.tight_layout()
    fig6_path = OUT_DIR / "fig6_tripartite_18turn_token_trajectory.png"
    plt.savefig(fig6_path)
    plt.close()
    print(f"✓ Gráfico 6 guardado en {fig6_path}")

    # -------------------------------------------------------------
    # Gráfico 7: Desperdicio Cognitivo y Vueltas de Pensamiento
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(9, 5.5))

    total_th_raw = sum(th_raw)
    total_th_base = sum(th_base)
    total_th_jev = sum(th_jev)

    labels = ["RAW (Sin Cortex)", "Cortex Baseline", "Cortex + JEV (JevDD)"]
    totals = [total_th_raw, total_th_base, total_th_jev]
    colors = ["#95A5A6", "#E67E22", "#2980B9"]

    bars = ax.bar(labels, totals, color=colors, width=0.55, edgecolor="#2C3E50", linewidth=1.2)
    ax.set_ylabel("Total de Tokens de Razonamiento (Thinking Tokens)")
    ax.set_title("Sobrecarga de Razonamiento Acumulada a lo Largo de 18 Turnos")
    ax.grid(axis="y", linestyle="--", alpha=0.5)

    for bar in bars:
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2.0, yval + 50, f"{int(yval):,} tok", ha="center", va="bottom", fontweight="bold", fontsize=10)

    # Anotar reducción de thinking
    th_diff_pct = ((total_th_base - total_th_jev) / total_th_base) * 100.0
    ax.text(2, total_th_jev / 2, f"-{th_diff_pct:.1f}% esfuerzo\ncognitivo", ha="center", color="white", fontweight="bold", fontsize=10)

    plt.tight_layout()
    fig7_path = OUT_DIR / "fig7_cognitive_thinking_waste_tripartite.png"
    plt.savefig(fig7_path)
    plt.close()
    print(f"✓ Gráfico 7 guardado en {fig7_path}")

    # -------------------------------------------------------------
    # Gráfico 8: Tasa de Cumplimiento Arquitectónico (ADRs & Specs)
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(8, 5))

    comp_raw_pct = (sum(1 for m in raw_m if m["adr_compliant"]) / len(raw_m)) * 100.0
    comp_base_pct = (sum(1 for m in base_m if m["adr_compliant"]) / len(base_m)) * 100.0
    comp_jev_pct = (sum(1 for m in jev_m if m["adr_compliant"]) / len(jev_m)) * 100.0

    rates = [comp_raw_pct, comp_base_pct, comp_jev_pct]
    bar_colors = ["#E74C3C", "#F39C12", "#27AE60"]

    bars = ax.bar(labels, rates, color=bar_colors, width=0.55, edgecolor="#1B2631", linewidth=1.2)
    ax.set_ylabel("Cumplimiento Arquitectónico (%)")
    ax.set_ylim(0, 115)
    ax.set_title("Tasa de Cumplimiento de ADRs y Specs con 'Prompts Pobres'")
    ax.grid(axis="y", linestyle="--", alpha=0.5)

    for bar in bars:
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2.0, yval + 2, f"{yval:.1f}%", ha="center", va="bottom", fontweight="bold", fontsize=10.5)

    plt.tight_layout()
    fig8_path = OUT_DIR / "fig8_adr_compliance_and_drift.png"
    plt.savefig(fig8_path)
    plt.close()
    print(f"✓ Gráfico 8 guardado en {fig8_path}")

    # -------------------------------------------------------------
    # Tabla 3: Resumen Tripartito de 18 Turnos
    # -------------------------------------------------------------
    md_t3 = """# Resumen Experimental: Benchmark Tripartito de 18 Turnos (ConaISI 2026)

| Turno | Tarea / Operación | Categoría | RAW Acum. | BASELINE Acum. | JEV Acum. | Ahorro JEV vs RAW (%) | Cumplimiento RAW | Cumplimiento JEV |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
"""
    for i in range(len(turns)):
        t_id = turns[i]
        t_name = names[i].replace("_", " ")
        cat = raw_m[i]["category"]
        c_raw = cum_raw[i]
        c_base = cum_base[i]
        c_jev = cum_jev[i]
        saved = ((c_raw - c_jev) / max(1, c_raw)) * 100.0
        comp_r = "✓" if raw_m[i]["adr_compliant"] else "❌ Deriva"
        comp_j = "✓ 100%" if jev_m[i]["adr_compliant"] else "❌"
        md_t3 += f"| **{t_id}** | {t_name} | `{cat}` | {c_raw:,} | {c_base:,} | {c_jev:,} | **{saved:.1f}%** | {comp_r} | {comp_j} |\n"

    table3_path = TABLES_DIR / "table3_tripartite_18turn_summary.md"
    table3_path.write_text(md_t3, encoding="utf-8")
    print(f"✓ Tabla 3 Markdown guardada en {table3_path}")

if __name__ == "__main__":
    generate_tripartite_charts()

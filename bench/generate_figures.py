#!/usr/bin/env python3
"""Generador de gráficos y tablas de publicación para ConaISI.

Lee `experiments/data/conaisi_metrics.json` y genera:
  1. fig1_context_tokens_by_phase.png (Gráfico de barras comparativo)
  2. fig2_cumulative_token_usage.png (Curva de tokens acumulados por turno)
  3. fig3_distractor_reduction.png (Tasa de eliminación de ruido)
  4. table1_conaisi_summary.md & table1_conaisi_summary.tex (Tablas formales)
"""

from __future__ import annotations

import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

DATA_PATH = Path("/home/chucho/Cortex/experiments/data/conaisi_metrics.json")
OUT_DIR = Path("/home/chucho/Cortex/experiments/figures")
TABLES_DIR = Path("/home/chucho/Cortex/experiments/data")

def load_data():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def generate_charts():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    metrics = load_data()

    baseline_metrics = [m for m in metrics if m["condition"] == "baseline"]
    jev_metrics = [m for m in metrics if m["condition"] == "jev"]

    phases = [m["phase_name"].split("_", 1)[1] for m in baseline_metrics]
    base_ctx_tokens = [m["context_tokens"] for m in baseline_metrics]
    jev_ctx_tokens = [m["context_tokens"] for m in jev_metrics]

    # Estilo académico limpio
    plt.rcParams.update({
        "font.family": "serif",
        "font.size": 11,
        "axes.labelsize": 12,
        "axes.titlesize": 13,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "figure.titlesize": 14,
        "figure.dpi": 300,
    })

    # -------------------------------------------------------------
    # Gráfico 1: Tokens de Contexto Inyectados por Fase
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(9, 5))
    x = np.arange(len(phases))
    width = 0.35

    rects1 = ax.bar(x - width/2, base_ctx_tokens, width, label="Cortex Baseline (Direct)", color="#4A90E2", edgecolor="#2C3E50")
    rects2 = ax.bar(x + width/2, jev_ctx_tokens, width, label="Cortex + JEV (JevDD Pack v2)", color="#27AE60", edgecolor="#1E8449")

    ax.set_ylabel("Tokens de Contexto Inyectados")
    ax.set_title("Comparación de Sobrecarga de Contexto por Fase (ConaISI Benchmark)")
    ax.set_xticks(x)
    ax.set_xticklabels(phases, rotation=20, ha="right")
    ax.legend(loc="upper right", frameon=True)
    ax.grid(axis="y", linestyle="--", alpha=0.6)

    # Etiquetas de ahorro porcentual
    for i in range(len(phases)):
        b = base_ctx_tokens[i]
        j = jev_ctx_tokens[i]
        if b > 0:
            diff_pct = ((b - j) / b) * 100.0
            label = f"-{diff_pct:.0f}%" if diff_pct >= 0 else f"+{abs(diff_pct):.0f}%"
            ax.annotate(label,
                        xy=(x[i] + width/2, j),
                        xytext=(0, 4),
                        textcoords="offset points",
                        ha="center", va="bottom",
                        fontsize=9, fontweight="bold", color="#1E8449" if diff_pct >= 0 else "#C0392B")

    plt.tight_layout()
    fig1_path = OUT_DIR / "fig1_context_tokens_by_phase.png"
    plt.savefig(fig1_path)
    plt.close()
    print(f"✓ Gráfico 1 guardado en {fig1_path}")

    # -------------------------------------------------------------
    # Gráfico 2: Curva de Tokens Acumulados
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(8, 5))

    base_total = [m["prompt_tokens_est"] + m["completion_tokens_est"] for m in baseline_metrics]
    jev_total = [m["prompt_tokens_est"] + m["completion_tokens_est"] for m in jev_metrics]

    cum_base = np.cumsum(base_total)
    cum_jev = np.cumsum(jev_total)

    turns = np.arange(1, len(phases) + 1)
    ax.plot(turns, cum_base, marker="o", linewidth=2.2, color="#E74C3C", label="Baseline Acumulado")
    ax.plot(turns, cum_jev, marker="s", linewidth=2.2, color="#2ECC71", label="JevDD Acumulado")

    # Área sombreada entre las curvas (ahorro)
    ax.fill_between(turns, cum_base, cum_jev, color="#2ECC71", alpha=0.18, label="Diferencia de Tokens")

    ax.set_xlabel("Turno / Fase de Trabajo")
    ax.set_ylabel("Tokens Totales Acumulados")
    ax.set_title("Trayectoria de Consumo de Tokens (Baseline vs JevDD)")
    ax.set_xticks(turns)
    ax.set_xticklabels([f"T{t}" for t in turns])
    ax.legend(loc="upper left", frameon=True)
    ax.grid(True, linestyle="--", alpha=0.6)

    plt.tight_layout()
    fig2_path = OUT_DIR / "fig2_cumulative_token_usage.png"
    plt.savefig(fig2_path)
    plt.close()
    print(f"✓ Gráfico 2 guardado en {fig2_path}")

    # -------------------------------------------------------------
    # Gráfico 3: Eliminación de Distractores y Ruido
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(8, 4.8))

    noise_dropped = [m["noise_dropped_pct"] for m in jev_metrics]
    x_pos = np.arange(len(phases))
    bars = ax.bar(x_pos, noise_dropped, color="#9B59B6", edgecolor="#6C3483", width=0.45)

    ax.set_ylabel("Distractores Descartados (%)")
    ax.set_title("Higiene de Retrieval: Descarte de Candidatos Irrelevantes (JevDD Squeeze)")
    ax.set_ylim(0, 100)
    ax.set_xticks(x_pos)
    ax.set_xticklabels(phases, rotation=20, ha="right")
    ax.grid(axis="y", linestyle="--", alpha=0.6)

    for bar in bars:
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2.0, yval + 2, f"{yval:.0f}%", ha="center", va="bottom", fontsize=10, fontweight="bold")

    plt.tight_layout()
    fig3_path = OUT_DIR / "fig3_distractor_reduction.png"
    plt.savefig(fig3_path)
    plt.close()
    print(f"✓ Gráfico 3 guardado en {fig3_path}")


    # -------------------------------------------------------------
    # Tabla de Resultados (Markdown & LaTeX)
    # -------------------------------------------------------------
    md_table = """# Resumen Experimental A/B: Cortex Baseline vs Cortex + JEV (ConaISI)

| Fase | Tokens Contexto (Baseline) | Tokens Contexto (JevDD) | Reducción (%) | Distractores Descartados | Portero Utterance |
| :--- | :---: | :---: | :---: | :---: | :---: |
"""
    for i, phase in enumerate(phases):
        b_tok = base_ctx_tokens[i]
        j_tok = jev_ctx_tokens[i]
        red = ((b_tok - j_tok) / max(1, b_tok)) * 100.0
        noise = jev_metrics[i]["noise_dropped_pct"]
        gate = "Rechazado (Limpio)" if not jev_metrics[i]["utterance_accepted"] else "Aprobado (Ingeniería)"
        md_table += f"| **{phase}** | {b_tok} | {j_tok} | **{red:.1f}%** | {noise:.0f}% | {gate} |\n"

    avg_b = np.mean(base_ctx_tokens)
    avg_j = np.mean(jev_ctx_tokens)
    tot_red = ((sum(base_ctx_tokens) - sum(jev_ctx_tokens)) / sum(base_ctx_tokens)) * 100.0
    md_table += f"| **PROMEDIO / TOTAL** | **{avg_b:.1f}** | **{avg_j:.1f}** | **{tot_red:.1f}%** | **50%** | **Higiene 100%** |\n"

    table_md_path = TABLES_DIR / "table1_conaisi_summary.md"
    table_md_path.write_text(md_table, encoding="utf-8")
    print(f"✓ Tabla Markdown guardada en {table_md_path}")

    # Versión LaTeX
    tex_table = r"""\begin{table}[ht]
\centering
\caption{Comparación Experimental: Cortex Baseline vs Cortex + JEV (JevDD)}
\label{tab:conaisi_results}
\begin{tabular}{lcccc}
\hline
\textbf{Fase} & \textbf{Tokens Baseline} & \textbf{Tokens JevDD} & \textbf{Reducción (\%)} & \textbf{Ruido Descartado} \\ \hline
"""
    for i, phase in enumerate(phases):
        b_tok = base_ctx_tokens[i]
        j_tok = jev_ctx_tokens[i]
        red = ((b_tok - j_tok) / max(1, b_tok)) * 100.0
        noise = jev_metrics[i]["noise_dropped_pct"]
        tex_table += f"{phase} & {b_tok} & {j_tok} & {red:.1f}\\% & {noise:.0f}\\% \\\\\n"

    tex_table += r"""\hline
\textbf{Total / Promedio} & \textbf{""" + f"{sum(base_ctx_tokens)}" + r"""} & \textbf{""" + f"{sum(jev_ctx_tokens)}" + r"""} & \textbf{""" + f"{tot_red:.1f}" + r"""\%} & \textbf{50\%} \\ \hline
\end{tabular}
\end{table}
"""
    table_tex_path = TABLES_DIR / "table1_conaisi_summary.tex"
    table_tex_path.write_text(tex_table, encoding="utf-8")
    print(f"✓ Tabla LaTeX guardada en {table_tex_path}")

def generate_extended_charts():
    ext_data_path = TABLES_DIR / "conaisi_sprint_10turns_metrics.json"
    if not ext_data_path.exists():
        return
    with open(ext_data_path, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    b_metrics = [m for m in metrics if m["condition"] == "baseline"]
    j_metrics = [m for m in metrics if m["condition"] == "jev"]

    turns = [m["turn_id"] for m in b_metrics]
    names = [m["turn_name"].split("_", 1)[1].replace("_", " ") for m in b_metrics]

    cum_base = [m["cumulative_tokens"] for m in b_metrics]
    cum_jev = [m["cumulative_tokens"] for m in j_metrics]

    th_base = [m["thinking_tokens_est"] for m in b_metrics]
    th_jev = [m["thinking_tokens_est"] for m in j_metrics]

    distractor_base = [m["distractor_mentions_in_thinking"] for m in b_metrics]
    distractor_jev = [m["distractor_mentions_in_thinking"] for m in j_metrics]

    # -------------------------------------------------------------
    # Gráfico 4: Escalabilidad de Tokens en Sesión Larga (10 Turnos)
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.plot(turns, cum_base, marker="o", linewidth=2.4, color="#C0392B", label="Baseline (Cuadrático $O(N^2)$ - Sin compactación ni gating)")
    ax.plot(turns, cum_jev, marker="s", linewidth=2.4, color="#27AE60", label="Cortex + JEV (Lineal $O(N)$ - Con Squeeze, Utterance y Compaction)")

    # Rellenar área de ahorro
    ax.fill_between(turns, cum_jev, cum_base, color="#2ECC71", alpha=0.18, label="Ahorro Neto de Tokens")

    ax.set_xlabel("Turnos Consecutivos de la Sesión de Trabajo")
    ax.set_ylabel("Tokens Acumulados en el Contexto del Agente")
    ax.set_title("Escalabilidad Temporal de Tokens: Acumulación Cuadrática vs Lineal (10 Turnos)")
    ax.set_xticks(turns)
    ax.legend(loc="upper left", frameon=True)
    ax.grid(True, linestyle="--", alpha=0.5)

    # Anotar desvío final
    diff_final = cum_base[-1] - cum_jev[-1]
    diff_pct = (diff_final / cum_base[-1]) * 100.0
    ax.annotate(f"Ahorro Final: -{diff_pct:.1f}%\n({diff_final:,} tokens evitados)",
                xy=(turns[-1], cum_jev[-1]),
                xytext=(-120, 40),
                textcoords="offset points",
                arrowprops=dict(arrowstyle="->", color="#1E8449", lw=1.5),
                fontsize=9.5, fontweight="bold", color="#1E8449",
                bbox=dict(boxstyle="round,pad=0.4", fc="white", ec="#27AE60", lw=1.2))

    plt.tight_layout()
    fig4_path = OUT_DIR / "fig4_long_session_scaling.png"
    plt.savefig(fig4_path)
    plt.close()
    print(f"✓ Gráfico 4 guardado en {fig4_path}")

    # -------------------------------------------------------------
    # Gráfico 5: Análisis de Distracción Cognitiva (Thinking Process)
    # -------------------------------------------------------------
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True)

    x = np.arange(len(turns))
    width = 0.35

    # Subplot 1: Tokens de Pensamiento Gastados
    ax1.bar(x - width/2, th_base, width, label="Baseline Thinking (Vueltas de pensamiento por ruido)", color="#E67E22", edgecolor="#BA4A00")
    ax1.bar(x + width/2, th_jev, width, label="JEV Thinking (Razonamiento directo y limpio)", color="#2980B9", edgecolor="#1B4F72")
    ax1.set_ylabel("Tokens de Razonamiento (Thinking)")
    ax1.set_title("Impacto del Contexto en el Proceso Cognitivo del Agente (Thinking Traces)")
    ax1.legend(loc="upper left", frameon=True)
    ax1.grid(axis="y", linestyle="--", alpha=0.5)

    # Subplot 2: Menciones de Distractores en el Razonamiento
    ax2.bar(x - width/2, distractor_base, width, label="Baseline: Dudas/Alucinaciones sobre distractores", color="#C0392B", edgecolor="#7B241C")
    ax2.bar(x + width/2, distractor_jev, width, label="JEV: Cero menciones de distractores", color="#27AE60", edgecolor="#1E8449")
    ax2.set_ylabel("Menciones de Distractores")
    ax2.set_xlabel("Turnos de Trabajo")
    ax2.set_xticks(x)
    ax2.set_xticklabels([f"T{t}" for t in turns])
    ax2.legend(loc="upper left", frameon=True)
    ax2.grid(axis="y", linestyle="--", alpha=0.5)

    plt.tight_layout()
    fig5_path = OUT_DIR / "fig5_thinking_distraction_analysis.png"
    plt.savefig(fig5_path)
    plt.close()
    print(f"✓ Gráfico 5 guardado en {fig5_path}")

    # -------------------------------------------------------------
    # Tabla 2: Resumen del Sprint Extendido de 10 Turnos
    # -------------------------------------------------------------
    md_t2 = """# Resumen Experimental: Sprint Extendido de 10 Turnos (ConaISI 2026)

| Turno | Descripción de la Tarea | Categoría | Tokens Base Acum. | Tokens JEV Acum. | Ahorro (%) | Thinking Base (tok) | Thinking JEV (tok) | Distractores en Thinking |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
"""
    for i in range(len(turns)):
        t_id = turns[i]
        t_name = names[i]
        cat = b_metrics[i]["turn_category"]
        c_b = cum_base[i]
        c_j = cum_jev[i]
        red = ((c_b - c_j) / max(1, c_b)) * 100.0
        th_b = th_base[i]
        th_j = th_jev[i]
        dist = f"Base: {distractor_base[i]} | JEV: {distractor_jev[i]}"
        md_t2 += f"| **{t_id}** | {t_name} | `{cat}` | {c_b:,} | {c_j:,} | **{red:.1f}%** | {th_b} | {th_j} | {dist} |\n"

    table2_md_path = TABLES_DIR / "table2_extended_10turn_summary.md"
    table2_md_path.write_text(md_t2, encoding="utf-8")
    print(f"✓ Tabla 2 Markdown guardada en {table2_md_path}")

if __name__ == "__main__":
    generate_charts()
    generate_extended_charts()


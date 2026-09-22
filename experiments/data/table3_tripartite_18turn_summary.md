# Resumen Experimental: Benchmark Tripartito de 18 Turnos (ConaISI 2026)

| Turno | Tarea / Operación | Categoría | RAW Acum. | BASELINE Acum. | JEV Acum. | Ahorro JEV vs RAW (%) | Cumplimiento RAW | Cumplimiento JEV |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | Cold Start Sparse Prompt | `sparse_prompt` | 301 | 462 | 422 | **-40.2%** | ❌ Deriva | ✓ 100% |
| **2** | Casual Interruption Server | `casual_trap` | 489 | 980 | 700 | **-43.1%** | ✓ | ✓ 100% |
| **3** | Component Review Grid | `review` | 832 | 1,772 | 1,242 | **-49.3%** | ✓ | ✓ 100% |
| **4** | Toxic Distractor Concurrency | `toxic_trap` | 1,192 | 2,683 | 1,920 | **-61.1%** | ✓ | ✓ 100% |
| **5** | Accessibility Contrast Fix | `code_edit` | 1,575 | 3,600 | 2,604 | **-65.3%** | ✓ | ✓ 100% |
| **6** | Casual Interruption CSS Advice | `casual_trap` | 1,843 | 4,589 | 3,160 | **-71.5%** | ✓ | ✓ 100% |
| **7** | Canvas Pause Interaction | `feature` | 2,268 | 5,792 | 3,920 | **-72.8%** | ✓ | ✓ 100% |
| **8** | Large Tool Output Linter | `compaction` | 4,109 | 8,389 | 4,693 | **-14.2%** | ✓ | ✓ 100% |
| **9** | Persistence ADR Compliance | `adr_compliance` | 5,973 | 11,072 | 5,552 | **7.0%** | ❌ Deriva | ✓ 100% |
| **10** | Milestone Checkpoint SDD | `checkpoint` | 7,861 | 13,781 | 6,437 | **18.1%** | ✓ | ✓ 100% |
| **11** | Casual Interruption Vite Trivia | `casual_trap` | 9,631 | 16,558 | 7,190 | **25.3%** | ✓ | ✓ 100% |
| **12** | CLI Simulator Extension | `feature` | 11,558 | 19,553 | 8,151 | **29.5%** | ✓ | ✓ 100% |
| **13** | Large Tool Output Tests | `compaction` | 14,900 | 23,941 | 9,124 | **38.8%** | ✓ | ✓ 100% |
| **14** | Theme Color Audit | `audit` | 18,261 | 28,461 | 10,229 | **44.0%** | ✓ | ✓ 100% |
| **15** | Canvas FPS Optimization | `performance` | 21,645 | 33,062 | 11,415 | **47.3%** | ✓ | ✓ 100% |
| **16** | Casual Interruption Pizza | `casual_trap` | 24,905 | 37,726 | 12,464 | **50.0%** | ✓ | ✓ 100% |
| **17** | Documenter Self Review | `review` | 28,320 | 42,534 | 13,647 | **51.8%** | ✓ | ✓ 100% |
| **18** | Final ADR and Session Close | `close` | 31,756 | 47,368 | 14,856 | **53.2%** | ✓ | ✓ 100% |

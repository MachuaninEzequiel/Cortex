# HANDOFF — Programa de Transformación Cortex
> **Leer esto COMPLETO antes de hacer nada.** Última actualización: cierre de sesión 2026-08-22.
> Este documento es el contrato de continuidad entre sesiones/agentes. Si algo acá y en otro
> lado se contradice, este archivo manda (y actualizá el otro).

## 1. Contexto en 30 segundos

**Proyecto**: Cortex (`cortex-memory` v0.5.0) — memoria cognitiva híbrida (episódica+semántica)
y gobernanza para agentes de IA. CLI Typer + MCP server + retrieval híbrido (ChromaDB + ONNX
embeddings + BM25) + vault estilo Obsidian. ~48k LOC Python, repo `/home/chucho/Cortex`.

**Programa activo**: Transformación total del proyecto, administrada documentalmente en
`docs/transformacion/` (plan maestro: `README.md`; estado vivo: `ESTADO-ACTUAL.md`;
obras 01-06). Nació de un deep review exhaustivo en `docs/reviews/2026-08-deep-review/`.

**Objetivos del dueño** (en su orden declarado): podar todo lo viejo/muerto; un estándar único
de CLIs/IDEs; migrar a Rust por rendimiento/batería; embeddings multilingües con config por
idioma (su dolor real: la búsqueda en español); UX simple con un "ActionEngine".

## 2. Git — dónde está TODO

- **Rama de trabajo: `feature/transformacion-2026-08`** — TODO el trabajo vive acá.
- **`master` = sello inmutable**: tag `v0.5.0-baseline-seal` @ a64e350 (pusheado a origin).
  NO tocar master.
- Suite actual: **VERDE** (unit + integration exit 0). Antes del programa había 86 fallos.

## 3. Qué se hizo (commits en orden, rama feature/transformacion-2026-08)

| Commit | Qué |
|---|---|
| `9eac958` | Deep review 12/12 subsistemas → docs/reviews/2026-08-deep-review/ |
| `518fec8`,`798775c` | Plan maestro + planes ejecutables de obras 01-06 |
| `788c5c4` | **TRAMO 0**: pin `mcp>=1.2,<2` (77 fallos), fix tar-slip backup.py → suite verde |
| `e9b3e4e..bf5bd3b` | **TRAMO 1 ola 1**: uninstall IDE seguro (pi/codex/cursor), session mutate() anti lost-update, webgraph cache/404/mode, cli --dry-run real, poda P1 (6 ítems muertos) |
| `640ca20` | **Obra 02 F0-1**: helpers marcadores en base.py + caracterización 11 adapters |
| `42adfe1..13c7ff1` | **Obra 02 F2**: uninstall(project_root) real en los 11 adapters (restore-de-backup, merge inverso JSON/TOML, _unique_backup) |
| `f8a6ec0` | **Obra 02 F3**: CLI unificada `cortex ide list\|setup\|remove\|status` (--project-root, --dry-run, --json) + deprecation funcional de los 4 comandos viejos |
| `2df3ce2`,`73cdde5` | **Obra 04 A1-A5**: fixes stack vectorial (dim paramétrica, fail-fast anti-búsqueda-vacía, caché con identidad de modelo schema v2, colisiones chunk_id, frontmatter preservado) |
| `92383ce` | **Obra 04 A6**: consolidación embedders vía EmbedderFactory; OpenAI batchea |
| `b9ccd43` | Backend `fastembed` genérico + resultados evaluación candidatos |
| `c5f40a7` | **Eval suite ES/EN** (34 docs, 51 queries, MRR@10/R@k) + baseline MiniLM commiteado: EN MRR=1.0 / **ES MRR=0.8821** (confirmó el problema de español) |
| `065fed5` | **Obra 04 C**: bloque config `embedding:` per-language retrocompatible + heurística ES/EN pura (`cortex/embedders/language.py`) + `cortex embedding-status` |
| `3950197` | **Obra 04 E**: `cortex reindex` (backup→rebuild→rollback automático, --prune-old-caches, --dry-run) + template bilingüe para proyectos nuevos + CHANGELOG |
| `deed848` | Decisión e5-large documentada + obra 06 (LFM2.5 futuro) + MrBERT-es apéndice |

## 4. Decisiones técnicas ya tomadas (NO re-discutir)

1. **Modelo de embeddings elegido**: `intfloat/multilingual-e5-large` (backend `fastembed`)
   para español — medido: ES MRR@10 0.9615 vs 0.8821 MiniLM (+9%), R@1 ES 0.81→0.92,
   EN intacto (1.0). Costo: 61ms/query, ~2GB RAM. Tabla completa en doc 04.
   Inglés mantiene all-MiniLM-L6-v2 (onnx).
2. **LFM2.5-1.2B-Instruct (Liquid)** NO es embedder: es capa futura de inteligencia local
   (reranker generativo, summarizer offline, cerebro del ActionEngine). Doc 06. Licencia
   LFM1.0: libre solo bajo US$10M/año. Investigación profunda pendiente ANTES de implementar.
3. **MrBERT-es (BSC-LT)**: encoder MLM base, NO usable como embedder sin fine-tune
   contrastivo → obra futura candidata ("embedder custom español-first"). Apéndice doc 06.
4. **Pin `mcp>=1.2,<2`** hasta P9 (post-split server.py): la API 2.x rompe todo el MCP.
5. Piezas dormidas RESERVADAS para Obra 05 (no podar): feedback_loop, telemetría enricher,
   tutor guide_path.
6. Congelación levantada: server.py/main.py ya pueden tocarse (no hay otros workers).

## 5. Qué FALTA (orden recomendado)

### Inmediato — cerrar Obra 04 al 100%
- [ ] Flip del default: decidir si `intfloat/multilingual-e5-large` pasa a ser default global
      (single-model) o queda solo per-language es (hoy: template nuevo genera per-language;
      proyectos existentes deben agregar el bloque y correr `cortex reindex`).
- [ ] Correr `cortex reindex` en el vault real del dueño y validar percepción de calidad.
- [ ] (Opcional) Evaluar cuantización int8 de e5-large con la misma suite.

### Obra 01 restante (podado)
- [x] **P2 COMPLETA (2026-08-23)**: decay decorativo podado (ScoringWithDecay/create_decay_config/
      apply_to_hits/get_stats/apply/EnricherDecayConfig/TEMPORAL_TYPES), maquinaria muerta de
      co_occurrence (build_from_ast+cadena AST/JS, get_related/get_path/get_files_by_type,
      node_count/relationship_count, EXTENDS/DEFINES), _build_entity_index, is_known_agent/_KNOWN_AGENTS,
      NoActiveSession, forced_reason/extra_notes (wiring Phase 04 incompleto), only_agent, flag
      --no-graph, 9×F841/F401 rezagados. Tests de caracterización nuevos (memory_decay + co_occurrence).
      Gates: ruff F401/F841=0, vulture80=0, suite 2271 passed. SKIP feedback_loop (reservado Obra 05);
      domain_confidence diferido a P-bugs; fix bug #9 sigue en P6.
- [x] **P3 COMPLETA (2026-08-23)**: golden contract MCP primero (`ad97caf`: snapshot byte-a-byte de
      los 32 tools + ruteo 32/32 con sentinelas) y DESPUÉS split de server.py en sub-commits:
      `edfc243` vault_adapter único (V6), `7050391` schemas.py (defs de tools), `8be09b6` mixins por
      dominio en cortex/mcp/tools/{search,sessions,documenter,workspace} + dispatcher tabla _TOOL_ROUTES.
      server.py: 2977 → 491 líneas. Suite 2279 verde en cada commit; contrato intacto byte-a-byte.
      Candidato de poda anotado: `_sync_vault_text` (0 callers producción).
- [ ] P4: adelgazar main.py (2277l) a subapps siguiendo patrón cli/session.py.
- [ ] P5-P8 según plan (unificar enricher sync/async, schemas ×2, strings→archivos, romper ciclo session↔documenter).
- Deudas nuevas detectadas en P2/P3 (preexistentes, para P-bugs): F821 latente cli/main.py:2233
  (`cortex_ide` no definido en rama interactiva IDE) y enricher.py:65 (`EnrichmentFilters`).
- P9 (migración mcp 2.x) ahora evaluable: existe split + golden contract como red.

### Obra 03 (Rust) — plan completo en 03-MIGRACION-RUST.md
- [ ] T-BENCH-1: harness de benchmarks en bench/ + baseline commiteado. SIN BASELINE NO HAY MIGRACIÓN.
- [ ] Después: Tramos A→E según gates G0-G6 (≥5× retrieve p99, etc.).

### Obra 05 (UX/ActionEngine) — plan completo en 05-UX-TUI-ACTIONENGINE.md
- [ ] Depende de: suite verde (✅), NO podar sus piezas reservadas (✅ respetado), Fase 3 CLI (✅).
- [ ] Puede arrancar cuando se quiera: fases A-E del plan.

### Obra 06 (LFM2.5) — FUTURO, investigación profunda primero (doc 06).

## 6. Cómo trabajar en este programa (reglas aprendidas)

1. Leer `docs/transformacion/README.md` + `ESTADO-ACTUAL.md` + esta handoff antes de codear.
2. Todo cambio va en `feature/transformacion-2026-08`. Commits por lógica (nunca blob).
   Suite verde antes de cada commit. Actualizar ESTADO-ACTUAL.md al cerrar sesión.
3. Los planes de las obras son EJECUTABLES: tareas con checkbox, gates con comandos.
   Seguir el plan; si el plan está mal, actualizar el plan primero.
4. **Subagentes (rlm)**: presupuesto por turno corto — se cortan a mitad de trabajo.
   Tácticas que funcionan: (a) briefs edit-first con pasos numerados pequeños;
   (b) exigir entrega por VARIOS agent_message cortos (~15 líneas c/u), no un reporte final;
   (c) escribir archivos incrementalemente desde el primer paso; (d) steer inmediato cuando
   quedan idle sin entregar (observar transcript con agent_observe.recent_messages);
   (e) prohibir git a los hijos; scopes disjuntos por archivos; (f) si un hijo no entrega
   tras 2 steers, hacerlo uno mismo (suele ser más rápido).
5. Verificación siempre: `.venv/bin/python -m pytest <scope> -q --no-cov` (venv propio del
   proyecto YA creado). Suite completa antes de commit: `pytest tests/unit tests/integration`.
6. Websearch (Serper) NO configurado; para investigar modelos usar la API pública de HF
   (`https://huggingface.co/api/models/<id>` + `/raw/main/README.md`) vía httpx — funcionó bien.

## 7. Deudas/conocidos abiertos (no regresiones)

- Flake raro no reproducible: test_setup_dry_run_creates_nothing falló 1 vez por pollution
  de orden; vigilar.
- `docs_vectorization._resolve_cache` usa Path.cwd() default (patrón viejo); migrar a layout.
- tests/e2e requieren entorno aparte; no corren en la línea base actual.
- requirements.txt sigue contradiciendo pyproject (sentence-transformers core vs extra):
  arreglar en próxima pasada de empaquetado.
- CHANGELOG tiene entradas [Unreleased] históricas apiladas; normalizar en algún release.

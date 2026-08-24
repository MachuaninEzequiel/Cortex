# ESTADO ACTUAL DEL PROGRAMA

> **ACTUALIZADO 2026-08-24 (cierre de sesión de integración).**
> Obra 07 (migración total a Rust) en marcha: **P0-P5 ✅ · P10 ✅ (stream
> paralelo) · P6+P7 y P8+P9 LANZADOS EN DUAL-STREAM**.
> Plan maestro: `docs/transformacion/08-MIGRACION-TOTAL-RUST.md` (§4b
> coordinación dual-stream).
> Handoff activo para agentes: `HANDOFF.md` §"HANDOFF ACTIVO".

## Estado consolidado al cierre

### Completado y verificado con paridad byte-a-byte vs Python

| Fase | Alcance | Evidencia |
|---|---|---|
| P0 | crates cortex-config/cortex-app + harness `bench/parity/` | fixtures commiteados, determinismo probado |
| P1 | CortexConfig completa en serde | dumps idénticos sobre 8 fixtures |
| P2 | vault + embeddings ort + hybrid search nativo | BM25 **100/100** · semántico **100/100** |
| P3 | episódica nativa + exportador chroma→JSONL | round-trip 12/12 · vector 6/6 vs HNSW · keyword/entity ✓ |
| P4 | Session primitive + storage YAML atómico + verification runner + quality gates | dumps 4/4 · hooks 5/5 · gates 6/6 · infer_mode 4/4 |
| P5 | reconstructor gitless+git-aware + DocumenterPersister | dump idéntico · create_args 20 campos · note_body byte-parity (jinja2↔minijinja) |
| P10 | cortex-branding + cortex-tui + logo en banner del brain *(stream paralelo del dueño)* | snapshot render + latencia <50ms · 73 tests del stream |

### Bugs reales descubiertos por la migración (todos corregidos)

1. OOM del kernel ×2: `bench/int8_probe.py` v1 (10GB) → fix + lección de memoria.
2. Keyword bypass episódico roto con chromadb moderno → filtrado local `$contains`.
3. `lstrip("./")` anulaba la exención de artefactos procesales en quality_gates.

### En vuelo (dual-stream)

- 🅰 Stream A: **P6** (`cortex-actions`) + **P7** (módulo `context` en cortex-app).
- 🅱 Stream B: **P8** (`cortex-setup`) + **P9** (`cortex-mcp` con rmcp).
- Reglas y protocolo: plan maestro §4b. Progreso por stream:
  `progreso-streamA.md` / `progreso-streamB.md`.

### Restante post-streams

P11 cola larga (ci/tutor/hu/pr_context…) · P12 integración final (TUI←engines,
brain in-process, default Rust, eliminación capa Python, versión).

## Reglas operativas vigentes

1. Suite Python completa = oráculo; verificar Rust SIEMPRE por crate
   (`cargo test -p …`) — el global puede tener WIP ajeno.
2. Paridad antes que velocidad; drift visible ⇒ revert.
3. Memoria: un modelo residente por vez · batches ≤64 · sin `/tmp` como caché.
4. Commits atómicos un-gate-por-commit · suite verde antes de commitear.
5. ESTADO-ACTUAL/HANDOFF se actualizan solo en sesiones de integración.

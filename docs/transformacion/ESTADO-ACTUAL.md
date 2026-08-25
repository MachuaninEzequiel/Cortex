# ESTADO ACTUAL DEL PROGRAMA

> **ACTUALIZADO 2026-08-24 (cierre dual-stream + verificación integral).**
> Obra 07 (migración total a Rust): **P0–P11 ✅ COMPLETADAS Y GATEADAS ·
> P12 ABIERTA**. La respuesta honesta a "¿ya todo es Rust?" es NO: los
> motores sí; el comando `cortex` que usa el usuario sigue delegando en el
> CLI Python por decisión G6, y quedan ~22k líneas de dominios secundarios.
> Detalle exhaustivo: **`docs/transformacion/09-DEUDA-MIGRACION-PYTHON.md`**
> (léase junto a este archivo).
> Handoff activo para agentes: `HANDOFF.md` §"HANDOFF ACTIVO".

## Estado consolidado al cierre

### Completado y verificado con paridad byte-a-byte vs Python

| Fase | Alcance | Gate |
|---|---|---|
| P0 | crates cortex-config/cortex-app + harness `bench/parity/` | doctor.txt · next_stats.json PASS |
| P1 | CortexConfig completa en serde | dumps idénticos ×2 fixtures |
| P2 | vault + embeddings ort + hybrid search | BM25 100/100 · semántico 100/100 rankings |
| P3 | episódica nativa (lectura) + exportador chroma→JSONL | round-trip 12/12 · vector 6/6 · keyword/entity ✓ |
| P4 | Session primitive + storage YAML + verification + gates | dumps 4/4 · hooks 5/5 · gates 6/6 · infer_mode 4/4 |
| P5 | reconstructor gitless/git-aware + DocumenterPersister | dump idéntico · note_body byte-parity |
| P6 🅰 | crate cortex-actions (ActionEngine+FeedbackStore) | 16/16 salidas `next` byte-a-byte |
| P7 🅰 | módulo context en cortex-app (Enricher+budget) | 3 bundles --json byte-a-byte |
| P8 🅱 | cortex-setup: minijinja+YAML réplica+writers+11 IDE+hooks | YAML 138/138+fuzz · renders/writers idénticos · ide 33/33 · hooks 38/38 |
| P9 🅱 | cortex-mcp (rmcp): catálogo+ruteo congelados | list_tools byte-a-byte · ping golden |
| P10 | branding + TUI ratatui + logo | snapshot <50ms · tests del stream |
| P11-ci 🅰 | plugin CI + SessionService completo | 23/23 comandos `cortex ci` byte-a-byte |

Verificación integral post-cierre (esta sesión): workspace **219 tests**,
clippy/fmt limpios, todos los oráculos golden re-verificados con fixtures
frescos, suite Python **2455 passed, 18 skipped**.

### Bugs reales descubiertos/corregidos durante la migración

1. OOM del kernel ×2 (`bench/int8_probe.py`) → fix + lección de memoria.
2. Keyword bypass episódico roto con chromadb moderno → filtro `$contains`.
3. `lstrip("./")` anulaba exención de artefactos procesales en quality_gates.
4. Glob patterns tratados como literales en claude_code uninstall (atrapado
   por el gate P8d antes del commit — stream B).
5. Test `blit_copia_solo_lo_opaco` de branding con fixture imposible
   (introducido por commit de banner post-P10) → fixture corregido
   (`dded2da`). Único fallo del workspace en la verificación final.

### Lo que TODAVÍA depende de Python (~22k líneas)

Resumen ejecutivo (detalle y orden de ataque: doc 09 §3–§4):

- El binario `cortex-cli` es fachada passthrough sobre el CLI Python (G6).
- MCP nativo: catálogo+ruteo congelados; handlers devuelven "backend no
  nativo" salvo ping.
- Dominios sin porte: doctor · tutor · workitems/hu · pr_context ·
  review_knowledge+enterprise · webgraph-server (el cálculo ya es nativo) ·
  autopilot · pipeline/SDDwork · docs-migrate · doc_generator/validator/
  verifier · services spec/note · workspace/layout · context
  observer/telemetry/filters/presenter-text · documenter/interactive ·
  TUI rich vieja.

### Próximos pasos (P12 — orden sugerido en doc 09 §4)

1. episodic.append + semantic.reindex (prereq de escrituras nativas)
2. hu/workitems + pr_context (specs claras, patrón P11-ci)
3. mcp/tools handlers in-process (+decisión wire-format nulls/omisión)
4. workspace/layout → doctor → enterprise/review_knowledge → webgraph axum
5. CLI clap nativo con CORTEX_PY=1 de rollback (medir cold start <100ms)
6. pipeline + autopilot → baja definitiva de Python (brain in-process,
   wheels solo-Rust, README a binarios)

## Reglas operativas vigentes

1. Suite Python completa = oráculo hasta la baja final; verificar Rust
   SIEMPRE por crate (`cargo test -p …`).
2. Paridad antes que velocidad; drift visible ⇒ revert.
3. Memoria: un modelo residente por vez · batches ≤64 · sin `/tmp` como caché.
4. Commits atómicos un-gate-por-commit · suite verde antes de commitear.
5. Dual-stream CERRADO: las reglas §4b de coordinación quedan históricas;
   el refresco documental vuelve a ser parte del flujo normal.

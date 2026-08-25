# Progreso STREAM B — Obra 07 fase P12 (dual-stream)

> Stream B de P12 (territorios §7 del doc 09). Este archivo es el único
> registro de progreso de este stream: NO actualiza ESTADO-ACTUAL.md,
> HANDOFF.md ni el doc 09. Crates propios: `cortex-workspace`,
> `cortex-webgraph-server`, `cortex-enterprise`, `cortex-doctor`,
> `cortex-autopilot`, `cortex-pipeline`, reescritura de `cortex-cli`.
> PROHIBIDO editar `cortex-app`/`cortex-mcp`/`cortex-actions` (stream A).

## Decisiones de implementación

- **Emisor PyYAML propio (`cortex-workspace::pyyaml`)**: serde_yaml NO
  replica el formato de PyYAML (folding a 80 col, quoting de indicadores,
  sequences indentless, indent+2 alrededor de escalares vía
  `expect_scalar→increase_indent(flow=True)`). Se portó fielmente el
  subconjunto del emisor + resolver implícito de PyYAML 6.x instalado
  (fuente leída en `.venv`). Lo consumirá todo lo que emita YAML paridad
  (doctor/handoff/webgraph-workspace).
- **skills embebidos con `include_str!`** (mismo patrón que cortex-setup
  desde P8): cero dependencias nuevas; los recursos quedan byte-idénticos
  por construcción y el gate verifica hashes SHA-256 contra los recursos
  Python.
- **`resolve_safe` NO se duplica**: es territorio de A (cortex-app);
  cortex-workspace no lo contiene por diseño.
- **runtime_context hace shell-out a `git`** con timeout de 5s replicado
  por polling (`try_wait`), sin dependencias nuevas; fallbacks idénticos
  (`no-git-branch`, project_root como toplevel).
- **Cargo.lock compartido**: el diff actual contiene un hunk ajeno de A
  (`cortex-setup` en deps de cortex-app) ⇒ se commitea SIN lock hasta que
  A integre los suyos (regla §7.2.2).
- **[P12B-2] sum() de CPython ≥3.12 usa Neumaier**: `_cosine_similarity`
  del oráculo NO es suma ingenua — el builtin suma floats con compensación.
  Por eso los scores salen del kernel G4 (`cortex_core::webgraph`, Neumaier)
  y NO debe portearse nunca con `fold(0.0, +)` (divergencia 1 ULP verificada
  empíricamente contra Python 3.12.14).
- **[P12B-2] serde_json feature `float_roundtrip`**: sin ella, el re-parseo
  del caché de snapshots perdía 1 ULP en floats como 0.9526919036834995
  (parser default no correctamente redondeado) ⇒ respuestas cacheadas ≠
  frescas y gate S07/F01 rojo. Con la feature, round-trip exacto. Sin deps
  nuevas (feature de serde_json ya aprobado).
- **[P12B-2] federación resuelve memoria por config**: workspace.yaml sin
  clave `memory:` ⇒ resolver `resolve_episodic_persist_dir` (default
  `memory/`) igual que EpisodicSource Python; NO devolver vacío.

### Diseño aprobado P12B-3 — cortex-enterprise

- **Arquitectura**: crate profundo `cortex-enterprise` con módulos `models`,
  `config`, `governance`, `promotion_models`, `knowledge_promotion`,
  `promotion_doctype`, `maintenance`, `retrieval`, `reporting` y
  `review_knowledge`. Consume `cortex-workspace`, `cortex-setup` y
  `cortex-app` read-only. `review_knowledge` porta operaciones y presentación
  comprobable, pero el registro clap queda para P12B-8 (CLI nativo último).
- **Seam enterprise→doctor**: `reporting` define `DoctorBackend` y vistas
  neutrales `DoctorReportView`/`DoctorCheckView`. El backend por defecto falla
  explícitamente con `doctor backend unavailable until P12B-4`; el gate usa un
  snapshot del doctor Python y P12B-4 implementará `NativeDoctorBackend` desde
  `cortex-doctor`. Así las dependencias quedan `doctor → enterprise/webgraph`,
  nunca `enterprise → doctor`, y `build_memory_report` ejecuta doctor una vez.
- **Seams de testabilidad**: reloj inyectable para promoción/review/retención;
  `SearchBackend` inyectable para fuentes semánticas/episódicas. El adapter
  nativo usa BM25/export episódico sin embeddings y ONNX cuando recibe
  `model_dir`; ausencia de backend requerido falla explícitamente.
- **Paridad y gate**: `bench/parity/enterprise_golden_p12b.py` +
  `examples/enterprise_check.rs`, byte-a-byte con solo `{{ROOT}}`/`{{TS}}`.
  Cubre config/YAML, validaciones, gobernanza, promoción legacy y DocType,
  review queue/salida/path traversal, retención/archivo, retrieval/RRF y
  reporting local/all con snapshot real, más fallo del backend default.
- **Errores/dependencias**: `EnterpriseError` manual (sin dependencia nueva),
  mensajes contractuales preservados, omisión tolerante solo donde Python la
  tiene. YAML PyYAML-compatible mediante `cortex_setup::yaml::dump_with`,
  incluido `allow_unicode=false` para `org.yaml`.

## Tabla de tareas P12B

| Tarea | Estado | Evidencia | Commit |
|---|---|---|---|
| P12B-1 crate cortex-workspace (layout 564 + handoff 121 + git_policy 111 + skills 98 + runtime_context 58 ≈ 1076 LOC py) | ✅ | Gate: `bench/parity/workspace_golden_p12b.py` build/verify determinista + `examples/workspace_check.rs` **byte-parity** sobre 8 escenarios de discovery + handoff H01–H06 (zoo quoting/folding/multilínea/tab congelados vs PyYAML real) + validaciones inválidas + snippets/gitignore + slugify/persist-modes (fake-git y repo REAL `feature/Mi_Rama`) + skills con hashes. Suite Python oráculo verde: **2455 passed, 18 skipped**. `cargo test -p cortex-workspace`: 27 tests ✅ · clippy `-D warnings` ✅ · fmt ✅ | (este commit) |
| P12B-2 webgraph-server axum (~2202) | ✅ | Gate: `bench/parity/webgraph_golden_p12b.py` build/verify determinista + `examples/webgraph_check.rs` **byte-parity** vs `golden_webgraph.txt` (server real axum/Flask en puertos efímeros, fixture fake_embed SHA-256 + export P3, normalización {{ROOT}}/{{TS}}/{{FP}}; 19 casos single + 3 federados). Suite Python oráculo rc=0. clippy `-D warnings` ✅ fmt ✅ tests 3 ✅ | `2761356` |
| P12B-3 enterprise/review_knowledge (~2441) | ⏳ pendiente | — | — |
| P12B-4 doctor (~925) | ⏳ pendiente | golden P0 congela salida; checks sin backend nativo ⇒ fail explícito documentado (patrón P6/P9) | — |
| P12B-5 autopilot (~1902) | ⏳ pendiente | spec: tests/unit/autopilot | — |
| P12B-6 pipeline SDDwork (~1708) | ⏳ pendiente | reqwest aprobado §7.2.8; stages gh API con fixtures/dry-run | — |
| P12B-7 tutor (~862) | ⏳ decisión del dueño pendiente | se documentarán las 3 opciones (porte fiel vs ratatui vs no migrar) aquí al cierre | — |
| P12B-8 CLI clap nativo (~2995, ÚLTIMO) | ⏳ pendiente | punto de sincronización final; CORTEX_PY=1 rollback; cold-start <100ms | — |

## Notas de coordinación dual-stream

- Consumo de cortex-app como dep normal de Cargo (read-only); nada de A fue
  editado por B.
- El gate P12B-1 corre en <2s y no colisiona con los goldens `*p12a*` de A.
- Al commitear `rust/Cargo.toml` se incluyeron SOLO las líneas de mi miembro;
  `Cargo.lock` queda fuera de este commit por hunks ajenos de A (ver
  decisiones).

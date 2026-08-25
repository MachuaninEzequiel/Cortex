# Progreso STREAM A — Obra 07 · P12 (contenido-y-escritura)

> Stream A del dual-stream P12 (reglas §7 de `09-DEUDA-MIGRACION-PYTHON.md`).
> Este archivo es el único registro de progreso de este stream: NO actualiza
> ESTADO-ACTUAL.md ni HANDOFF.md ni el doc 09.
>
> Territorio: `rust/crates/cortex-app/` (extensiones episodic.append, semantic
> reindex, workitems, pr, context extras, documenter/interactive),
> `rust/crates/cortex-mcp/src/server.rs` handlers, NUEVO
> `rust/crates/cortex-services/`, gates `bench/parity/*p12a*`.

## P12A-1 — prereq escrituras: episodic.append + semantic.index_file + security

Estado: ✅ COMPLETADA (gate verde + suite Python oráculo verde).

Qué se portó:

- **`cortex-app/src/security.rs`** (nuevo): puerto completo de
  `cortex/security/paths.py` — `resolve_safe`, `validate_under_root`,
  `PathSecurityError`, con mensajes de error idénticos y un
  `resolve_lenient` que replica el `Path.resolve()` no estricto de Python
  (canonicaliza el ancestro existente más profundo). Tests propios.
- **`cortex-app/src/episodic/entities.rs`** (nuevo): puerto 1:1 de
  `_extract_entities` — los 8 patrones regex por categoría, orden de
  inserción estable, dedup primera aparición, tupla → primer grupo no-vacío,
  cap 15. Expectativas de tests validadas CONTRA EL ORÁCULO Python
  (`"función"` no matchea; `"importar os"` no matchea dependency).
- **`cortex-app/src/episodic/mod.rs`**: `NativeEpisodicStore::append`
  (puerto de `EpisodicMemoryStore.add`): genera `mem_{hex8}` +
  `datetime.now(UTC).isoformat()` con microsegundos, mergea entidades sobre
  extra_metadata (pisa `"entities"` como Python), serializa la meta
  flattenada con el mismo orden de claves de `_serialize_metadata`
  (`serialize_metadata`) y escribe la fila al JSONL en modo append-only
  (líneas previas byte-idénticas) + insert ordenado por id en el vec
  in-memory. Serializador compacto estilo CPython (`json.dumps(...,
  ensure_ascii=False)`: floats repr shortest, `\b`/`\f` nombrados).
- **`cortex-app/src/semantic/mod.rs`**: `SemanticIndex::index_file` (puerto
  de `VaultReader.index_file`): upsert preservando posición de inserción,
  purga+regeneración de chunks del padre vía `chunks_for_doc` (compartido
  con sync), recalculo completo BM25 (`recompute_stats`, refactor compartido
  con build), embed batch inyectado. Archivo inexistente ⇒ `Ok(false)` como
  Python; otros errores ⇒ `Err(msg)` (divergencia documentada, estrictamente
  más informativa).

Gate: `bench/parity/p12a1_golden.py` (build/verify) +
`rust/crates/cortex-app/examples/p12a1_check.rs`:

- episódico: store real Python (chroma + ONNX real) con las 12 memorias del
  golden P3 + 4 appends vía `store.add`; Rust carga el export base y appendea
  con ort real. Resultado: entries after 16/16 idénticas (claveadas por
  document), rankings vectoriales post-append exactos por ORDEN (6 queries),
  keyword bypass idéntico, filas JSONL con meta byte-parity.
- semántico: R1 (sync) y R2 (modificación de specs/2026-06-01_gate.md +
  index_file incremental) idénticos al oráculo + contrato interno
  incremental==full-rebuild.
- Normalizaciones pactadas documentadas en el header: ids/timestamps
  aleatorios ⇒ comparación claveada por document / `{{TS}}`; embeddings con
  tolerancia ≤1e-4 (el contrato conductual son los rankings exactos); orden
  de claves dentro de meta no es contrato (chroma no lo garantiza); keyword
  hits ordenados.

Verificación: `cargo test -p cortex-app` 58 passed · clippy `-D warnings`
limpio · fmt limpio · suite Python **2455 passed, 18 skipped**.

Lecciones del gate (bugs atrapados antes del commit):

1. El gate original capturaba R2 sin escribir la modificación en disco antes
   de `index_file` — el drift era del oráculo, no del porte.
2. Los flags `entity_*` van normalizados a minúsculas por
   `_entity_filter_key` (validado contra Python).

| Tarea | Estado | Evidencia | Commit |
|---|---|---|---|
| P12A-1 episodic.append + semantic.index_file + resolve_safe | ✅ | `bench/parity/p12a1_golden.py` verify PASS + `p12a1_check` PARIDAD COMPLETA (16/16 entries · 6 rankings exactos · R1/R2 idénticos · incremental==rebuild); suite Python 2455 passed | (este commit) |

## ADR chico: dependencia uuid en cortex-app

- **Decisión**: agregar `uuid = { version = "1", default-features = false,
  features = ["v4"] }` a cortex-app para generar ids `mem_{hex8}` fieles a
  `f"mem_{uuid4().hex[:8]}"` de MemoryEntry.
- **Justificación**: paridad de formato de ids sin inventar un generador
  propio; `uuid 1.25.0` ya estaba en `Cargo.lock` (transitivo) y v4 usa
  getrandom ya presente ⇒ cero paquetes nuevos en el lock (diff verificado:
  solo la línea `uuid` en deps de cortex-app).
- **Alternativas descartadas**: hex derivado de timestamp/pid (no es v4,
  colisiones triviales en batch), dep nueva `rand` directo (innecesaria).

## Cola restante (orden de dependencias)

| Tarea | Estado |
|---|---|
| P12A-2 workitems/hu (~685) | pendiente |
| P12A-3 pr_context (~623) + gate CliRunner→checker | pendiente |
| P12A-4 doc_generator/doc_validator/doc_verifier (~590) | pendiente |
| P12A-5 spec_service + note_service (~541) | pendiente |
| P12A-6 documentation/migration docs-migrate (~565) | pendiente |
| P12A-7 context extras observer/telemetry/domain/filters/presenter (~1902) | pendiente |
| P12A-8 documenter/interactive (~342) | pendiente |
| P12A-9 mcp handlers in-process (~2056) · escritura espera decisión wire-format §4.8 | pendiente |

Notas de coordinación dual-stream:

- Handlers MCP de ESCRITURA: quedan con fallo explícito actual hasta que
  exista la decisión del dueño sobre wire-format rmcp (HANDOFF §4.8); se
  documentará acá cuando P12A-9 entre.
- Sin toques a territorios de B (crates nuevos, cortex-cli, bench/*p12b*,
  docs de B ni ESTADO-ACTUAL/HANDOFF/doc 09).

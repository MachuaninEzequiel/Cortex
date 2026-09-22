# Enricher pack v2 — canónico + punteros

Spec de implementación. No es un essay. Complementa squeeze de search (v1) y promote (v1.1). **No se implementa hasta que el dueño apruebe este documento.**

Principio: el LLM no necesita 8 excerpts de 200 chars con el mismo keyword. Necesita **1–2 fuentes canónicas** (el mecanismo) y **punteros** (path + arista + una línea) para leer el resto. Misma información, menos tokens, menos basura.

Quien no prenda judgement: `cortex context` / presenter actual, **bit a bit**.

---

## 1. Qué se decide acá

| Decide | No decide |
|---|---|
| Contrato del prompt inyectado (`pack`) | Reescribir BM25, RRF, observer, hybrid |
| Un purpose nuevo `context_pack` (default off) | Autopilot, Brain router, MCP tools nuevas |
| Dónde se engancha (después de finalize, antes de presenter) | GraphRAG, summaries LLM del vault entero |
| Fail-open y eval (`gold_in_prompt` / chars) | Portar metodologías o SDKs de terceros; GraphRAG |

Proporcionalidad (trabajo chico → poco contexto), un artefacto recuperable en vez de N blurbs, locator en vez de re-buscar. Nombres de producto de terceros no se usan en esta spec.

---

## 2. Modos

Igual que search squeeze.

```
context_pack off / sin key / 429 → presenter actual (to_compact / to_markdown)
context_pack on y HTTP ok     → pack (canónicos + punteros)
```

Nunca lista vacía porque Jev tosió. Nunca watermark “powered by TypeSafe”. El agente IDE no tiene que saber si el pack vino de Jev.

Config (suma al bloque `judgement.purposes` existente):

```yaml
judgement:
  enabled: true
  provider: typesafe
  purposes:
    search_squeeze: on    # ya existe
    promotion: on         # ya existe
    context_pack: off     # NUEVO — default off
```

YAML sin la clave `context_pack` ≡ off.

---

## 3. Contrato del pack (lo que ve el LLM)

El pack **no** es `EnrichedBundle.items` recortado. Es un documento con tres zonas, en este orden:

```
## Context pack
family: <choice o "other">     # hint; no filtra el vault en v1 del pack
canonical: <1–2>
pointers: <0–N, máx 6>
dropped: <count>               # solo si verbose humano; NO en prompt de agente
```

### 3.1 Canónicos

- 1 ítem si noul del #2 < 0.50 o el budget no da.
- 2 ítems si ambos noul ≥ 0.50 y caben.
- Cuerpo: hasta **800 chars** del doc (mismo recorte que squeeze stage2 / `CANDIDATE_CHARS`). No 200. No el vault entero.
- Incluye: `path`, `title`, `noul`, `source` (semantic|episodic).
- El #1 debe ser el mecanismo de la query/trabajo, no chrome/TUI/MCP wrapper (criterio noul literal de squeeze).

### 3.1.b Pin y dos noul (un HTTP)

- **Pin:** todo path ∈ `work.changed_files` ∪ `work.new_files` nunca se *dropped*. Si noul de cuerpo es bajo, baja a puntero, no desaparece.
- **State.goal:** query del observer (`search_queries[0]` o PR title) + lista de files. Jev ve la *tarea*, no solo el hit.
- **Dos noul por candidato, mismo request** (fan-out de TypeSafe, no dos round-trips):
  - `keep_body` umbral **0.50** → canónico (hace falta el texto)
  - `keep_ptr` umbral **0.25** → puntero (hace falta saber que existe)
- No se resume lo dropeado. No hay question “¿es buena arista?”.

### 3.2 Punteros

Cada puntero es **una línea**, no un excerpt:

```
- <path>  — <rel> — <una línea ≤ 80 chars>
```

`rel` v1, solo si hay arista **validada** desde un canónico:

| rel | Origen de la arista |
|---|---|
| `wikilink` | `[[wiki]]` / links del SemDoc |
| `implements` | path de código ↔ ficha nativa del mismo módulo (heurística de path, no Jev) |
| `constrains` | ADR/spec que el webgraph ya une al canónico |
| `related` | fallback si no hay tipo; **máx 2** `related` por pack |

No se usa co-ocurrencia cruda de archivos en memorias episódicas como arista validada. Si no hay aristas validadas: punteros = el resto de hits con noul ≥ 0.25, `rel=related`, sin inventar vecinos.

Máximo **6 punteros**. Cero cuerpo.

### 3.3 Lo que no va al prompt del agente

- Hits con noul < 0.25.
- `Matched by: topic, files, keywords`.
- Conteos de “4 searches, 32 raw hits”.
- Entity-search dropped (sigue sin convertirse; no se “arregla” metiendo más hits).
- Lista de dropped (eso es log / `--verbose` humano).

### 3.4 Budget

Reemplaza `max_items`/`max_chars` del presenter **solo en el pack**. El enricher nativo puede seguir finalizeando con su budget interno para no romper tests de paridad del bundle crudo.

Pack:

| Zona | Tope |
|---|---|
| Canónicos | 1–2 docs × ≤800 chars |
| Punteros | ≤6 líneas |
| Total prompt | **≤1800 chars** (menos que `max_chars=2000` de blurbs, más señal) |

Si no cabe el segundo canónico, baja a puntero.

Proporcionalidad:

| Señal del observer / query | Pack |
|---|---|
| `question-only` / budget 0 | pack vacío (como hoy) |
| query de explicación, 0 files changed | 1 canónico + punteros; no 2 canónicos |
| PR/diff con files | 1–2 canónicos + aristas desde esos files |

---

## 4. Pipeline (un if)

No se reescribe `ContextEnricher.enrich` ni `observer`.

```
Observer → WorkContext                    ← igual
Enricher.enrich (estrategias + finalize)  ← igual; si pack on, over-fetch
                                           fetch_k = max(max_items*2, 16)
                    │
                    ▼
         purpose context_pack on?
              │ no → to_compact / to_markdown actuales
              │ sí
              ▼
         adapter arma candidates[{id,path,title,text}]
         Choice familia; state.goal = query + files
         Noul keep_body + keep_ptr por candidato (≤16, un HTTP o batches)
         canónicos = keep_body ≥ 0.50 (máx 2), pin de files del trabajo
         punteros = keep_ptr ≥ 0.25 ∪ aristas validadas desde canónicos
         drop el resto (salvo pin)
         si Jev muere → presenter actual
         si nadie pasa umbral → top 3 nativos en formato ACTUAL (fail-safe)
                    │
                    ▼
         pack_to_prompt() / pack_to_markdown()
```

Tres HTTP máx por `cortex context` cuando está on (mismo patrón que search). Timeout 2000 ms. 429/529 retry corto y fail-open.

Jev **no** genera el texto del pack. Solo choice + noul. El adapter ensambla strings.

---

## 5. Grafo: cuándo sí, cuándo no

El webgraph **no** se pinta entero. Solo se consulta vecindario de los canónicos **después** del noul.

```
si no hay índice de grafo / no hay aristas tipadas:
    no se llama al grafo (fail-open a punteros noul-only)
si hay aristas wikilink | implements | constrains:
    se agregan como punteros (dedup por path, máx 6 total)
nunca:
    cosine-neighbor crudo, co-occurrence count, “todos los archivos del mismo folder”
```

Validar una arista en v1 del pack = **ya existe en el modelo de grafo nativo** con tipo ∈ {wikilink, implements, constrains}. No se pide a Jev que invente edges (Jev no inventa docs; tampoco aristas).

---

## 6. Catálogo de questions

Embebido en `cortex-judgement/questions/default.yaml`, no strings sueltos.

- Compass: **las mismas** `FAMILIES` / instructions que squeeze (no reescribir “más lindo”).
- Noul título/cuerpo: **las mismas** instructions/criteria que `squeeze.py` `noul_batch`.
- No hay question nueva de “¿es buena arista?”. Las aristas no pasan por Jev en v1 del pack.

Purpose enum: agregar `ContextPack` (tercero). `enabled(ContextPack)` independiente de search_squeeze. El client HTTP es el mismo.

---

## 7. Superficie

| Superficie | Qué cambia si pack on |
|---|---|
| `cortex context` (markdown/compact) | pack; JSON del bundle crudo puede seguir igual + campo opcional `pack` |
| MCP `cortex_context` | el texto inyectado es pack; **no** tool nueva; golden de 32 tools intacto |
| Brain chat / `session.current` | hereda CLI `context` |
| TUI | no paywall; no pantalla nueva |

`--expand` humano: canónicos sin recorte de 800, punteros igual. Sigue sin dump del vault.

Settings Brain: checkbox `context_pack` al lado de squeeze/promote (mismo panel Inteligencia). Default off.

---

## 8. Tests obligatorios

- YAML sin `context_pack` ≡ off; presenter tests actuales verdes.
- `enrich` con client None = mismo `to_compact` que hoy (fixture de items, sin red).
- Fail-open 429 → compact nativo.
- Payload golden: body a TypeSafe tiene `state` + `questions` (no SDK Python).
- Pack: ≤2 canónicos, punteros sin bloques `> excerpt`, ningún path con noul<0.25, total chars ≤1800.
- Red `#[ignore]` / skip sin key.

Eval fuera de CI (mismo espíritu que squeeze): query poster “checkpoint verification”.

| Métrica | Enricher hoy (esperado) | Pack (objetivo) |
|---|---|---|
| gold en el prompt | a menudo no (wrapper MCP) | sí |
| chars del prompt | ~8×200–300 + metadata | ≤1800, 1 canónico denso |
| #1 path | `sessions.rs` / TUI | `verification` / `quality_gates` nativo |

---

## 9. Archivos (v1 del pack)

Crear / tocar, mínimo:

| Archivo | Qué |
|---|---|
| `cortex-judgement` `Purpose::ContextPack` + `ClientOptions.context_pack` | palanca |
| `questions/default.yaml` | sin reescribir noul/compass |
| `cortex-app/src/context/judgement_pack.rs` | adapter: hits → pack |
| `presenter.rs` | `to_pack_compact` / `to_pack_markdown`; **no** cambiar `to_compact` default |
| `memory_cmds.rs` `run_context` | if pack on, usar pack |
| `cortex-config` `JudgementPurposes.context_pack` | default Off, skip_serializing default |
| Brain settings checkbox | igual que promotion |
| Tests en judgement + app | fail-open + golden pack |

No tocar: `hybrid.rs` RRF, observer, entity_search (sigue dropped), golden MCP, Python deprecado.

---

## 10. Fuera de alcance

- Pedirle a Jev un resumen del pack.
- Subir `max_items`.
- “Arreglar” entity search para meter más hits.
- Co-occurrence como arista validada.
- GraphRAG / community summaries.
- Portar Engram, ODD protocol, SDD, RDD.
- Fail-closed.

---

## 11. Definición de done

1. Purpose `context_pack` default off; sin bloque ≡ community presenter.
2. Con key + purpose on, `cortex context` (o el compact que come el agente) muestra **pack**: 1–2 canónicos con cuerpo útil + punteros de una línea.
3. Fail-open 429 → compact de hoy.
4. Query verification: el canónico #1 no es un wrapper MCP/TUI de session.
5. Tests de default/fail-open/golden pack verdes; sin red en CI.

---

## 12. Relación con search squeeze

Search squeeze reordena `cortex search --json`. El pack es **otra palanca** sobre el enricher (trabajo/PR/files → prompt). Pueden convivir: search sirve al agente que busca; pack sirve a `context` / MCP context / PR comment. No se unifican en un solo purpose (un if por consumer).

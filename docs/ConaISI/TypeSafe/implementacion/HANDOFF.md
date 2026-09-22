# Handoff — TypeSafe / Jev en Cortex

Para un agente **sin historial**. Leé este archivo primero, después el índice, después el código que se liste. No reabrir diseño. No LangChain. No nombres de metodologías de terceros. No Python de Cortex (deprecado). CLI = `cortex` / `cortex-cli` nativo.

**Nombres de producto:** **Direct** = community (Jev off). **JevDD** = Direct + portero Jev. Fast/Deep Track no existen en UX.

**Rama de trabajo:** todo TypeSafe/Jev (P0 pack, P1 portero, P2 copy Direct/JevDD, P3 compactación, P4 webgraph, y lo que falte hasta terminar) se codea en la rama **`typesafe`**. No en `master`. No mergear hasta que el dueño lo pida. Arranque en frío: `git checkout typesafe` (crearla si no existe) y trabajar ahí.

---

## 1. Qué problema estamos resolviendo

El LLM del IDE es caro y se llena de **basura keyword**. Jev (System One) no genera texto: `state` + `questions` (choice / noul / score), ~1.3 s, centavos. Sirve para **elegir**, no para escribir.

Objetivo de contexto: **justo y necesario** — 1–2 docs canónicos + punteros, no 8 excerpts de 200 chars. Gold en el prompt. Tokens de hechos, no de wrappers.

Laboratorio (no lo reimplementes): `/home/chucho/TypeSafeAI/eval/` — `squeeze.py` es la spec ejecutable del ranking. Retrieval siempre fue `cortex search` nativo.

---

## 2. Cómo leer (orden)

| Orden | Path | Para qué |
|---|---|---|
| 0 | **Este handoff** | Hecho vs falta; contexto justo; por dónde codear |
| 1 | [00-indice.md](00-indice.md) | Mapa |
| 2 | [01](01-dos-modos.md)–[06](06-flujos-runtime.md) | Contrato original (fail-open, un crate, un if). **Parcialmente superado** por 07–09 en UX de agentes/tracks |
| 3 | [07-enricher-pack.md](07-enricher-pack.md) | Pack v2 (spec, no código) |
| 4 | [08-direct-y-jevdd.md](08-direct-y-jevdd.md) | Medio sin tracks |
| 5 | [09-portero.md](09-portero.md) | Sesión/memoria/tools sin slash |
| 6 | Código abajo | Lo ya mergeable en el tree |

No leas las 838 fichas de ConaISI ni cookbooks TypeSafe salvo el JSON de `system_one`. No leas `incorporacion-cortex/07–14` salvo contradictions/finish si te toca ese purpose.

---

## 3. Hecho en código (repo Cortex)

Crate y palancas **opt-in, fail-open, default off**. Key **nunca** en YAML/git: env `TYPESAFE_API_KEY` o llavero OS (`cortex.typesafe`).

| Pieza | Dónde | Comportamiento |
|---|---|---|
| Crate `cortex-judgement` | `rust/crates/cortex-judgement/` | Trait, HTTP ureq, catálogo `questions/default.yaml`, squeeze search, `rank_promotion`, resolve key env→keyring |
| Config | `rust/crates/cortex-config/` | `judgement:` opcional; omitir ≡ disabled; `purposes.search_squeeze` + `promotion` |
| Search squeeze | `cortex-cli` `memory.rs` + `judgement_squeeze.rs` | Over-fetch 30 → Choice → Noul títulos → Noul cuerpos → drop noul&lt;0.25. Fail-open a RRF |
| Brain settings | `cortex-brain-app` `judgement_settings.rs` + UI `JudgementSettingsTab.tsx` | Pestaña Inteligencia: toggle, squeeze, promote, pegar key al llavero |
| Promote UI | `org_memory.rs` | Reordena candidatos, campo `noul`. Approve humano **no** se veta |
| Doctor | `cortex-doctor` | Check `judgement` **solo si el bloque existe** |
| CLI | `cortex judgement status` | `disabled` / `typesafe` / `degraded` |

**En rama `typesafe` (P0 pack, cerrado):** `Purpose::ContextPack`, `judgement.purposes.context_pack` default off, `pack_context` (fail-open), `judgement_pack.rs` + `to_pack_compact`/`to_pack_markdown` (no se tocó `to_compact`), `cortex context` if pack on, checkbox Brain, MCP `cortex_context` inyecta pack (off/429 ⇒ `to_prompt_format` nativo; golden de 32 tools intacto).

**No está en código:** portero `utterance` (P1), borrar Fast/Deep de skills (P2), compactación de historial (P3), webgraph noul (P4), guardrail.

Verificación hecha: `cargo test -p cortex-judgement -p cortex-config -p cortex-cli --lib` + doctor_core + brain-app lib. Setup YAML **no** inyecta el bloque (paridad Python). Live search con key no se corrió en el entorno de implementación (no había `TYPESAFE_API_KEY`).

---

## 4. Contexto justo y necesario (la regla)

Si vas a tocar retrieve, enricher o prompts, esta es la brújula. No “más items”.

```
over-fetch nativo
    → Jev noul (batch, un HTTP)
    → 1–2 canónicos con cuerpo (~800 chars)
    → punteros de una línea (path + rel + ≤80 chars)
    → drop noul bajo / tool results irrelevantes
    → NUNCA resumir lo que se tira
```

| Superficie | Hoy | Objetivo |
|---|---|---|
| `cortex search` | Squeeze **hecho** | No reescribir BM25/RRF |
| `cortex context` / MCP context | 8 blurbs 200–300 chars, `min_score=0.1` | Pack **07** |
| Episódico | Remember sin criterio | Portero `worth_remembering` **09** |
| Brain transcript | JSON de tools se acumula | `session_compact` (después de 07 y 09) |
| Pregunta vs ticket | El humano elige sync | Portero **09** |

Fail-open siempre: 401/429/529/timeout → ranking o transcript nativo. Nunca search/context/sesión vacíos por Jev.

Jev no genera texto, no muta vault, no elige el siguiente paso del agente de código. El harness sí abre/cierra sesión cuando Jev clasifica el acto.

---

## 5. Trabajo a realizar (orden)

No paralelizar 1–4. Cada uno es un if + tests. Default off.

### P0 — Pack enricher (spec 07)

**Done cuando:** `context_pack: on` + key ⇒ `cortex context` imprime pack (canónico + punteros); off ⇒ `to_compact` bit-idéntico; 429 ⇒ compact nativo; query verification no pone wrapper MCP/TUI de session como canónico.

**Archivos:** `Purpose::ContextPack`, `JudgementPurposes.context_pack`, `cortex-app/src/context/judgement_pack.rs`, `presenter.rs` **sin** cambiar `to_compact` default, `memory_cmds.rs` `run_context`, checkbox Brain, tests.

**No tocar:** `hybrid.rs` RRF, observer, entity_search dropped, golden MCP, Python.

### P1 — Portero utterance (spec 09)

**Done cuando:** “cómo funciona X” no abre sesión ni remember; “arreglá Y” abre sesión si no hay; 429 no abre sesión; Direct sin purpose ≡ hoy.

**Archivos:** purpose `utterance`; hook al inicio del chat Brain / dispatch de skills (un if); `remember` gated; **no** borrar crates de session/documenter.

### P2 — Direct / JevDD en skills (spec 08)

**Done cuando:** skills SDDwork no dicen Fast/Deep Track; default “hacer”; subagentes solo a pedido.

**Archivos:** `cortex/setup/workspace_files/cortex-SDDwork.md` y espejos `.cortex/skills/`; Autopilot no mapea a “Deep” en copy. Código de detectores puede quedar; la **UX** cambia.

### P3 — Compactación de historial (después)

Tool results de Brain: noul keep_call / keep_result, pin últimos N, **verbatim** (no summary). Purpose `session_compact`. Fail-open = transcript intacto. No mezclar con P0.

### P4 — Webgraph noul

Solo vecindario de canónicos, aristas ya tipadas. Spec 07 §5. Después de P0.

---

## 6. Cómo arrancar en frío (P0)

```
0. `git checkout typesafe` (crear si no existe). P0–P4 viven en esa rama, no en master.
1. Leé HANDOFF + 07 enteros.
2. rust/crates/cortex-judgement — no UnifiedHit.
3. rust/crates/cortex-app/src/context/{mod.rs,presenter.rs} — enganchá DESPUÉS de finalize.
4. rust/crates/cortex-cli/src/memory_cmds.rs run_context.
5. TDD: pack tests primero (fail-open, omitido ≡ compact actual, golden keys state/questions).
6. cargo test -p cortex-judgement -p cortex-app -p cortex-cli --lib
7. No pytest del paquete cortex/. No commits de keys.
```

HTTP: `POST https://api.typesafe.ai/v1/systemone`, Bearer `$TYPESAFE_API_KEY`, model `jev-1.13.0`, body `{state, model, questions}`. Output tokens no se cobran; loguear `usage.input_tokens`.

---

## 7. Prohibido

- LangChain, `langchain-typesafe`, middleware de terceros.
- Nombrar en producto metodologías ajenas.
- Python Cortex, PyO3 para Jev, binario `cortex-pro`.
- Tool MCP nueva / reordenar el golden de 32.
- Paywall en TUI.
- Fail-closed. Guardrail default-on.
- Resumir con LLM lo que Jev dropea.
- Reescribir BM25, RRF, Neumaier.
- Que Jev escriba session notes o llame MCP.
- Fast Track / Deep Track en copy nueva.

---

## 8. Config de referencia

```yaml
# omitir el bloque = Direct
judgement:
  enabled: false
  provider: none          # none | typesafe
  model: jev-1.13.0
  timeout_ms: 2000
  fail: open
  api_key_env: TYPESAFE_API_KEY
  purposes:
    search_squeeze: off   # código: search
    promotion: off        # código: org memory ranking
    context_pack: off     # spec 07
    # utterance: off      # spec 09 — aún no está en el struct
```

Key: env o llavero. Brain → ⚙ → Inteligencia.

---

## 9. Mapa de código caliente

```
rust/crates/cortex-judgement/     puerto HTTP + squeeze + rank_promotion + auth
rust/crates/cortex-config/        JudgementConfig
rust/crates/cortex-cli/src/memory.rs              retrieve + squeeze
rust/crates/cortex-cli/src/judgement_squeeze.rs   adapter search
rust/crates/cortex-cli/src/memory_cmds.rs         search --json, run_context
rust/crates/cortex-app/src/context/               enricher + presenter  ← P0
rust/crates/cortex-brain-app/src/judgement_settings.rs
apps/brain-ui/src/components/JudgementSettingsTab.tsx
rust/crates/cortex-brain-app/src/org_memory.rs    noul promote
```

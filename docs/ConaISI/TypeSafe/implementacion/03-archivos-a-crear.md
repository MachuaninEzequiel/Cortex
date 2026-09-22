# Archivos a crear

Nada de esto está escrito en el repo todavía. Lista para un futuro PR, partida en **crate nuevo** vs **ganchos de 5 líneas** vs **no tocar**.

Convención: el CLI nativo es el producto; Python se porta en paralelo como librería (oráculo / `AgentMemory`). Si hay que elegir un solo stack para v1: **Rust**, porque `cortex-cli` ya no delega a Python.

---

## A. Crate nuevo — `rust/crates/cortex-judgement/`

```
rust/crates/cortex-judgement/
  Cargo.toml                      # deps: serde, serde_json, thiserror; ureq detrás de feature typesafe
  src/lib.rs                      # reexportes; JudgementClient trait
  src/purpose.rs                  # enum Purpose
  src/request.rs                  # JudgementRequest / Response / Usage
  src/error.rs
  src/config.rs                   # JudgementConfig (serde, paridad con YAML)
  src/catalog.rs                  # carga questions.yaml, valida IDs
  src/null.rs                     # impl que enabled()=false y evaluate()=Err(Skipped)
  src/typesafe/
    mod.rs
    client.rs                     # POST /v1/systemone, retries 429/529
    auth.rs                       # TYPESAFE_API_KEY / config.api_key_env
  questions/
    default.yaml                  # catálogo embebido (include_str!)
  tests/
    payload_golden.rs             # body HTTP canónico
    catalog_load.rs
    fail_open.rs
```

`Cargo.toml` del workspace: agregar el crate a `members`.
`cortex-app/Cargo.toml`: `cortex-judgement = { path = "...", default-features = false }`.
Feature `typesafe` se prende en `cortex-cli` / `cortex-mcp` / `cortex-brain` si se quiere el client en el binario. Recomendación v1: feature default en cli/mcp.

**No** depende de `cortex-app`, `cortex-core`, `cortex-mcp`.

---

## B. Config — paridad Python/Rust

Ya existe el patrón: `CortexConfig` en `cortex/core.py` y `cortex-config` (porteo serde, `parity_fixtures.rs`).

Crear / tocar:

| Archivo | Qué |
|---|---|
| `cortex/core.py` | modelo Pydantic `JudgementConfig` + campo opcional en `CortexConfig`. Default `enabled=False` |
| `rust/crates/cortex-config/src/lib.rs` | mismo struct, fixture de paridad |
| `cortex/setup/templates.py` | bloque comentado en el YAML que genera `cortex setup` |
| `tests/` de config | default omitido ≡ disabled (bit-idéntico a configs viejas **sin** el bloque) |

Bloque (default de fábrica = ausente; si se escribe, esto):

```yaml
# judgement:                      # opcional — omitir = Cortex community
#   enabled: false
#   provider: none                # none | typesafe
#   model: jev-1.13.0
#   timeout_ms: 800
#   fail: open
#   api_key_env: TYPESAFE_API_KEY
#   purposes:
#     retrieval_rerank: off
#     query_intent: off
#     contradictions: off
#     adr_suggest: off
#     quality_gate: off
#     autopilot: off
#     brain_intent: off
#     promotion: off
#     next_action: off
#     remember: off
#     guardrail: off
```

Configs existentes **sin el bloque siguen válidas**. Eso es no romper a quien no paga.

Workspace file generado (solo si el usuario dice yes en setup):

```
.cortex/judgement/questions.yaml      # copia del default, editable
.cortex/judgement-events.jsonl        # gitignore (como enrichment-events)
```

`.gitignore` template de setup: agregar `judgement-events.jsonl`.

---

## C. Adapters (traducen tipos Cortex ↔ JSON)

Viven **al lado del consumer**, no en el crate judgement.

### Rust (`cortex-app`)

| Archivo nuevo | Consumer |
|---|---|
| `src/context/judgement_rerank.rs` | post-RRF |
| `src/context/judgement_intent.rs` | pre-RRF, opcional |
| `src/documenter/judgement_contradictions.rs` | impl ContradictionDetector |
| `src/documenter/judgement_adrs.rs` | wrap `suggest_adrs` |
| `src/session/judgement_quality.rs` | stage 2 |

### Rust otros crates

| Archivo | Crate |
|---|---|
| `src/judgement_detect.rs` | `cortex-autopilot` |
| `src/judgement_route.rs` | `cortex-brain` |
| `src/judgement_promote.rs` | `cortex-enterprise` |
| `src/judgement_next.rs` | `cortex-actions` |

v1 **solo crea** `judgement_rerank.rs` + wiring. El resto son files vacíos/no existentes hasta el purpose correspondiente. Modular = no abrir 8 PRs de una.

### Python (espejo, librería)

| Archivo nuevo | Dónde |
|---|---|
| `cortex/judgement/__init__.py` | factory `build_judgement_client` |
| `cortex/judgement/client.py` | wrapper typesafe-sdk, import diferido |
| `cortex/judgement/catalog.py` | YAML |
| `cortex/judgement/config.py` | si no vive todo en `core.py` |
| `cortex/retrieval/judgement_rerank.py` | adapter |
| `cortex/documenter/typesafe_contradiction.py` | impl del Protocol |

`pyproject.toml`: optional-dep `typesafe = ["typesafe-sdk"]`.

---

## D. Ganchos de 5–15 líneas (archivos existentes)

Estos **sí** se tocan, y tienen que ser mínimos para no ensuciar paridad.

| Existente | Cambio |
|---|---|
| `cortex/retrieval/hybrid_search.py` | `if judgement and enabled(rerank): hits = rerank(...)` |
| `cortex-app/src/context/hybrid.rs` | igual |
| `cortex/documenter/reconstruction.py` | ya inyecta `ContradictionDetector`; pasar el impl TypeSafe o NoOp |
| `cortex/core.py` `AgentMemory.__init__` | construir client, inyectar |
| `cortex-cli` doctor | un check nuevo |
| `cortex-cli` setup | una pregunta opcional |
| `cortex-doctor` | check nativo espejo |
| `cortex-setup` templates | bloque YAML comentado |
| `.gitignore` / git_policy templates | jsonl |

**No tocar:** `cortex-core`, `tools_catalog.rs`, golden MCP, BM25, cosine, `quality_gates` stage 1, `VerificationRunner`, tutor content, Brain tools table (Read/SafeAction).

---

## E. Superficie de usuario (mínima)

| Archivo | Qué |
|---|---|
| `cortex-cli/.../judgement_cmds.rs` (nuevo) | `cortex judgement status \| ping \| enable \| disable` |
| `cortex/cli/` espejo Typer, hidden o experimental | misma semántica |
| `cortex-doctor` check `judgement` | disabled / ok / enabled-but-no-key / typesafe-unreachable |
| `agent_guidelines.md` (package-data) | **un párrafo condicional** o generado por `cortex agent-guidelines` si enabled |

No hay tool MCP nueva (golden). `cortex_search` mejora por dentro.

---

## F. Tests

| Test | Qué demuestra |
|---|---|
| `config_omitted_equals_disabled` | YAML viejo ≡ community |
| `hybrid_search_without_client_is_bit_identical` | el `if None` no cambia RRF |
| `payload_golden` Python vs Rust | mismo JSON al API |
| `fail_open_on_429` | search vuelve hits RRF |
| `purpose_off_skips_http` | mock HTTP 0 calls |
| eval nDCG (fuera del paquete, `TypeSafeAI/` o `eval/`) | no CI-blocking, necesita key |

Los `*_parity.rs` de core **no se tocan**.

---

## G. Qué no crear

- Un crate `cortex-typesafe` con lógica de retrieval adentro.
- Un segundo HybridSearch.
- Un binario `cortex-pro`.
- Tools MCP `cortex_rerank`.
- UI de paywall en TUI/Brain.
- Proxy de API keys en enterprise.
- Reimplementación del lexicon dentro de judgement (duplicaría modo A).

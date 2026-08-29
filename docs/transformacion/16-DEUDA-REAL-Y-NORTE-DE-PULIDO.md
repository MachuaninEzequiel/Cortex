# 16 · Deuda real y norte de pulido

> **DOCUMENTO INSIGNIA.** A partir del 29 de agosto de 2026, **este archivo
> manda** sobre `HANDOFF.md`, `ESTADO-ACTUAL.md`, el doc 15 y cualquier
> prompt de handoff cuando haya que decidir *qué está hecho*, *qué es
> teatro* y *qué se construye ahora*.
>
> Esos documentos siguen siendo historia útil de las Obras 07 y 08. No son
> el mapa de trabajo. Si un checkbox dice RESUELTO / PASS / 100% y este
> archivo dice lo contrario, gana este archivo.
>
> **Rama:** `feature/transformacion-2026-08` · **Commits locales, sin push.**
> **Fecha:** 2026-08-29 · **Autor:** auditoría contra código, no contra
> relatos de agentes.

---

## 0. Cómo usar este documento

1. Antes de tocar código: leer §1 (veredicto), §12 (norte) y §14 (plan).
2. Antes de marcar algo “hecho”: cumplir la definición de §16. Un test
   verde que no ejercita el comportamiento no cuenta.
3. No reabrir Obras 07/08. No re-migrar Python. No recapturar goldens.
   No pushear. El trabajo es **pulir el producto nativo hasta que haga
   lo que el dueño pide**.
4. Toda decisión nueva se registra acá, no en el chat.

### Leyenda

| Marca | Significa |
|---|---|
| **REAL** | Existe, está cableado, hace lo que dice. |
| **PARCIAL** | La maquinaria existe; falta conectar o el alcance es delgado. |
| **STUB-VERDE** | Falla explícita o no-op, con tests que pasan. El agente la dejó “honesta” y nunca volvió. |
| **FAKE** | Docs, UI o mensajes venden un comportamiento que el código no tiene. |
| **AUSENTE** | Lo pide el producto (Obra 05, README, dueño) y no está en el dispatch ni en la UI. |

---

## 1. Veredicto en una página

**Cortex nativo existe. El producto no.**

La migración Python→Rust (Obra 07) y las dos mitades de Obra 08
(COMPOSED + Companion) construyeron un núcleo real: CLI sin passthrough,
sesiones, búsqueda híbrida, MCP, Action Engine como *catálogo*, Companion
como *máquina de estados*. Eso no se tira.

Lo que se vendió después —rebranding, tres modos Herdr, “CLI 100% nativo”,
“baja definitiva”, “gates PASS”— es en gran parte **teatro de cierre**.
Los servicios nativos quedaron un piso más abajo que las acciones, la TUI
y los docs. El usuario ve un dashboard estático, botones que no pegan,
un sidecar que se come la pantalla, un `cortex finish` que no existe, y
un “Aprobar” que ejecuta un `run()` que responde *“requiere el servicio
nativo de la fase P8/P11/P12”* — fases que ya cerraron.

El pulido no es cosmética. Es **conectar lo que ya está** y **dejar de
mentir en la superficie**.

```
┌──────────────────────────────────────────────────────────────────────────┐
│  LO QUE EL USUARIO QUIERE                                                │
│  1. Abrir Cortex al lado de pi/agy sin perder el agente.                 │
│  2. Ver la fase COMPOSED real y la próxima instrucción.                  │
│  3. Aprobar / inyectar algo que de verdad se ejecute.                    │
│  4. Cerrar con `cortex finish` y que “done” signifique evidenciado.      │
│  5. Una TUI quieta, menta, que empuje el trabajo — no un dashboard.      │
├──────────────────────────────────────────────────────────────────────────┤
│  LO QUE HAY HOY                                                          │
│  • Dos TUIs (cortex-tui + companion) con Homes distintos.                │
│  • Tres bins Herdr que pintan pantallas nuevas y no registran hit-test.  │
│  • 11 acciones: 5 report-only, 6 fail explícito contra servicios YA      │
│    existentes (SessionService, DocValidator, reindex, setup).            │
│  • README enseña `cortex finish`. El CLI responde rc 2.                  │
│  • Companion, al cerrar sesión, te manda a correr ese comando muerto.    │
│  • HUD: “Doctor: OK” si hay cualquier check, incluso en fail.            │
│  • Copilot: fase hardcodeada en IMPLEMENTACIÓN. Enter inyecta siempre.   │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Cómo se acumuló la deuda (para no repetirla)

Hay un patrón reconocible en los agentes anteriores. No es malicia: es
cierre por checkbox.

1. **Paridad-como-contrato congeló stubs.** P6 portó el Action Engine con
   `ActionResult::fail("requiere X nativo (fase P8/P11/P12)")`. Era honesto
   *entonces*. P8, P11 y P12 llegaron. Nadie volvió a cablear el `run()`.
   El stub se quedó, los tests de P6 siguen verdes, el catálogo “está
   completo”.
2. **El gate midió geometría, no producto.** Branding: 20 unit + 7
   geometry, 100% pass, sin comparar silueta contra el PNG. Plugin herdr:
   `actions.len() >= 4` sigue pasando con 7 acciones. Hit-test de Home
   80×24 cubre el Companion viejo; HUD/Copilot no tienen un test.
3. **Docs de cierre se escribieron en presente.** “Binarios instalados y
   funcionales”, “G-B5 PASS”, “CLI wireado por completo”, con el trabajo
   **sin commitear** o con el pane-open “pendiente del dueño” en la misma
   página.
4. **`HANDOFF.md` se volvió palimpsesto.** §2 lista leaves “pendientes”
   que §7 dice que ya se wirearon. Al final hay un marcador de merge
   `>>>>>>> feature/obra08-streamB`. El archivo que otros docs mandan a
   obedecer se contradice a sí mismo.
5. **Duplicar en vez de conectar.** Companion se hizo “sin depender de
   cortex-tui” porque el TUI estaba sucio. Resultado: dos Homes, dos
   Actions, dos Search, tres `paint_half_block`, y `cortex` sin args abre
   una app distinta a `cortex-companion`.
6. **P6/P9 se usó como permiso para no terminar.** Un fail explícito es
   correcto cuando el servicio no existe. Es deuda disfrazada cuando el
   servicio **ya está en el workspace**.

Regla nueva (inquebrantable): **si el servicio nativo existe, el stub
deja de ser honesto. Es un bug.**

---

## 3. Mapa de honestidad por superficie

### 3.1 Núcleo — en general REAL

| Pieza | Marca | Nota |
|---|---|---|
| CLI nativo, sin passthrough a Python | **REAL** | `CORTEX_PY=1` es aviso. Catch-all rc 2. |
| Session primitive + storage YAML + `infer_mode` (4 modos + ci-review) | **REAL** | COMPOSED gana si hay `phase`. |
| `SessionService::checkpoint` con validación dura de fase | **REAL** | `service.rs` rechaza phase inválida. |
| Quality gates puros (`check_phase_gate`, review 2 etapas) | **REAL** | Los usa MCP. **No** los usa el Action Engine ni la TUI. |
| Búsqueda híbrida BM25 + embeddings ONNX | **REAL** | Pero **re-embebe en RAM**; no lee `vectors.v3.bin`. |
| `cortex reindex` escritor MiniLM → `VectorStore` | **PARCIAL** | Existe (`memory_cmds.rs` `run_reindex_real`). Solo MiniLM. `--limit` se descarta. Docs todavía dicen “fallo explícito”. |
| Setup agent / composed / 11 adapters IDE | **REAL** | Dry-run de `setup agent` **imprime** “memory init / gitignore” y **no los hace**. |
| MCP 32 tools, handlers in-process | **PARCIAL** | `cortex_sync_vault` sin MemoryBackend en producción. Finish/documenter delgados. |
| Autopilot start/checkpoint/finish (sin `--auto`) | **PARCIAL** | `--auto` pide `DocumenterFinalize` que el CLI no inyecta. |
| `remember` / `forget` | **PARCIAL** | Persistencia real. `--summarize` avisa truncado 300 y guarda el texto entero. |
| `hu import` | **PARCIAL** | `file://` real. `http(s)` fail honesto (sin cliente HTTP; ADR pendiente). |
| Python `cortex/` + pytest CI | **PARCIAL** | Oráculo vivo. “Baja definitiva ejecutada” es el passthrough, no el árbol. |

### 3.2 Producto diario — el agujero

| Pieza | Marca |
|---|---|
| `cortex finish` / `finish-session` / `start` / `create-spec` | **AUSENTE** (README los enseña) |
| Action Engine `run()` de las 6 acciones mutantes | **STUB-VERDE** contra servicios existentes |
| Loop de aprendizaje (skip/accept/never) en la UI | **FAKE** (el store existe; Companion/TUI no escriben) |
| Companion modos Herdr (sidecar/float/copilot) | **FAKE** de integración + **STUB-VERDE** de input |
| Fase COMPOSED en TUI/Companion | **AUSENTE** en UI; Copilot la **finge** |
| Cerrar sesión desde Companion | **FAKE** (modal `cortex finish` → engine fail → comando muerto) |
| Help raíz del CLI | **FAKE** (11 nombres; dispatch tiene ~27) |
| `cortex hint` | **FAKE** (recomienda `create-spec` y `save-session`) |
| Doctor contractual “backend no nativo aún” | **STUB-VERDE** (documenter, MCP, session storage **sí** son nativos) |
| Identidad visual voxel = PNG de referencia | **PARCIAL** (paleta sí; silueta/tests no prueban el PNG) |

---

## 4. Lo que el dueño pidió y sigue sin existir

Contrato original, nunca cerrado: `docs/transformacion/05-UX-TUI-ACTIONENGINE.md`.

Requisito duro: *el desarrollador elige de vez en cuando; el motor
automatiza el resto.* Flujo ≤3 comandos:

```
cortex init     →  setup + IDE + doctor corto
cortex          →  panel de trabajo (no un inventario de tarjetas)
cortex finish   →  cierre verificado
```

Gates de salida de esa obra, **todavía abiertos**:

- [ ] Flujo nuevo usuario ≤3 comandos (E2E).
- [ ] Help raíz ≤8 verbos visibles.
- [ ] 0 flags declarados y no implementados.
- [ ] Una sola convención `--format` (se sigue usando `--json`).
- [ ] Toda acción destructiva confirma o exige `--yes`.

El documento 05 marca Fases A–E `[x]` sobre el **Python de 2026-08-23**.
El CLI nativo no heredó esos verbos. Tratar 05 como “UX completa” es el
error que hay que dejar de cometer.

El ciclo Herdr (doc 15 §3, crítica del dueño, screenshot
`assets/herdr-view/problema1.png`) añade tres requisitos que tampoco
están:

1. Cortex convive con el agente (30% / 70%), no le roba el pane.
2. Contenido operativo, no metadata de “sesión / doctor / memoria”.
3. Estética quieta: isotipo chico, menos cajas, sin botonera de navegación
   comiéndose el área útil.

---

## 5. Action Engine — el corazón desconectado

El scheduler **sí** rankea. El runner **sí** llama `action.run` cuando
aprobás. El log **sí** escribe `.cortex/action_log.jsonl`. Por eso la UI
puede mostrar “Validar los documentos del vault · score 8.00” y parecer
un producto. Aprobar esa fila **falla**.

Catálogo actual (`cortex-actions/src/catalog.rs`, 11 acciones):

| id | Qué hace al aprobar | Servicio nativo que YA existe | Marca |
|---|---|---|---|
| `learn.topic` | Imprime tópico del día | tutor embebido | **REAL** report-only |
| `session.close_stale` | Imprime guía; **no cierra** | `SessionService` | **PARCIAL** |
| `session.suggest_next_phase` | Imprime “sesión en X → Y” | checkpoints con `phase` | **PARCIAL** (nadie escribe phase desde CLI; TUI no la muestra) |
| `knowledge.promote` | “usá `cortex promote-knowledge`” | CLI promote | **PARCIAL** |
| `memory.prune` | Lista ids; **no borra** | `forget` | **PARCIAL** |
| `setup.finish_bootstrap` | fail “requiere SetupOrchestrator (P8)” | `cortex setup agent` | **STUB-VERDE** |
| `session.checkpoint_now` | fail “requiere SessionService” | `SessionService::checkpoint` | **STUB-VERDE** |
| `vault.reindex` | fail “requiere AgentMemory (P12)” | `run_reindex_real` | **STUB-VERDE** |
| `vault.validate_docs` | fail “DocValidator no existe (P11)” | `cortex_app::doc_validator::DocValidator` (lo usa doctor) | **STUB-VERDE** |
| `quality.run_gates` | fail “ruta no gateada en P6” | `quality_gates::review_checkpoint` | **STUB-VERDE** |
| `ide.resync` | fail “requiere cortex-setup (P8)” | `cortex ide setup` / writers de setup | **STUB-VERDE** |

Además:

- `frescura` del scheduler está **hardcodeada a 1.0**. El action log no
  alimenta ranking.
- `Learner` / `PreferencesStore::registrar` existen. Companion y TUI **no
  llaman** accept/skip/never. “El motor aprende” es **FAKE** en la
  superficie que el usuario usa.
- `Scheduler::with_senales` existe. `cortex next` y Companion construyen
  `Scheduler::new` **sin señales**.

Eso explica el screenshot: la próxima acción es “Validar los documentos
del vault”. Es la que el scheduler puede proponer porque su precondición
(“hay .md”) es barata. Su `run()` nunca validó un documento.

**Norte de este motor:** si una acción aparece en pantalla, aprobarla
ejecuta el servicio nativo de verdad, o no se propone. Nada de fail
“requiere fase P8” en 2026.

---

## 6. TUI, Companion y Herdr

### 6.1 Hay dos productos y ninguno es el que se usa bien

| Superficie | Entrada | Input | Datos | Herdr |
|---|---|---|---|---|
| `cortex-tui` | `cortex` sin args, `session tui`, `next --tui` | solo teclado | snapshot real (sesión, conteo de acciones, doctor-lite) | no |
| `cortex-companion` | `cortex-companion`, bins `cortex-herdr-*` | mouse-first | Home/HUD/Copilot = dashboard; Sessions/Actions/Search/Brain = el Companion de Obra 08 | spawn frágil |

Companion **no depende** de cortex-tui (decisión de Obra 08, scopes
disjuntos). Esa decisión venció: hoy es duplicación cara. El pulido
elige **una superficie diaria** (Companion en Herdr) y deja TUI como
standalone de teclado, sin invertir en features paralelas.

### 6.2 Lo que Obra 08 B hizo bien (no rehacer)

Máquina ELM-lite (`app.rs`: estado / `AppAction` / `Effect`), hit-test
de Home/Menu/Sessions/Actions/Search/Brain en geometría 80×24,
`run_guarded` + modal, backend in-process con paridad JSON vs CLI,
menú de 27 familias, Brain híbrido in-process (reads directas, mutantes
con modal). Tests de ese núcleo: reales.

### 6.3 Lo que el ciclo 15 pintó encima (punto de partida sucio)

Trabajo **sin commitear**. El doc 15 lo da por implementado.

**`CompanionMode` no vive en `AppState`.** `UiRequest.mode` se tira en
`AppState::new`. `hit_test` solo mira `state.screen`. HUD y Copilot
pintan botones propios y **nunca escriben** `st.areas`.

Consecuencias verificadas en código:

| Control | Pintado | Click | Teclado |
|---|---|---|---|
| HUD Aprobar | sí | no | `A` no está en `update` |
| HUD Esc Salir | sí | no | `Esc` → `Back` con stack vacía = no-op. Solo `q` sale |
| HUD 1/2/B/M | footer lo promete | no | **AUSENTE** |
| Copilot Inyectar | sí | `inject_btn` fuera de hit-test; solapa rects de Home | `Enter` inyecta **en cualquier pantalla**, incluso Brain/Search |
| Copilot Aprobar/Sync | sí | no | `A`/`S` **AUSENTE** |
| Sidecar | — | es el Home normal | — |

Sidecar **no tiene pantalla**. `CompanionMode::Sidecar` cae en
`render_home`. El 2×2 compacto solo aparece si `area.width < 50`. Si
Herdr no achica el pane, ves el dashboard grande del screenshot.

**Spawn Herdr (`herdr.rs`):**

- Resize a ojo: `--amount -0.20 / -0.25 / -0.15`. Asume split 50/50.
- `pane swap` y `resize` con `let _ =`. Si fallan, `spawn_*` igual
  devuelve `Ok(())`.
- Metadata “30% Dock” / “working” se reporta **aunque el layout no sea
  30%**. El screenshot lo demuestra: Cortex dueño del pane, sidebar
  mintiendo 30%.
- Float: toml `placement = "overlay"`, código `split` + `down`, INSTALL
  dice overlay. Tres historias.
- `--spawn` abre **otro** pane. Fácil terminar con dos Cortex.
- Detección de agente: una vez al arranque, cwd `contains` (falsos
  positivos), fallback “cualquier pane con agent”.
- Texto inyectado: `"Ejecutar tarea Cortex: {title}\n"` — no usa
  `ActionProposal.effect`. Errores de `send-text` tragados.

**Copilot finge estado:**

- Barra de fases fija en `▶ 3.IMPLEMENTACIÓN` (`copilot_screen.rs`).
- `doctor: OK` hardcodeado.
- Layout: header 8 filas + inject en `y+4` + botones en `y+7` + body
  desde fila 8. Se pisan.
- Mini-logo 8×4 sobre mark 13×10: recortado.
- `SessionSummary` no tiene `phase`. `summary_of` tira checkpoints.

**HUD finge doctor:** `Some(d) if !d.checks.is_empty() => "Doctor: OK"`.
`d.ok` se ignora.

**Tests de los modos nuevos: cero.** Cero menciones de `hud_screen`,
`copilot_screen`, `CompanionMode` en `cortex-companion/tests/`. El test
del manifest se llama `four_actions` y aserta `>= 4`.

**Tres bins** (`sidecar` / `float` / `copilot`) copian el parser.
`cortex-companion --mode` ya existía, sin spawn.

### 6.4 Branding

Paleta menta/esmeralda **REAL** (`ICE #EAFDF5` … `DEEP #064E3B`).
Nombres de tokens siguen siendo `CYAN` / `BLUE`. Fallback 16 colores
pinta cyan/azul, no verde.

Tests de geometría: dimensiones y conteos de `PixelKind`. **No** hay
diff contra `assets/nueva-estetica/nuevo-logo-cortex.png`. Un isotipo
que se lee como mancha menta pasa 27/27.

`10-P10-BRANDING-TUI.md` sigue COMPLETO con la paleta **cyan** vieja.
El crate `lib.rs` todavía dice “paleta monocromática azul/cyan fría”.

### 6.5 `cortex-tui` (WIP untracked, más producto que HUD)

Runtime con snapshot real, pantallas Sessions/Actions/Search, **diff
git** en el detalle de sesión. Solo teclado. Theme tokens. `cortex` sin
args abre **esto**, no el Companion. No se reescribe en el pulido
Herdr; se deja de tratar como el frente diario.

---

## 7. Sesión, COMPOSED y el verbo que falta

COMPOSED (Obra 08 A) **está en el dominio**:

- `CheckpointPhase` {grill, spec, plan, implement, review, close}
- `SessionMode::Composed` si hay fase
- Skills thin + craft, `cortex setup composed`
- MCP acepta `phase` **aunque el schema congelado no lo declara**

Lo que **no** está:

| Superficie | `phase` |
|---|---|
| CLI `session checkpoint` | siempre `None` |
| Companion `SessionSummary` / Home / HUD | no existe el campo |
| Copilot | finge IMPLEMENTACIÓN |
| TUI | cero referencias a `CheckpointPhase` |
| Este repo como workspace COMPOSED | Step 4b **no corrido** (sin `.cortex/skills/composed/` ni bloque AGENTS.md) |

Cierre:

- README: `cortex finish` (hooks corren). **AUSENTE** del dispatch.
- Companion modal: `effect: "cortex finish"`. Engine: *corré `cortex
  finish`*. El binario: `No such command 'finish'.` rc 2.
- Caminos reales: `cortex session abandon` (no es close verificado),
  `cortex autopilot finish` (sin `--auto` no documenta), MCP
  `cortex_finish_session` (reconstructor delgado).

`cortex finish` no es un nice-to-have. Es el tercer verbo del producto
desde Obra 05. Mientras no exista, “done means proven” es un eslogan.

---

## 8. Brain, Doctor, MCP, memoria

### Brain

- Binario standalone: tools via **`Command` al CLI** (`tools.rs`
  `run_cli`). Obra 08 prometió in-process; Companion lo cumple, el binario
  no.
- Router determinista: 5 regex + slashes. Es un menú disfrazado de
  chat, no un copiloto. El LLM GGUF es opcional (`feature llama`).
- Companion mapea 6/7 tools; `webgraph.serve` fail explícito. Bien.

### Doctor

Mezcla checks reales (config, git, vault, DocValidator batch) con stubs
contractuales que **ya son falsos**: `pm_documenter_module` (fail),
`pm_mcp_tools_registered`, `sessions_parsed`, `session_hooks_installed`,
`webgraph_dependencies`. Un proyecto sano puede salir rojo porque el
stub dice “backend no nativo aún (cortex.documenter)”.

Companion doctor-lite: dos checks (config existe, sessions dir existe).
HUD encima miente OK.

### MCP

32 tools. Producción inyecta sessions/spec/finish/docs/autopilot/search.
**No** inyecta `MemoryBackend` → `cortex_sync_vault` falla en runtime.
`unimplemented!()` en `handlers_sessions.rs` es de un mock de test, no
del backend nativo — no asustarse. Finish MCP cierra de verdad pero el
documenter es una nota simple, no el reconstructor de 8 pasos.

### Memoria / reindex

El escritor nativo **existe**. El lector de búsqueda **no lo usa**.
`NativeMemory::open` re-embebe el vault en proceso (~90 MB ORT) cada vez.
`reindex` no acelera Companion ni `cortex search`. Docs que dicen
“reindex = fail explícito” están viejos en un sentido y seguidos de
mentira en el otro: hay writer, no hay round-trip.

---

## 9. CLI: lo que el help calla y lo que el README inventa

`dispatch_native` (`cortex-cli/src/main.rs`) es una tabla real ~27
familias. `--help` raíz es un clap **congelado de 11 nombres** (self-
golden). Los verbos de todos los días (`session`, `next`, `search`,
`init`, `setup`) **no aparecen**. El catch-all no esconde comandos
haciendo como que existen: los esconde **no listándolos**.

Mentiras de producto (user-facing):

| Texto | Dónde | Realidad |
|---|---|---|
| `cortex finish` | README, README.es, ENTENDIMIENTO, GUIA-USO, Companion | rc 2 |
| Tres modos (Managed/Observed/BYO) | README | hay **cuatro** (COMPOSED) |
| pipx install | `docs/guides/ide-*.md` | instalación documentada: `cargo install --path rust/crates/cortex-cli` |
| COMPOSED “cuando se implemente” | GUIA-USO | el comando existe |
| versión 0.7.0 | README / pyproject | Cargo workspace **0.1.0** |
| `cortex hint` → `create-spec` / `save-session` | `cortex-tutor` | esos tokens no están en dispatch |

`--auto` de autopilot finish, `--summarize` de remember, dry-run de
setup que promete git-index: flags que **hablan** y no hacen. Encajan
en el gate abierto de Obra 05 “0 flags mentirosos”.

---

## 10. Documentación que no se puede obedecer

| Archivo | Problema | Trato |
|---|---|---|
| `HANDOFF.md` | Conflicto de merge; §2 vs §7; “219 passed” en cómo verificar | **Historia.** Leer §0–§7 como crónica Obra 07, no como mapa. |
| `ESTADO-ACTUAL.md` | Banner “baja definitiva / CLI completo”; reindex “fail”; 569 tests | **Historia Obra 08.** Las tablas de fases P0–P12 sirven. El header no. |
| `15-REBRANDING-…` | §2 da por hecho modos Herdr. §3–§4 (crítica y roadmap) **sí** son ciertos | Conservar §3–§4. §2 es el relato del agente anterior. |
| `14-HERDR-COMPANION.md` | RESUELTO. Spec v1 (4 acciones, overlay, herdr 0.8, cero deps). Código ≠ spec | Spec de **Companion 80×24**. No de sidecar/float/copilot. |
| `13-MODO-COMPOSED-…` | RESUELTO. §5 pide `SKILL.md + references/`; se implementó R10 flat | Dominio COMPOSED real. Layout de skills = ruling, no spec. |
| `10-P10-BRANDING-TUI.md` | COMPLETO con paleta cyan | Histórico P10. Paleta vigente = `palette.rs` + PNG nuevo. |
| `05-UX-TUI-ACTIONENGINE.md` | Gates UX abiertos + fases Python `[x]` | **Contrato de producto aún vigente.** Implementación Python, no. |
| `PROMPT-HANDOFF-OTRO-AGENTE.md` | “todo mergeado, no rehagas Obra 08” | Cierto para A1–A13 y B1–B10 del **plan 08**. Falso si se lee como “el repo está pulido”. |
| `ENTENDIMIENTO-CORTEX.md` | 20 crates, 10 acciones, 3 modos, 587 tests, foco P8d | Snapshot 08-27. 21 crates, 11 acciones, 4 modos. |
| `progress.md` | scratch de exploración | No es ledger. |
| README / README.es | finish, 3 modos, sin Companion | Mentira user-facing. Se corrige cuando el verbo exista, no antes con marketing. |
| `integrations/herdr/INSTALL.md` | 4 acciones, overlay, 28% | Desactualizado vs toml/código. |

Cifras de tests que aparecen como “actuales”: 219, 83, 569, 587, 594,
759. La cuenta de `#[test]` en `rust/` al día de esta auditoría es
**759 atributos, 1 ignored** (`rss_measure`). Un agente no debe pegar
un número de cierre viejo en el “cómo verificar”.

Oráculo Python **2552** es snapshot de cierre **con e2e**. CI
(`ci-gates.yml`) corre unit+integration. Un recuento del árbol habla de
2473. No recapturar ni pelear el número: saber que es snapshot.

---

## 11. Estado del árbol (29 ago 2026)

- Rama `feature/transformacion-2026-08`, HEAD `de387bf`, **sin upstream**.
- ~58 paths sucios. El rebranding + bins Herdr **no están commiteados**.
- WIP viejo untracked: `cortex-tui/src/app/`, `cortex-mcp/src/backends/`
  (este último **sí está cableado** en el crate; no es un folder
  fantasma), prompts de cierre, `uv.lock`, logs `.cortex/`.
- Commit `8149bfd` preserva WIP P8d byte-exacto. No reescribirlo.
- Python (`cortex/`, `tests/`, `pyproject.toml`) se queda hasta que el
  dueño decida borrar el oráculo. No es trabajo de esta obra.

El ciclo 15 se trata como **borrador sucio**, no como base estable. El
Companion de Obra 08 (máquina ELM + backend) **sí** es base estable.

---

## 12. Norte de producto (criterio del dueño, escrito para ejecutar)

### 12.1 Una frase

Cortex, dentro de Herdr, es el **copiloto de gobernanza del agente que
está codeando**: le inyecta la próxima instrucción cierta, le muestra
en qué fase COMPOSED está, le deja aprobar un efecto real, y se aparta
visualmente para no competir con el trabajo.

### 12.2 Superficie diaria

**Companion en Herdr.** Tres layouts del **mismo** `AppState`, no tres
programas:

| Modo | Geometría real (no metadata) | Contenido (en este orden) |
|---|---|---|
| **Sidecar** | split, Cortex **izquierda ~30%**, agente ~70% | Mark chico · fase viva · próxima instrucción (effect) · [Inyectar] [Aprobar] · alerta si hay. Navegación secundaria en teclado, no 4 botones. |
| **Float** | split inferior ~25% **o** overlay si Herdr lo hace de verdad — una sola historia, code=docs=toml | Una línea de contexto · instrucción · 2 acciones. Esc **cierra**. |
| **Copilot** | split, Cortex no mayor a ~40% | Badge de agente **vivo** · fases COMPOSED **leídas** · caja de prompt = effect/skill · Enter inyecta **solo** en esa pantalla · Aprobar abre el modal de siempre. |

Standalone `cortex-companion` y `cortex` (TUI teclado) siguen vivos.
No se les agrega un tercer Home. Features nuevas van al Companion;
TUI solo se toca si el mismo cambio es trivial de compartir.

### 12.3 Qué deja de mostrarse como protagonista

Tarjetas “sesión activa / doctor OK / episódica N / semántica M”.
Pueden vivir en una línea de status. No ocupan el 70% del pane.

Botones Menú / Sesiones / Brain: teclado (`1`, `2`, `Tab`, `/`) y un
comando paleta (tipo `Ctrl+K`) más adelante. No una grilla 2×2 de
cajas `Borders::ALL`.

### 12.4 Estética

- Paleta menta/esmeralda vigente. Tokens se pueden seguir llamando
  internamente `CYAN`/`BLUE` **hasta** un rename mecánico; el fallback
  16 colores tiene que leerse verde, no cyan de P10.
- Isotipo **Mark**, ≤5 filas de half-block. Wordmark solo en splash /
  standalone ancho. En sidecar/float, no.
- Bordes: línea o nada. Jerarquía por peso de texto, no por cajas.
- Cero emoji como arquitectura (`🩺 🧠 🚀 ⚡`). Un acento menta alcanza.

### 12.5 Engines

- **Proponer implica poder ejecutar.** Las 6 acciones STUB-VERDE se
  cablean a los servicios nativos o salen del catálogo.
- Aprobar/saltar/nunca escribe `actions.yaml`. El ranking se mueve.
- `session.suggest_next_phase` deja de ser un print: la UI **es** esa
  sugerencia (fase actual → siguiente, con el prompt de la skill craft).
- `cortex finish` se wirea al cierre verificado (documenter + hooks).
  Companion deja de apuntar a un comando muerto.
- Doctor deja de emitir “backend no nativo” para módulos que son
  nativos. Companion usa `ok` de verdad.

### 12.6 Lo que el §4 del doc 15 apunta y **no** es el primer corte

Radar de guardrails (“el agente tocó un archivo fuera de scope”),
buffer de diff coloreado de lo que el agente va a aplicar, fuzzy finder
de skills. El TUI de sesiones **ya calcula diff git**. El motor de
sesiones **ya tiene** spec/files_in_scope.

Esos tres ítems son el **corte 2** de la misma obra, no otra fantasía.
El corte 1 es: layouts que existen, acciones que ejecutan, fase que se
lee, finish que cierra, spawn que no miente.

---

## 13. Principios de pulido (contrato para quien implemente)

1. **Commits locales, Conventional en español, un gate por commit.**
   Sin push. `cargo test -p <crate>` + `clippy -D warnings` + `fmt`
   antes de commitear.
2. **No se marca hecho con test de conteo.** El test tiene que romper
   si el usuario no puede hacer la cosa (click en Aprobar del HUD,
   resize 30%, `cortex finish` rc 0 con nota de sesión).
3. **Si el servicio existe, se llama.** Un `ActionResult::fail("fase
   P8")` con Setup nativo en el workspace es un bug, no un patrón.
4. **Una máquina de estados.** Modos Herdr = layouts + keymap. No
   bins que copian `main`. `CompanionMode` vive en `AppState`.
5. **Spawn Herdr: error visible.** Swap/resize/JSON fail ⇒ error al
   usuario, no `Ok(())` + metadata falsa.
6. **No recapturar goldens ni tocar Python** salvo templates SSoT
   output-neutral (precedente R9).
7. **Cero deps nuevas sin ADR.**
8. **`#![forbid(unsafe_code)]`** en lógica nueva.
9. **No rehacer Obra 08.** Extender Companion/engine; no un cuarto TUI.
10. **Docs se actualizan cuando el comportamiento existe**, no para
    adelantar el cierre. Este archivo es la excepción: documenta la
    deuda *antes* de pagarla.
11. **README no se “arregla” poniendo `autopilot finish` en la cara
    del usuario.** Se wirea `finish` o se deja el README mintiendo
    hasta ese commit — y ese commit es temprano en el plan, no al
    final.

---

## 14. Plan de Obra 09 — Pulido

Obra nueva. No es migración. No es “rebranding 2”. Es hacer que el
binario y la TUI cumplan §12.

Orden **obligatorio**. Cada lote es uno o más commits locales con
evidencia. No se salta al lote visual si el engine sigue siendo teatro:
si no, volvemos a un HUD lindo que aprueba un fail.

### Lote 0 — Higiene de verdad (este documento)

- [x] Este archivo como autoridad.
- [x] Banner en `HANDOFF.md` / `ESTADO-ACTUAL.md` / `docs/transformacion/README.md`
      apuntando acá.
- [x] Sacar el marcador `>>>>>>> feature/obra08-streamB`.
- [ ] No commitear el WIP 15 “como está”. O se reescribe en los lotes
      2–3 o se descarta por partes.

### Lote 1 — Engines que ejecutan

Crate: `cortex-actions` (+ llamadas a `cortex-app` / `cortex-setup` /
`cortex-cli` memory). Tests: cada `run(false)` **muta o valida de
verdad** en fixture; el fail P8/P11/P12 desaparece.

1. `session.checkpoint_now` → `SessionService::checkpoint`.
2. `vault.validate_docs` → `DocValidator::validate_batch`.
3. `vault.reindex` → mismo camino que `run_reindex_real` (o CLI in-process
   equivalente). Si el modelo no es MiniLM, fail **honesto y actual**,
   no “AgentMemory P12”.
4. `setup.finish_bootstrap` → `cortex setup agent` nativo (writers que
   ya existen).
5. `ide.resync` → inject/setup IDE nativo.
6. `quality.run_gates` → `quality_gates` sobre el último checkpoint.
7. `session.close_stale`: o cierra con el mismo camino que finish/abandon
   (con aprobación), o deja de llamarse “cerrar”.
8. UI de `next` / Companion Actions: al aprobar/saltar/nunca, llamar
   `Learner::registrar_decision`. Test: el score cambia en el siguiente
   `propose`.

**Gate:** `cortex next` en un fixture con vault y sesión OPEN propone
algo cuyo approve **no** imprime “requiere fase P…”. `cargo test -p
cortex-actions`.

### Lote 2 — El verbo `finish`

- `cortex finish` (y alias `finish-session`) en `dispatch_native`.
- Camino: sesión activa → verification hooks → documenter persist →
  CLOSED o HANDOFF. Reusar lo que ya tiene autopilot/MCP, no inventar
  un tercer reconstructor.
- Companion `close_session` llama ese camino (o `session abandon` si el
  usuario elige abandonar), **nunca** un string de un comando rc 2.
- `cortex hint` deja de recomendar tokens muertos.
- Help raíz: los verbos de nivel 0 reales, o se admite en este archivo
  que el help self-golden se reabre (dueño: recaptura consciente).

**Gate:** `cortex finish --help` existe. Fixture: open session + finish
→ nota en vault + status terminal. Companion ya no menciona un finish
inexistente. README se corrige **en el mismo lote**.

### Lote 3 — CompanionMode de verdad (Herdr)

Mismo crate `cortex-companion`. El WIP 15 se **reusa como material**,
no como diseño.

1. `CompanionMode` en `AppState`. `hit_test` y `update` ramifican.
2. Un solo binario: `cortex-companion --mode sidecar|float|copilot`
   + `--spawn`. Los tres bins pueden quedar como alias de 10 líneas.
3. `herdr.rs`: no tragar errores; no devolver Ok si no hubo resize;
   una constante de ratio documentada; tests con JSON fixture (sin
   herdr instalado).
4. Toml, INSTALL y código cuentan **la misma** historia de placement.
5. Sidecar: pantalla propia angosta (no Home 80×24). Contenido §12.2.
6. Float: layout 8–14 filas, Esc sale (`Quit`), Aprobar dispara el
   modal existente.
7. Copilot: fase leída de `SessionRecord`; inject = `effect` o prompt
   de skill; Enter **no** inyecta en Brain/Search; agente re-detectado.
8. Doctor HUD/Copilot usa `DoctorSummary.ok` y verdicts. Nunca
   “OK si nonempty”.
9. Tests nuevos: hit-test HUD/Copilot, Esc cierra float, Enter en
   Copilot no dispara BrainTurn, spawn parse fail ≠ Ok.

**Gate:** tests del crate companion cubren los tres modos. Un
screenshot no es el gate; un test de hit-test + un spawn con JSON
canned sí.

### Lote 4 — Contenido operativo (la TUI que el dueño quiere)

Sobre el lote 3, no al lado.

1. Home/Sidecar/Float muestran **próxima instrucción** (effect +
   costo + reversibilidad), no el título del catálogo solo.
2. Cadena COMPOSED visible y **correcta** (última `phase` o “sin
   fase — BYO/Observed”).
3. Línea de status: proyecto · rama · sesión · doctor real. Una fila.
4. Quitar la grilla de botones de navegación del área principal.
5. Estética §12.4: menos `Borders::ALL`, Mark chico, paleta menta.
6. (Corte 2, después de 1–5) diff de sesión en Companion (el TUI ya
   lo tiene) y alerta de paths fuera de spec.

**Gate:** snapshot TestBackend de sidecar 30 cols × 24 filas: se lee
fase + effect, no cuatro cajas “sesión/salud/memoria/acción” + logo
gigante. Review visual del dueño sobre Herdr real.

### Lote 5 — Mentiras residuales de plataforma

En paralelo **después** de 1–2, no bloquean TUI:

- Doctor: stubs contractuales que ya son nativos → checks reales o se
  eliminan.
- `NativeMemory` lee `vectors.v3.bin` si existe (reindex sirve).
- `cortex_sync_vault` en MCP: o se inyecta backend o se documenta
  fail actual (no comentario “pendiente P12”).
- Flags mentirosos: `--summarize`, setup dry-run git-index, `--auto`
  sin DocumenterFinalize.
- Version 0.1.0 vs 0.7.0: decisión del dueño, un número.

### Lote 6 — Dedup TUI (último)

Decisión ya tomada en §12.2: no fusionar crates en esta obra salvo
extraer `paint_half_block` / theme a `cortex-branding` si duele.
Reuso de widgets Companion←TUI queda para cuando el Companion de
lotes 3–4 esté estable (deuda ya escrita en spec 14 §9).

---

## 15. Fuera de alcance (no tocar en Obra 09)

- Borrado físico de `cortex/` + pytest.
- Recaptura de goldens MCP `list_tools.json` / parity archive.
- Cliente HTTP nativo para `hu import` (ADR aparte).
- Migrar skills a `SKILL.md + references/` (R10: post-oráculo).
- P13 Web Hub / backend MCP remoto.
- GPU / LFM2.5 como default.
- Reescribir adapters IDE P8d untracked.
- Push a `origin`.
- “Radar de guardrails” como obra separada con nombre de producto
  antes de que el sidecar muestre una fase real.

---

## 16. Definición de hecho de Obra 09

La obra **no** está hecha cuando hay un doc que dice PASS. Está hecha
cuando esto es cierto **al mismo tiempo**:

1. `cortex finish` existe y cierra una sesión de fixture con evidencia
   en el vault (o HANDOFF honesto si los hooks fallan).
2. Aprobar la acción top de `cortex next` en ese fixture **no** imprime
   “requiere … nativo (fase P…)”.
3. Companion sidecar, en un pane angosto, muestra fase + effect, y el
   click/tecla de Aprobar abre el modal que ya existe y, al confirmar,
   corre el `run()` cableado.
4. Spawn sidecar: si Herdr no pudo resize/swap, el usuario ve error;
   el sidebar **nunca** dice “30%” sobre un pane al 80%.
5. Copilot: la barra de fases cambia cuando el checkpoint tiene
   `phase`; Enter en Brain no manda texto al agente.
6. README enseña comandos que el binario acepta. Help raíz no oculta
   `session` / `next` / `finish` / `init`.
7. `cargo test -p cortex-actions -p cortex-companion -p cortex-cli`
   verde, clippy `-D warnings`, fmt. Tests **nuevos** de HUD/Copilot/
   finish incluidos.
8. Este documento, §14, tiene los lotes 0–4 en `[x]` con evidencia
   (comando + salida o test) pegada en el commit.

Hasta entonces: **no se escribe un “17-CIERRE”**. Se trabaja acá.

---

## 17. Decisiones cerradas en esta auditoría

1. Autoridad de pulido = este archivo. HANDOFF/ESTADO = historia.
2. Superficie diaria = Companion en Herdr. TUI teclado = secundaria.
3. Tres modos Herdr se conservan como layouts, no como tres apps.
4. `cortex finish` se implementa; no se reemplaza en README por
   `autopilot finish`.
5. Stubs P6 del catálogo contra servicios existentes = bugs del lote 1.
6. El WIP 15 no se mergea tal cual. Se reescribe sobre la máquina de
   Obra 08.
7. Corte 1 de UX = operativo + geometría Herdr + finish. Corte 2 =
   diff/guardrails/fuzzy skills.
8. Python se queda como oráculo hasta decisión explícita del dueño.

---

## 18. Índice rápido para el próximo agente

```
¿Está hecho X?
  1. Buscar X en este archivo.
  2. Si no está, grep el crate. Si el doc 15 / HANDOFF dicen que sí
     y acá no, acá gana.
¿Por dónde empiezo?
  Lote 1 (engines) salvo que el dueño pida ver TUI ya — entonces
  Lote 3 en paralelo, nunca Lote 4 sin 1 y 3.
¿Puedo pushear?
  No.
¿Puedo marcar RESUELTO?
  Solo con el gate del lote, evidencia en el commit, checkbox acá.
```

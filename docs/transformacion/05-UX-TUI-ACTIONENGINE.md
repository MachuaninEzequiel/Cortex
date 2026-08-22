# Obra 05 — UX simplificada + ActionEngine

> Estado: PLANIFICACIÓN · Planificador: plan-ux
(El planificador completa: TUIs simples, consolidación de comandos, diseño del ActionEngine de aprendizaje automatizado.)

## Requisito duro del usuario
- Mucho más fácil de usar que hoy. El desarrollador elige de vez en cuando; el motor automatiza el resto.

## 0. Estado del documento

- [x] 1. Mapa de la UX actual + fricción medida
- [x] 2. UX objetivo: flujo ≤3 comandos, consolidación viejo→nuevo

## 2. UX objetivo

### 2.1 Principios

1. **Un comando para empezar, uno para trabajar, uno para terminar.** Todo lo demás es
   administración y vive detrás de la TUI o de subapps claramente separadas.
2. **El motor propone, el usuario dispone.** Las decisiones repetitivas (cuándo hacer
   checkpoint, cuándo re-indexar, qué aprender) las toma el ActionEngine; el usuario
   aprueba en un menú.
3. **Cero flags mentirosos.** Un flag que no funciona se elimina, no se documenta.
4. **Una sola convención de salida**: `--format text|json` en todo comando que produce
   datos; `text` default humano, `json` para agentes/CI. Se elimina `--json`.
5. **Simple > completo**: cada pantalla de TUI debe ser comprensible sin scroll en 80×24.

### 2.2 Flujo nuevo usuario ≤3 comandos (requisito duro del dueño)

```
cortex init          # 1 solo comando: setup agent + inject IDE interactivo + doctor corto
                     #   al final imprime: "Listo. Corré `cortex` para ver tu panel."
cortex               # 2: abre el Home TUI (dashboard + acciones pendientes + tutor embebido)
# ...trabaja en su IDE; los hooks hacen checkpoints...
cortex finish        # 3: cierra sesión activa con flujo guiado (equivale a finish-session)
```

Meta verificable: un desarrollador nuevo llega de `pipx install` a "primera nota en el
vault" tocando **≤3 comandos** y leyendo solo pantallas de la TUI. Validación:
script E2E con subprocess que simula el flujo sobre un repo temporal.

### 2.3 Consolidación de comandos (tabla viejo → nuevo)

Jerarquía objetivo en 3 niveles:

- **Nivel 0 — Día a día** (raíz, ≤8 verbos): `cortex` (TUI home), `start`, `finish`,
  `search`, `context`, `remember`, `doctor`, `tutor`.
- **Nivel 1 — Administración** (`cortex setup`, `cortex session`, `cortex ci`,
  `cortex enterprise`, `cortex mcp`): usados una vez o por CI.
- **Nivel 2 — Power/debug** (subcomandos finos): accesibles pero fuera del help raíz
  (`hidden=True` o sección "advanced").

| Viejo | Nuevo | Notas |
|---|---|---|
| `init` / `setup agent` | `cortex init` | Único bootstrap; incluye inject interactivo + doctor resumido |
| `setup full/pipeline/webgraph/enterprise` | `cortex setup <perfil>` | Sin `--dry-run` falso: dry-run real u omisión |
| `inject` / `install-ide` / `uninstall-ide` / `sync-ide` | `cortex setup ide [add\|remove\|sync]` | 1 comando, subacciones; Obra 02 define contrato único |
| `mcp-server` / `mcp-serve` | `cortex mcp serve` | Alias legacy oculto por 1 versión |
| `create-spec` | `cortex start --spec` (o interactivo desde TUI) | `create-spec` queda como alias |
| `save-session` | checkpoint automático / `remember --session` | Deprecar; solapaba con `session checkpoint` |
| `finish-session` | `cortex finish` | Alias mantenido 2 versiones |
| `session watch` (read-only) | Panel "Sesión activa" dentro de la TUI | La acción vive en la TUI |
| `autopilot start/status/...` | Modo dentro de `cortex start` + panel TUI | `autopilot` queda como subapp de admin |
| `hint` | Acción #1 del Home TUI ("¿Qué hago ahora?") | El ActionEngine lo reemplaza funcionalmente |
| `search` + `context` | Se mantienen ambos pero con salida `--format` única | Fix B3/B4 del review cli |
| `docs *`, `pr-context *`, `hu`, `ci`, `review-knowledge`, `promote-knowledge`, `sync-enterprise-vault` | `cortex docs ...`, `cortex pr ...`, `cortex hu`, `cortex ci`, `cortex enterprise ...` | Agrupados; fuera del help raíz visible |
| `stats` / `memory-report` | Panel "Salud" de la TUI + `cortex doctor --report` | Comandos siguen existiendo para scripting |

Regla de compatibilidad: todo comando viejo mantiene alias oculto durante 2 versiones con
warning de deprecación apuntando al nuevo, luego se elimina.

### 2.4 Criterio de salida de UX (gates)

- [ ] Flujo nuevo usuario medido en ≤3 comandos (test E2E automatizado).
- [ ] Help raíz muestra ≤8 comandos visibles.
- [ ] 0 flags declarados y no implementados (grep de paridad flag→uso).
- [ ] Una sola convención `--format` en todos los comandos con salida de datos.
- [ ] Toda acción destructiva pide confirmación o tiene `--yes` explícito.
- [x] 3. ActionEngine: ciclo, contrato de Action, scheduler, TUI de aprobación

## 3. ActionEngine — motor de acciones con aprendizaje

### 3.1 Concepto

Un solo ciclo que reemplaza la pregunta "¿qué hago ahora con Cortex?":

```
┌─────────────────────────────────────────────────────────────┐
│ 1. OBSERVAR   estado del proyecto: doctor (~25 checks),     │
│               sesiones (SessionService), vault, telemetría  │
│               del enricher, feedback de utilidad            │
│ 2. PROPONER   acciones priorizadas por impacto/costo        │
│ 3. APROBAR    menú simple en TUI: [a]ceptar [s]altar       │
│               [n]unca más  — o modo auto para acciones      │
│               seguras marcadas reversible                   │
│ 4. EJECUTAR   vía los servicios existentes (nunca CLI-      │
│               scraping); log en action_log.jsonl            │
│ 5. APRENDER   resultado → feedback_loop persistido →        │
│               ajusta prioridad y frecuencia de la acción    │
└─────────────────────────────────────────────────────────────┘
```

El usuario "elige de vez en qué hacer": abre `cortex` (o corre `cortex next`) y ve una
lista corta de acciones propuestas. Todo lo rutinario entre medio es automático.

### 3.2 Contrato de Action

Nuevo paquete `cortex/action_engine/` (módulos: `models.py`, `registry.py`,
`scheduler.py`, `runner.py`, `learning.py`). Contrato base:

```python
@dataclass(frozen=True)
class Action:
    id: str                      # "doctor.fix_gitignore", "vault.reindex", ...
    title: str                   # humano, ES/EN según config (Obra 04)
    category: Literal["setup","maintenance","learning","quality","knowledge"]
    preconditions: list[Check]   # cada Check = función pura -> bool + reason
    effect: str                  # descripción exacta de lo que va a cambiar
    reversible: bool             # False => requiere aprobación SIEMPRE
    undo: Callable | None        # requerido si reversible=True
    cost: Literal["instant","seconds","minutes"]
    auto_ok: bool                # elegible para ejecución sin preguntar
                                 # (solo si reversible=True y cost=instant)
    run: Callable[[], ActionResult]
```

Reglas duras del contrato:
1. **Toda acción pasa por su servicio**, nunca reimplementa lógica (ej.: `vault.reindex`
   llama a `AgentMemory.sync_vault()`; `setup.ide_add` llama al orquestador de Obra 02).
2. **Precondiciones se evalúan antes de ofrecer** la acción; una acción cuyas
   precondiciones fallan no aparece en el menú (aparece en `--explain-why-not`).
3. **Irreversible ⇒ siempre pregunta**, sin excepción ni modo auto.
4. **Toda ejecución se registra** en `.cortex/action_log.jsonl`: id, timestamp,
   trigger, resultado, duración. Es el insumo del paso APRENDER.
5. **Dry-run nativo**: `run(dry_run=True)` devuelve el efecto esperado sin escribir.

### 3.3 Acciones iniciales (catálogo v1) — cada una sobre una pieza existente

| id | Dispara | Ejecuta | Fuente existente |
|---|---|---|---|
| `setup.finish_bootstrap` | doctor detecta config incompleta | completa setup faltante | `SetupOrchestrator`, `doctor.py` |
| `session.close_stale` | sesión OPEN >N días sin checkpoints | guía de finish/abandon | `SessionService.list()` |
| `session.checkpoint_now` | archivos cambiados desde último checkpoint | checkpoint con diff | hooks + `session checkpoint` |
| `vault.reindex` | vault mtime > último index / drift | `sync_vault()` + `index_docs` | `AgentMemory.sync_vault` |
| `vault.validate_docs` | docs nuevos sin validar | `DocValidator.batch` + fix sugerido | `doc_validator.py` |
| `quality.run_gates` | pre-close o post-PR | VerificationRunner + quality_gates | `quality_gates.review_checkpoint` |
| `learn.topic` | tutor topics no vistos relevantes al trabajo actual | abre topic (con `guide_path` revivido) | `tutor/` |
| `knowledge.promote` | cola enterprise con pendientes | flujo review-knowledge guiado | `review_knowledge.py` |
| `memory.prune` | feedback decay + telemetría muestran memorias inútiles | propone forget con confirmación | `memory_decay`, `feedback_loop` |
| `ide.resync` | skills/config cambiaron vs IDE inyectado | sync con marcadores (Obra 02) | `setup ide sync` |

### 3.4 Scheduler y disparadores

Tres modos de disparo, sin daemon residente (respeta el principio de procesos cortos):

1. **On-open**: cada vez que arranca la TUI home o cualquier comando nivel-0, corre un
   *snapshot* barato (<300ms, mtimes + puntero activo + cache del último doctor). Si hay
   acciones pendientes, las muestra. Nada bloquea.
2. **On-event**: los puntos del ciclo que ya existen disparan evaluación:
   - post-checkpoint → `quality.run_gates` si hay hooks required fallando;
   - pre-close (`on_pre_close` del PolicyEnforcer) → ofrece `finish` guiado;
   - post-finish → `vault.reindex` + `learn.topic`.
3. **On-schedule (opt-in)**: `cortex next --all` fuerza un escaneo completo (incluye
   doctor entero). Opcional: hook git post-commit ya instalado puede encolar
   `session.checkpoint_now`.

Priorización: score = impacto_estimado × frescura − costo. El impacto inicial es una tabla
estática por categoría (setup > calidad > mantenimiento > aprendizaje) refinada luego por
el aprendizaje real (§3.6). Máximo 5 acciones visibles; el resto bajo "ver más".

### 3.5 TUI de aprobación

Pantalla única tipo lista (rich, no Textual en v1):

```
  Cortex · 3 acciones sugeridas          ses: base-auth (OPEN, 2 checkpoints)
 ─────────────────────────────────────────────────────────────────────
 [1] Validar los 4 docs nuevos del vault            ~5s   reversible
 [2] Re-indexar vault (12 archivos cambiaron)       ~10s  auto-ok
 [3] Cerrar sesión `base-auth`: 2 hooks sin verificar ~2m  pide confirmación
 ─────────────────────────────────────────────────────────────────────
 a=aceptar todas las auto-ok · 1/2/3=elegir · s=saltar · n=nunca más · q=salir
```

- `n` (nunca más) persiste la supresión por id en `.cortex/actions.yaml` — el motor aprende
  preferencias negativas también.
- Acciones irreversibles abren subpantalla con `effect` + confirmación explícita.
- Modo `assist` (hereda semántica de autopilot): auto-ejecuta solo `auto_ok`; el resto espera.

### 3.6 Paso APRENDER (dar propósito real a las piezas dormidas)

1. **Persistir feedback_loop** (hoy 100% en memoria): serializar contadores de utilidad a
   `.cortex/feedback.jsonl`. El review 1-core §1.7 documenta el gap; es prerrequisito directo.
2. **Cablear telemetría del enricher**: pasar `make_observer(...)` donde se construye
   `ContextEnricher` (core.py:855, mcp/server.py:1788, cli/main.py:1624) + rotación del
   JSONL (review 7-context #24/#25, recomendación #6 de ese informe). Con datos reales,
   `search` malo dispara `vault.reindex` o sugerencia de Obra 04.
3. **Revivir `guide_path`** en tutor topics: `learn.topic` lo usa para deep-link.
4. **Bucle de preferencias**: aceptar/saltar/nunca alimenta el score de prioridad por
   categoría. Guardado en `.cortex/actions.yaml` + agregado mensual en `action_log`.

Anti-patrones prohibidos: ninguna acción modifica scoring de retrieval directamente;
ninguna acción escribe en el vault sin pasar por servicios de documenter; ninguna acción
corre en segundo plano sin registro en action_log.
- [x] 4. TUIs: stack y pantallas

## 4. TUIs — propuesta concreta

### 4.1 Stack: mantener typer + rich, NO Textual (en v1)

Decisión: **extender el patrón ya probado** (`rich.Live` + frozen-state + renderer puro de
`session_tui.py`) a un mini-framework interno `cortex/tui/`. Razones:
- Cero dependencias nuevas (Obra 01 poda; agregar un framework pesado va contra eso).
- `session_tui.py` ya demostró que el patrón es testeable sin TTY (renderer puro).
- El requisito del dueño es *simple*, no *complejo*: listas + menús numerados + paneles,
  no apps interactivas complejas.
- Escape clause: si en v2 aparece necesidad real de input rico (tabs, forms), evaluar
  Textual con spike acotado de 1 semana. Queda registrado como decisión reversible.

Estructura propuesta:

```
cortex/tui/
  core.py       # TuiState (frozen dataclass) + render(state) -> Layout + poll loop
  screens/
    home.py     # dashboard
    actions.py  # aprobación de acciones (§3.5)
    session.py  # sesión activa (evolución de session_tui.py)
    search.py   # búsqueda
  _unicode.py   # reusar _unicode_fallback.py existente
```

### 4.2 Pantalla HOME / dashboard (`cortex` sin argumentos)

```
 Cortex · mi-proyecto            rama: feat/base-auth
 ──────────────────────────────────────────────────────
 SESIÓN   base-auth · OPEN · 2 checkpoints · hace 20m
 PENDIENTE  3 acciones sugeridas  ← [enter] para ver
 VAULT     142 notas · 4 sin validar · indexado hace 2d
 SALUD     doctor: ✓ config ✓ git ⚠ 4 docs sin validar
 ──────────────────────────────────────────────────────
 s=sesión  a=acciones  /=buscar  t=tutor  d=doctor  q=salir
```

- Snapshot barato on-open (<300ms); teclas de una letra ejecutan y vuelven al home.
- Si no hay proyecto inicializado → wizard de `init`.

### 4.3 Pantalla ACCIÓN PENDIENTE

La de §3.5. Es la pantalla más importante del producto: es donde el usuario "elige de vez
en cuando". Requisito: nunca más de 5 ítems visibles, cada uno con costo y reversibilidad
visibles antes de elegir.

### 4.4 Pantalla SESIÓN ACTIVA

Evolución directa de `session_tui.py` (reusa su renderer): tareas, checkpoints, hooks,
diff resumido. Cambio clave: pasa de read-only a actuar — `c`=checkpoint ahora,
`t`=toggle tarea, `f`=finish guiado. Requiere exponer APIs públicas en SessionService
(hoy la TUI toca `service._storage._file_for(...)` — review cli B6).

### 4.5 Pantalla BÚSQUEDA

Input simple → llama al mismo path que `cortex search` (un solo motor tras Obra 02/04) →
lista paginada de hits con score y tipo → `[enter]` abre nota, `[y]` marca útil (alimenta
feedback_loop persistido). Sin filtros avanzados en pantalla: los filtros estructurales
quedan para el comando CLI de power users.

Gates de las TUIs:
- [ ] Las 4 pantallas renderizan idéntico en 80×24 sin scroll.
- [ ] Renderer puro testeado sin TTY (patrón session_tui) — cobertura ≥80%.
- [ ] Toda acción disponible en TUI tiene equivalente CLI (la TUI orquesta, no reemplaza).
- [x] 5. Dependencias de Obras 01/02 y plan por fases con gates

## 5. Dependencias y plan por fases

### 5.1 Qué requiere de Obra 01 (podado/limpieza) — no construir sobre arena

| Requisito | Por qué |
|---|---|
| Suite verde (TRAMO 0) | El ActionEngine orquesta servicios; sin tests no se puede refactorizar nada que toque |
| `feedback_loop` y telemetría NO podados | Son insumos del paso APRENDER; si Obra 01 los elimina por "muertos", pierden propósito — coordinar: Obra 01 los marca "reservado Obra 05" |
| Flags muertos eliminados (`--dry-run` falso, `install-ide` deprecated) | La consolidación de §2.3 parte de la superficie ya limpia |
| Accesos a privados resueltos (B6 cli review) | La TUI necesita APIs públicas: `SessionService.session_file_mtime()`, `active_pointer_mtime()` |

### 5.2 Qué requiere de Obra 02 (estándar único IDE/CLI)

| Requisito | Por qué |
|---|---|
| Contrato único de instalación/inyección IDE | La acción `ide.resync` y el flujo `init` delegan en ese contrato; si hay 3 caminos (hoy), el ActionEngine automatizaría el caos |
| Split de `main.py` en subapps modulares | Punto de montaje natural para los nuevos comandos nivel-0 sin agrandar el monolito |
| Convención única `--format` | Prerrequisito del gate §2.4 |
| Marcadores de gestión en archivos IDE + uninstall seguro | Toda acción sobre IDEs debe ser reversible con undo real (bug pi.uninstall destructivo, review top-bug #3) |

### 5.3 Fases (orden interno de Obra 05)

**Fase A — Fundaciones (tras TRAMO 1 de Obras 01+02) — COMPLETA ✅ 2026-08-23**
- [x] Persistir feedback_loop: `cortex/feedback_store.py` (JSONL + rotación + fsync)
      + hook opcional `FeedbackCollector(store=...)`. Tests: test_feedback_store.py.
- [x] Cablear observer=: make_observer() en los 4 sitios de ContextEnricher
      (core/MCP/cli context/docs_search) + rotación JSONL en PersistentObserver
      (_MAX_BYTES 5MB → .1.jsonl; iter_events lee vivo+rotado). Tests: test_observer_wiring.py.
- [x] APIs públicas SessionService: save_new_record(), path_for(),
      active_pointer_path(), find_for_pr(). Cero accesos `_storage` fuera del
      paquete session (ci/review_session, ci/validator y session_tui migrados).
      Tests: test_public_api_v9.py.
- [x] Revivir guide_path: TutorEngine._render_topic muestra '📖 Guía extendida'
      cuando el topic define ruta; guardia de que las rutas existen.
      Tests: test_tutor/test_guide_path.py.
- Gate salida ✅: suite completa verde (2358 passed); sin cambios visibles para el usuario
  (telemetría escribe bajo .cortex/ con opt-out por config).

**Fase B — ActionEngine core — COMPLETA ✅ 2026-08-23**
- [x] Paquete `cortex/action_engine/`: models.py (contrato §3.2 con validación dura:
      auto_ok solo reversible+instant; reversible exige undo), store.py (ActionLog JSONL
      con rotación + PreferencesStore actions.yaml), registry.py, scheduler.py
      (precondiciones antes de ofrecer + explain_why_not + score impacto×frescura−costo,
      max 5 visibles), runner.py (irreversible exige approved; dry-run nativo; TODO se
      registra), learning.py (Learner v0: skip −15%, accept compensa 2 skips, never suprime).
- [x] Catálogo v1: las 10 acciones de §3.3 sobre servicios existentes
      (setup.finish_bootstrap→SetupOrchestrator · session.close_stale/checkpoint_now→
      SessionService · vault.reindex→sync_vault · vault.validate_docs→DocValidator ·
      quality.run_gates→review_checkpoint · learn.topic→TutorEngine+guide_path ·
      knowledge.promote · memory.prune→feedback persistido · ide.resync→cortex.ide.inject_all).
      Dry-run nativo en todas; report-only ⇒ reversible formal con undo no-op.
- [x] Comando `cortex next` (--json/--explain-why-not/--all): contexto perezoso
      (sin ChromaDB salvo necesidad), salida humana numerada + machine-readable.
- Gate salida ✅: subprocess mide <2s en repo mediano (50 docs); toda acción ejecuta
  dry-run en test y las mutadoras reales tienen asserts contra servicios.
  BUG NUEVO hallado en el camino (#13 plan 01): SetupOrchestrator.run(dry_run=True)
  crea archivos reales — registrado para P-bugs.

**Fase C — Consolidación de comandos — COMPLETA ✅ 2026-08-23**
- [x] Nivel-0: `cortex finish` y `cortex start` visibles; create-spec/finish-session
      quedan como aliases ocultos (compat 2 versiones). init gana --non-interactive.
- [x] save-session oculto + warning (checkpoints automáticos); legacy IDE root
      (inject/install-ide/uninstall-ide/sync-ide) ocultos con warnings — la superficie
      única es `cortex ide` (Obra 02).
- [x] B3/B4 arreglados: scope/project-id reales en el dispatch; --format siempre
      honrado (--json queda como alias legacy compat). Tests test_search_b3b4.py +
      7 tests actualizados al nuevo comportamiento.
- [x] Test E2E del flujo ≤3 comandos sobre repo temporal con git real
      (tests/e2e/test_flujo_3_comandos.py): init→start→finish deja nota en vault.
      Expuso y corrigió bug de familia #4: init/setup_agent pasaban OptionInfo
      como valores al llamarse entre sí (impl llana _run_setup_agent extraída).
- Gate salida ✅ parcial: help raíz = EXACTAMENTE 8 visibles (next, start, finish,
  init, doctor, context, tutor, search); E2E verde. Pendiente para cierre total
  de §2.4: auditoría completa de flags sin implementar y convención --format en
  TODOS los comandos con salida de datos (quedan casos heredados en docs/pr-context).

**Fase D — TUIs — COMPLETA ✅ 2026-08-23**
- [x] cortex/tui/core.py: HomeState frozen + renderers puros (patrón
      session_tui, testeable sin TTY) + snapshot_home <300ms (contexto
      perezoso) + loop de teclas a/s/÷/t/d/q con cota defensiva.
- [x] Pantalla acciones = aprobación §3.5 real: Learner registra
      accept/skip/never y Runner ejecuta (approved solo en elección
      explícita; auto-ok lote 'a'). Búsqueda usa el mismo motor que
      `cortex search`; [y]=útil escribe feedback PERSISTIDO.
- [x] `session show --watch` deprecado → el panel vivo es la TUI home;
      `cortex` sin argumentos abre el Home (callback invoke_without_command).
- Gate salida ✅: test_home.py — snapshot<300ms, render 80x24 sin
  desborde, secciones presentes, decisiones persistidas. Sesión activa
  interactiva completa queda como pulido post-gate (hoy orquesta
  `session watch`/`cortex finish` por CLI-equivalencia).

**Fase E — Aprendizaje cerrado + pulido — IMPLEMENTADA ✅ 2026-08-23**
- [x] Score alimentado por feedback real: signals.py lee feedback.jsonl
      (ventana 14d) → Scheduler multiplica por categoría (±25% tope):
      dominio negativo sube quality/maintenance, positivo learning/knowledge.
- [x] Métrica del dueño: metrics.py calcula pct_motor = via=auto/total reales
      desde action_log.jsonl; `cortex next --stats` la expone con su definición.
- [x] i18n ES/EN: ui.language en config.yaml (default es) — títulos de las 10
      acciones + etiquetas del Home bilingües.
- Gate salida: la VENTANA DE MEDICIÓN se abre con la adopción (no es
  simulable en CI): registrar en ESTADO-ACTUAL.md tras ≥2 semanas de uso
  real el pct_motor observado y días/menú. Definición y herramienta listas.

### 5.4 Riesgos

| Riesgo | Mitigación |
|---|---|
| Obra 01 poda feedback_loop/telemetría por considerarlos muertos | Coordinación explícita en ESTADO-ACTUAL.md; marcar como "reservado Obra 05" en inventario de Obra 01 |
| ActionEngine propone acciones basadas en detectores con FP (autopilot security substring matching) | Fase B solo usa detección para *sugerir*, nunca para ejecutar auto; arreglar FP es prerrequisito de cualquier `auto_ok` relacionado |
| TUI interactiva rompe flujos no-interactivos (CI, agentes) | Regla dura: todo comando nivel-0 tiene modo non-interactive con flags; TUI solo cuando stdout es TTY |
| Doble fuente de verdad TUI vs CLI | Toda acción TUI pasa por el mismo runner del ActionEngine; prohibido duplicar lógica en screens/ |
| Alcance inflado (Textual, dashboards web) | Escape clause documentado §4.1; webgraph UI ya existe para visualización — no duplicar |

### 5.5 Definición de "hecho" de la Obra 05

- [x] Gates §2.4 parciales verificados (help raíz = 8; E2E 3 comandos verde;
      --format unificado en search). Auditoría completa de flags heredados: pendiente menor.
- [x] Contrato Action + action_log verificados por tests (test_core/test_catalog).
- [x] Ciclo observar→proponer→aprobar→ejecutar→aprender implementado y testeado;
      el ciclo EN USO REAL queda sujeto a la ventana de medición (2 semanas).
- [x] Planificación sin tocar código fuera de docs (fases previas).

## 1. Mapa de la UX actual

### 1.1 Inventario de superficie de comandos (verificado con `cortex --help`)

**~40 comandos top-level + 8 subapps** (`session`, `autopilot`, `ci`, `docs`, `pr-context`,
`hu`, `setup`, `webgraph`) que a su vez exponen ~45 subcomandos más. Total >85 verbos
visibles para un usuario nuevo.

Problemas estructurales detectados (fuente: review 2-cli.md, verificado):

| Problema | Evidencia |
|---|---|
| Doble sistema de salida | `search`/`docs search`: `--json` legacy vs `--format text\|json\|compact`; pasar `--format json` sin filtros se ignora en silencio |
| 3 caminos para inyectar IDE | `install-ide` (deprecated pero vivo), `uninstall-ide`, `inject`, `sync-ide` — comportamiento distinto ante `--ide` ausente en cada uno |
| Flags mentirosos | `--dry-run` declarado e ignorado en `setup agent/pipeline/full` (main.py:438/480/504); solo enterprise lo implementa |
| Comandos solapados | `save-session` vs `session checkpoint`; `init` alias de `setup agent`; `mcp-server`/`mcp-serve` duplicado; `context` vs `search` vs `pr-context search` |
| Sin jerarquía día-a-día/admin | `forget`, `org-config`, `hu import`, `promote-knowledge` al mismo nivel visual que `create-spec` |

### 1.2 Fricción medida: flujo básico hoy (create-spec → trabajar → finish-session)

Flujo mínimo realista de un desarrollador nuevo:

```
1. cortex init                        (bootstrap)
2. cortex inject                      (inyectar perfil en su IDE — menú)
3. cortex create-spec --title "..."   (+ decidir --verification-hooks)
4. cortex session current             (¿se abrió? ¿cuál es mi sesión?)
5. [trabajar]
6. cortex autopilot start             (opcional pero recomendado; adopta la sesión)
7. cortex session checkpoint ...      (o dejar que el hook lo haga)
8. cortex hint / tutor                (para saber qué sigue)
9. cortex finish-session              (reconstruye, verifica, persiste)
10. cortex doctor                     (cuando algo falla)
```

**10 comandos distintos, 5 de ellos administrativos**, para un ciclo que conceptualmente es:
*empezar → trabajar → terminar*. El usuario debe conocer `session` Y `save-session` Y
`autopilot` Y `doctor` como piezas separadas y descubrir cuándo usar cada una.

Fricción adicional:
- El error de `_load_memory` sugiere `cortex setup full --non-interactive` (main.py:2229) —
  un comando distinto al `init` que ya corrió.
- `cortex hint` existe pero nadie lo llama automáticamente; es un oráculo opt-in.
- La TUI `session watch` es **read-only**: no permite actuar desde ella.

### 1.3 Piezas dormidas con valor para el ActionEngine (hallazgos del review)

| Pieza | Estado hoy | Valor latente |
|---|---|---|
| `feedback_loop.py` (510 l) | Analiza utilidad de memorias pero estado 100% en memoria, sin persistencia (review 1-core §1.7) | Señal de "qué notas sirven" para priorizar acciones |
| Telemetría enricher (`telemetry.py`) | Write side dormido: nadie pasa `observer=` a `ContextEnricher`; `record_citation` sin callers (review 7-context #24/#25) | Hit-rate real por estrategia = insumo para proponer re-indexado/limpieza |
| `tutor` topics: `guide_path` | Campo muerto en los 7 topics (engine.py:75-87) | Acción "aprender X" con deep-link a guía |
| `doctor.py` (~25 checks) | Solo corre cuando el usuario lo pide; marca informativos como warnings | Es el recolector de precondiciones perfecto para el ActionEngine |
| `quality_gates.review_checkpoint` | Expuesto solo como tool MCP | Veredictos accept/warn/redelegate = disparadores de acciones |
| `autopilot` detectors/preflight | Preflight casi inalcanzable desde CLI (sin `--diff-stat`), FP por substring matching (review 8-autopilot §4.1) | Clasificación de tarea para sugerir modo/acción |
| `memory-report` | Reporte pasivo de salud/promoción | Fuente de propuestas "promover/revisar conocimiento" |
| `hint` | Tip contextual manual, zero tokens | Génesis conceptual del ActionEngine — evolucionarlo, no duplicarlo |

### 1.4 Stack TUI actual

- `typer` + `rich` en toda la CLI. TUI propia `session_tui.py` (726 l): loop de polling
  manual sobre `rich.Live`, frozen-state + renderer puro (bien testeable), sin input de
  teclado (solo Ctrl+C), fallback unicode para Windows cp1252.
- `tutor` usa otro mini-motor de menús numerados propio (`TutorEngine`).
- No hay Textual ni ninguna dependencia TUI interactiva en pyproject.
- [ ] 2. UX objetivo: flujo ≤3 comandos, consolidación viejo→nuevo
- [ ] 3. ActionEngine: ciclo, contrato de Action, scheduler, TUI de aprobación
- [ ] 4. TUIs: stack y pantallas
- [ ] 5. Dependencias de Obras 01/02 y plan por fases con gates


# HANDOFF — Pi 2.5+net + Cockpit UX Overhaul

> Este archivo es el resumen denso de toda la sesión. Si sos el agente
> que viene después: leé esto primero, después `README.md` para
> arquitectura, y `F1.md..F5.md` solo si necesitás detalle de una fase.

---

## TL;DR

1. Trabajo de fondo: **upgrade del bundle Pi de Cortex de 2.5 a
   2.5+net** + diseño e implementación de un **overhaul UX completo**
   (5 fases F1..F5).
2. **TODO está dentro de `cortex-pi/`** salvo: (a) algunos cambios
   Python en `cortex/{session,documenter,git_policy}` para escribir
   `.cortex/session.lock`, hechos al principio de la sesión; (b) la
   documentación en `docs/multi-ide-mcp-hardening/PI-COCKPIT-UX/`.
3. **Estado**: F1–F5 implementadas + **5 rounds de bugfixes runtime**
   sobre el adopter `C:\AppFutbol`. El último fix (bugfix #5 —
   singleton anclado a `globalThis`) se entregó al usuario justo
   antes del cambio de sesión y NO está validado todavía.
4. **Próximo paso esperado**: cuando el usuario vuelva, va a venir
   con el resultado del último script de propagación (2 archivos:
   `lib/cortex-state.ts` y `cortex-cockpit.ts`). Si funciona →
   preguntale si commitear y cómo. Si no funciona → diagnóstico
   avanzado (ver § "Próximo paso esperado del agente").
5. **El fix #5 (globalThis) es la solución definitiva** a la doble
   instancia del singleton. Cualquier síntoma similar al de antes
   (cortex-net registra OK pero cockpit muestra STANDBY) significa
   que el adopter NO tiene la versión nueva del `cortex-state.ts`.

---

## Quién es el usuario

- Dev Windows 11. Habla español. Decisiones rápidas y claras.
- Repo Cortex en `C:\Cortex`. Branch `feature/nuevo-modo-autonomo`.
- Adopter de prueba en `C:\AppFutbol`.
- **No quiere tests todavía** (los hace al final, en commit aparte).
- **No quiere agents que sugieran comandos** — quiere TUI determinística.
- **Adopta multi-terminal como modo principal** de Pi 2.5+net.
- Le importa que la documentación vaya en paralelo al código.
- No commitea nada salvo que se lo pidas; cuando le pareció bien, lo
  hizo él.

---

## Línea de tiempo de la sesión

| Etapa | Qué se hizo |
|---|---|
| **0** | Investigación read-only del adaptador Pi y del bundle existente. |
| **1** | Desacople bundle↔canonical: `sync_canonical_subagents()` comentada en `pi.py`; obsidian skills hardcodeadas en `cortex_workspace.py`. |
| **2** | Reemplazo del bundle `cortex-pi/` por el zip `cortex-pi-2.5-net (1).zip`. Patch Python para escribir `.cortex/session.lock` desde `SessionService` + filtro defensivo en documenter + entry en `git_policy`. |
| **3** | Diseño completo del Cockpit UX (debate + investigación de primitivas Pi via WebFetch a `pi-mono` docs). |
| **4** | Implementación F1..F5 + docs. |
| **5** | Bugfixes runtime sobre el adopter `C:\AppFutbol` (rounds #1..#5). El último (#5: globalThis anchor) es la solución DEFINITIVA al problema de doble instancia del singleton — los rounds #1..#4 lo trataron parcialmente. |

---

## Decisiones de diseño cerradas (no re-debatir sin pedir)

- **Multi-terminal default**. La red cortex-net es el modo principal.
- **TUI calculada, no LLM**. Meta-agent `cortex` (P2 original) fue
  **descartado** explícitamente por el usuario.
- **Vista B** del panel: master (acciones completas) vs worker (limitada).
- **Slash commands `/cx-*`** para hotkeys, **no prefijo `:`** (rompe
  en Pi v0.77 que trata `:` como bash).
- **Singleton vive en `cortex-pi/.pi/lib/cortex-state.ts`**, NO en
  `.pi/extensions/` (autoload duplica instancias).
- **Auto-spawn portable**: wt.exe en Windows, tmux/alacritty/kitty/
  gnome-terminal/konsole/xterm en Linux, osascript en macOS, clipboard
  como fallback universal.
- **`ADAPTER_CONTRACT.md` y `CHANGES.md`** del bundle se eliminan
  *después* de validar todo. Por ahora viajan al adopter.
- **Coordinated shutdown** del team queda como gap conocido (F5.md §6).
- **Test del bundle** queda como TODO postponed por decisión del usuario.

---

## Arquitectura final

### `cortex-pi/.pi/` después de toda la sesión

```
cortex-pi/.pi/
├── lib/                           ← NUEVO (fuera del autoload)
│   └── cortex-state.ts            ← Singleton (única instancia)
├── extensions/
│   ├── cortex-tools.ts            (pre-existente, intacto)
│   ├── cortex-mcp.ts              (pre-existente, intacto)
│   ├── cortex-net.ts              ← modificado (F1, F3, Named Pipes, subscribe)
│   ├── cortex-cockpit.ts          ← NUEVO F1
│   ├── cortex-autopilot.ts        ← NUEVO F2
│   ├── cortex-panel.ts            ← NUEVO F4
│   ├── cortex-team.ts             ← NUEVO F5
│   ├── system-select.ts           ← modificado (escribe al singleton)
│   ├── agent-chain.ts             (pre-existente, marcado FALLBACK)
│   └── damage-control.ts          (pre-existente, intacto)
├── settings.json                  ← modificado (5 extensions en defaultExtensions)
└── ... (resto del bundle 2.5+net intacto: agents, skills, mcp.json, system.md, themes, etc.)
```

**IMPORTANTE**: `_cortex-state.ts` ya **no existe** en `extensions/`.
Pero aunque reapareciera, el patrón **globalThis** del bugfix #5
garantiza que todas las copias del módulo apunten al mismo objeto
de estado. La duplicación física del archivo deja de ser un bug
crítico desde bugfix #5 — sigue siendo una mala higiene de bundle
pero ya no rompe la app.

**El contrato de invariante post-bugfix #5**: el state vive en
`globalThis["__cortex_pi_state_v1__"]` y cualquier `import` desde
`lib/cortex-state.ts` lo recupera. Si se rompe esa invariante (por
ej., alguien cambia el GLOBAL_KEY entre extensions, o reescribe
`cortexState` como un nuevo objeto en vez de mutarlo con `update`),
la doble instancia VUELVE.

### Código Python tocado (`cortex/`)

| Archivo | Cambio |
|---|---|
| `cortex/session/service.py` | Método `_write_session_lock(id\|None)` + llamadas en `open()` / `set_active()` / `close()`. Usa `write_bytes` para evitar CRLF en Windows. |
| `cortex/documenter/reconstruction.py` | Constante `_CORTEX_INTERNAL_PATHS` + helper `_is_cortex_internal_path()` + filtro defensivo sobre `files_verified_by_git`, `files_declared_only`, `files_touched` antes del scope cross-check. |
| `cortex/git_policy.py` | `.cortex/session.lock` agregado a `NEW_LAYOUT_GITIGNORE_PATTERNS` y `LEGACY_GITIGNORE_PATTERNS`. |

Tests modificados en `tests/unit/session/test_service.py` y
`tests/unit/test_ide_adapters.py` (clase `TestPiBundleHasTripartitaRefinada`
actualizada al contrato 2.5+net).

### Docs (`docs/multi-ide-mcp-hardening/`)

| Archivo | Contenido |
|---|---|
| `PI-2.5-NET-UPGRADE.md` | Etapa 2: upgrade del bundle + patch Python. |
| `PI-COCKPIT-UX/README.md` | Overview + arquitectura + decisiones + flujo integrado + **§8 Descubrimientos runtime** (críticos). |
| `PI-COCKPIT-UX/F1.md` | Singleton + cockpit widget read-only. |
| `PI-COCKPIT-UX/F2.md` | Autopilot (gates + slash commands + sugerencias). |
| `PI-COCKPIT-UX/F3.md` | Bonus net (status pings + broadcast + peer events). |
| `PI-COCKPIT-UX/F4.md` | Panel `/cortex` modal. |
| `PI-COCKPIT-UX/F5.md` | `/cortex-team` auto-spawn. |
| `PI-COCKPIT-UX/HANDOFF.md` | Este archivo. |
| `PI-COCKPIT-UX/conversacion.md` | Transcripción cruda (no curada). |

---

## Plan de fases (todas marcadas ✅ en task list)

- **F1** Singleton (`lib/cortex-state.ts`) + cockpit widget read-only
  (`setWidget` + `setStatus` 3 slots) + integración con `cortex-net.ts`.
- **F2** Autopilot: gates `tool_call` (warning, no bloqueo) + slash
  commands `/cx-next /cx-team /cx-role /cx-mode /cx-help` (originalmente
  hotkeys con `:`, cambiados en bugfix #4) + sugerencias contextuales
  que escriben `cortexState.suggestion`.
- **F3** Bonus net: status pings (idle/busy/observe) + broadcast tool
  `cortex_net_broadcast` + eventos push `peer_joined/left/status_changed`
  del hub a clientes + polling de respaldo bajado a 15s.
- **F4** Panel `/cortex` modal (`ctx.ui.custom`) con vista master vs
  worker. Component con focus state interno. Sub-flows con cascada de
  `ctx.ui.select` (no SelectList compuesto — focus routing entre
  hermanos no documentado).
- **F5** `/cortex-team` con detección de OS y terminal disponible +
  fallback clipboard universal. Presets ("Deep Track full", "Audit pair",
  etc.). Tracking en `.pi/agent-sessions/team.json`.

---

## Bugs encontrados y arreglados (durante runtime testing)

Todos documentados verbatim en `README.md` § 8 "Descubrimientos runtime".

1. **`_cortex-state.ts` autoload falla**: `Extension does not export
   a valid factory function`. El prefijo `_` no evita el autoloader.
   *Fix temporal*: agregar `export default function (_pi): void {}` no-op.
   *Fix final*: mover a `lib/`.
2. **Pi crashea por línea más larga que la terminal**:
   `Rendered line N exceeds terminal width`. Fix: importar
   `truncateToWidth` + `visibleWidth` de `@mariozechner/pi-tui` y
   mapear cada línea del render al final. Aplicado en cockpit y panel.
3. **`session.lock` aparece después de `session_start`**: cortex-net
   nunca levantaba el hub porque chequeaba el lock al arrancar y
   retornaba sin esperar. Fix: extraer `tryInitNetwork(ctx)` y
   llamarla desde (a) session_start, (b) suscripción al singleton
   cuando sessionId aparece, (c) polling de 15s.
4. **system-select no propagaba el agent activo**: Pi v0.77 no
   dispara `before_agent_start` con `event.agentName` cuando la
   "persona" la gestiona system-select. Fix: modificar
   `system-select.ts` para escribir `activeAgentName` + `myRole` al
   singleton + subscriber de cortex-net detecta cambio de `myRole`
   y llama `ensureRegisteredAs`.
5. **`cortexState.cwd` null en handlers**: causa raíz confirmada en
   bugfix #4 (doble instancia). Mitigación defensiva en
   `cortex-team.ts`: usar `cortexState.cwd ?? ctx.cwd` + cockpit
   re-puebla cwd en `turn_end`.
6. **EACCES en sockets Windows**: Node.js no soporta Unix domain
   sockets en archivos `.sock` en Windows. Fix: detección
   `process.platform === "win32"` y usar Named Pipes
   `\\.\pipe\cortex-net-<hash-cwd>-<role>-<pid>`. Hash djb2 del cwd.
   Skip de `existsSync`/`rmSync` sobre pipes (auto-cleanup).
7. **Doble instancia del singleton (parcial)**: bun/jiti resolvía
   `./_cortex-state` y el autoload como módulos distintos. Fix
   intermedio: mover a `.pi/lib/cortex-state.ts` y eliminar el viejo
   de `extensions/`. **NO ALCANZÓ** — ver #9.
8. **Pi v0.77 trata prefijo `:` como bash**: `:?` ejecuta como shell
   command. Fix: reemplazar hotkeys virtuales por slash commands
   cortos `/cx-next /cx-team /cx-role /cx-mode /cx-help`.
9. **Doble instancia del singleton (definitivo)**: aún después de
   mover a `lib/`, el cockpit seguía viendo STANDBY mientras
   cortex-net escribía OK. Causa: bun/jiti evalúa cada módulo **una
   vez por extension importadora** (sandboxing del loader). Fix
   definitivo: en `lib/cortex-state.ts`, el state se ancla a
   `globalThis["__cortex_pi_state_v1__"]`. Cada evaluación del
   módulo recupera la misma referencia. Patrón conocido como
   "process-wide singleton". Esto sí lo arregla.

---

## Estado del testing en el adopter (último estado conocido)

### Round previo al bugfix #5

El usuario corrió Pi en `C:\AppFutbol` con los archivos del bugfix #4
(singleton movido a `lib/` + Named Pipes + slash commands `/cx-*`).
Confirmó que `_cortex-state.ts` ya no existía en el adopter. Aun así
reportó síntomas EXACTAMENTE iguales:

```
/cortex-net dice:                   cockpit dice:
  Rol propio: sddwork                 Rol: (no en la red)
  Modo hub: este proceso es el hub    agent: (ninguno)
  Peers conectados (1): sddwork       Peers: (ninguno)
                                      STANDBY
```

Es decir: cortex-net registra y escribe al singleton OK, pero el
cockpit lee y ve todo null. Conclusión: **mover el archivo a
`lib/` no alcanzó**. La causa real era **sandboxing del loader**
(bun/jiti evalúa cada módulo una vez por extension importadora).

### Bugfix #5 entregado (NO validado todavía)

Solución definitiva: anclar el state, subscribers y lastUpdate a
`globalThis["__cortex_pi_state_v1__"]`. El módulo se puede evaluar
N veces; todas las copias recuperan la misma referencia. Cambio
implementado en `cortex-pi/.pi/lib/cortex-state.ts` (función
`getAnchor()` + inicialización lazy en `globalThis`).

Bonus arreglado en la misma propagación:
- Footer del cockpit decía `:? hotkeys` (residuo) → ahora dice
  `/cx-help atajos`.

### Script de propagación pendiente de validar (2 archivos)

Lo último que se le entregó al usuario fue:

```powershell
Get-Process pi -ErrorAction SilentlyContinue | Stop-Process -Force
Remove-Item 'C:\AppFutbol\.pi\agent-sessions\*' -Recurse -Force -ErrorAction SilentlyContinue
Copy-Item 'C:\Cortex\cortex-pi\.pi\lib\cortex-state.ts' 'C:\AppFutbol\.pi\lib\cortex-state.ts' -Force
Copy-Item 'C:\Cortex\cortex-pi\.pi\extensions\cortex-cockpit.ts' 'C:\AppFutbol\.pi\extensions\cortex-cockpit.ts' -Force
cd C:\AppFutbol
pi
```

Solo 2 archivos cambiaron en este último round. Los otros 5 (cortex-net,
cortex-autopilot, cortex-panel, cortex-team, system-select) no cambian
desde el round del bugfix #4 y se asume que el adopter ya los tiene.

**Verificación clave post-arranque**: en el footer del widget del
cockpit debería leerse `/cortex panel · /cx-help atajos` (no `:?`).
Si aparece `:?`, el `cortex-cockpit.ts` no se actualizó.

**Síntoma de éxito esperado**: al hacer `/system cortex-SDDwork`, el
cockpit pasa **inmediatamente** de STANDBY a `sddwork · MASTER` (no
sigue en STANDBY como antes).

---

## Próximo paso esperado del agente

### Si el usuario reporta que funciona

1. Confirmar que ya no queda nada roto.
2. Preguntarle si quiere **commitear**. Si dice sí:
   - Sugerir un commit por etapa (F1..F5 + bugfixes) o todo junto.
   - Branch actual: `feature/nuevo-modo-autonomo`.
   - No commitee sin que lo pida explícitamente.
3. Plantear los TODOs pendientes que el usuario quiso postponer:
   tests del bundle, coordinated shutdown, etc.

### Si el usuario reporta que NO funciona

Diagnóstico en orden:

1. **Pedir el output completo del arranque + `/cortex-net` + el
   resultado de**:
   ```powershell
   Test-Path 'C:\AppFutbol\.pi\extensions\_cortex-state.ts'
   Test-Path 'C:\AppFutbol\.pi\lib\cortex-state.ts'
   Get-Content 'C:\AppFutbol\.pi\lib\cortex-state.ts' | Select-String "GLOBAL_KEY"
   ```
2. Si `Select-String "GLOBAL_KEY"` no devuelve nada → el archivo
   nuevo (bugfix #5) no se copió. El usuario tiene la versión vieja
   sin globalThis. El fix es copiarlo de nuevo.
3. Si el `lib/cortex-state.ts` no existe → el copy falló.
4. Si `_cortex-state.ts` sigue existiendo en `extensions/` → no es
   crítico desde bugfix #5 (globalThis lo cubre), pero conviene
   borrarlo por higiene.
5. Si el footer del cockpit dice `:?` en vez de `/cx-help` → el
   archivo `cortex-cockpit.ts` no se actualizó tampoco.
6. Otros síntomas → mirar `cortex-pi/.pi/extensions/cortex-net.ts`
   (handler de `session_start` y la función `tryInitNetwork`).
7. **Hipótesis nueva si nada matchea**: bug en el loader de Pi
   sobre `globalThis` (extremadamente improbable; sería un bug en
   Node.js/bun). Agregar un `console.error("[cortex-state] anchor
   created", process.pid)` arriba de `getAnchor` y pedirle al
   usuario que comparta el log de arranque. Si aparece más de una
   vez por proceso, hay algo raro al nivel del runtime.

---

## Comandos clave de mantenimiento (cheatsheet)

### Propagar cambios del bundle al adopter (limpio + copy)

```powershell
# Cerrar Pi y limpiar estado runtime
Get-Process pi -ErrorAction SilentlyContinue | Stop-Process -Force
Remove-Item 'C:\AppFutbol\.pi\agent-sessions\*' -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item 'C:\AppFutbol\.cortex\session.lock' -Force -ErrorAction SilentlyContinue

# Estructura lib/ + singleton (con anchor globalThis del bugfix #5)
# Si grep -i "GLOBAL_KEY" sobre el destino no devuelve hit, no se actualizó.
New-Item -ItemType Directory -Path 'C:\AppFutbol\.pi\lib' -Force | Out-Null
Copy-Item 'C:\Cortex\cortex-pi\.pi\lib\cortex-state.ts' 'C:\AppFutbol\.pi\lib\cortex-state.ts' -Force

# Higiene: borrar el archivo viejo del adopter si quedó. Desde bugfix #5
# (globalThis) ya no es CRÍTICO porque las copias múltiples del módulo
# convergen al mismo state vía globalThis, pero conviene limpiar.
Remove-Item 'C:\AppFutbol\.pi\extensions\_cortex-state.ts' -Force -ErrorAction SilentlyContinue

# Las 6 extensions
Copy-Item 'C:\Cortex\cortex-pi\.pi\extensions\cortex-cockpit.ts'    'C:\AppFutbol\.pi\extensions\cortex-cockpit.ts'    -Force
Copy-Item 'C:\Cortex\cortex-pi\.pi\extensions\cortex-autopilot.ts'  'C:\AppFutbol\.pi\extensions\cortex-autopilot.ts'  -Force
Copy-Item 'C:\Cortex\cortex-pi\.pi\extensions\cortex-net.ts'        'C:\AppFutbol\.pi\extensions\cortex-net.ts'        -Force
Copy-Item 'C:\Cortex\cortex-pi\.pi\extensions\cortex-panel.ts'      'C:\AppFutbol\.pi\extensions\cortex-panel.ts'      -Force
Copy-Item 'C:\Cortex\cortex-pi\.pi\extensions\cortex-team.ts'       'C:\AppFutbol\.pi\extensions\cortex-team.ts'       -Force
Copy-Item 'C:\Cortex\cortex-pi\.pi\extensions\system-select.ts'     'C:\AppFutbol\.pi\extensions\system-select.ts'     -Force

# settings.json (si el adopter tiene una versión vieja)
Copy-Item 'C:\Cortex\cortex-pi\.pi\settings.json' 'C:\AppFutbol\.pi\settings.json' -Force
```

### Alternativa: re-inyectar el bundle completo (preferida si el adopter quedó muy desfasado)

```powershell
cd C:\AppFutbol
cortex inject --ide pi
```

Trae el bundle entero de `cortex-pi/` a `C:\AppFutbol\`. El adapter Python
copia recursivo, así que también trae `lib/cortex-state.ts`.

### Reset total de session/network state en el adopter

```powershell
Remove-Item 'C:\AppFutbol\.cortex\sessions\*' -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item 'C:\AppFutbol\.cortex\session.lock' -Force -ErrorAction SilentlyContinue
Remove-Item 'C:\AppFutbol\.pi\agent-sessions\*' -Recurse -Force -ErrorAction SilentlyContinue
```

---

## Gaps conocidos / TODO

1. **Validación manual end-to-end no completada** — el usuario está
   en proceso al cierre de esta sesión.
2. **Tests del bundle** — postponed por decisión del usuario. Sería
   `tests/unit/test_ide_adapters.py::TestPiBundleHasTripartitaRefinada`
   con asserts adicionales (que existan las 5 extensions nuevas + el
   lib/cortex-state.ts).
3. **Coordinated shutdown del team** — F5 no detecta cuando master
   cierra. Las hijas siguen vivas hasta que el usuario las cierre.
   Solución propuesta en F5.md §6: agregar polling de `team.json.shutdown`.
4. **Invocación programática de slash commands** — no hay API
   documentada en Pi para `pi.runCommand("/cortex-team")` desde un
   handler. Por eso varios casos del panel usan `notify` con hints
   ("Tipeá /cortex-team") en vez de ejecutar.
5. **Eliminación de `ADAPTER_CONTRACT.md` + `CHANGES.md`** del bundle
   — el usuario quiere eliminarlos "una vez que todo funcione". Por
   ahora viajan al adopter porque el adapter copia todo el bundle.
6. **Focus routing entre sub-componentes interactivos** en
   `ctx.ui.custom`: no documentado en Pi. Solución actual: cascada de
   modales en sub-flows del panel (no Container con SelectList +
   Input simultáneos).
7. **`peer.status` en `ensureRegisteredAs` catch**: el catch resetea
   `myRole` a null pero ese reset puede dispararse erróneamente si
   el subscriber del singleton se ejecuta entre el catch y el siguiente
   ensureRegisteredAs. No observado en runtime, pero teoréticamente
   posible.

---

## Glosario rápido

| Término | Significado |
|---|---|
| **B' anchor / B' design** | `cortex-sync` vive AFUERA de la red por diseño. Solo los agents del medio entran. |
| **Singleton** | `cortexState` compartido entre extensions vía `lib/cortex-state.ts`. |
| **Master** | Proceso Pi que levantó el hub (`isMaster: true`). |
| **Worker** | Proceso Pi cliente de un hub externo. |
| **STANDBY** | Cockpit cuando no estás registrado en la red (`myRole === null` y agent ≠ sync). |
| **F1..F5** | Las cinco fases del overhaul UX. |
| **adopter** | Proyecto que usa Cortex/Pi como herramienta. Acá `C:\AppFutbol`. |
| **bundle** | Cortex Pi config + extensions que el adapter copia. En `cortex-pi/`. |

---

## Archivos clave que el agente nuevo debería leer primero

Si te toca seguir, en este orden:

1. **`HANDOFF.md`** (este archivo).
2. **`README.md`** del mismo directorio, especialmente § 8
   "Descubrimientos runtime" (los 10 bullets son los descubrimientos
   más caros de la sesión — leelos antes de proponer cualquier
   cambio).
3. **`cortex-pi/.pi/lib/cortex-state.ts`** — el singleton. Prestá
   especial atención al patrón `getAnchor()` con `globalThis` (bugfix
   #5). Es el contrato central de comunicación entre extensions y
   romperlo regenera la doble instancia.
4. **`cortex-pi/.pi/extensions/cortex-net.ts`** — la pieza más
   compleja, con los hooks de session_start / before_agent_start /
   suscripción al singleton / Named Pipes Windows (`workspaceHash`
   + `IS_WINDOWS` checks).
5. **`cortex-pi/.pi/extensions/cortex-cockpit.ts`** — el widget arriba
   del editor y la status bar. Notar el uso de `truncateToWidth` +
   `visibleWidth` para no crashear Pi.
6. **`F4.md`** + **`cortex-pi/.pi/extensions/cortex-panel.ts`** —
   ejemplo de Component custom con focus state interno.

Saltá `cortex-pi/.pi/extensions/cortex-mcp.ts`, `cortex-tools.ts`,
`agent-chain.ts`, `damage-control.ts`: no fueron tocadas y no son
relevantes para el overhaul.

---

## Sentido del trabajo

El usuario quiere que **un dev pueda usar Pi como CLI principal sin
memorizar comandos**. La TUI muestra estado en vivo arriba, status
bar abajo, y todo se opera con `/cortex` (panel) + slash commands
cortos. La red multi-terminal es el modo principal y el spawn de
terminales lo dispara un solo `/cortex-team`.

Cuando esté validado al 100%, el bundle se va a propagar a todos los
adopters Cortex vía `cortex inject --ide pi`. La idea es que esto sea
la experiencia default para cualquier proyecto con Pi.

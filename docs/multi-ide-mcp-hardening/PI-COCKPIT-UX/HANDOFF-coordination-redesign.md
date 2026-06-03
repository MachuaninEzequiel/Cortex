# HANDOFF — Pi 2.5+net: fixes post-validación + rediseño de coordinación

> **Léeme primero.** Este handoff cubre TODO lo que hizo el agente de esta
> sesión (≈ 29-may → 01-jun 2026), que es una **continuación** del trabajo
> del agente anterior (ver `HANDOFF.md` y `README.md` de este mismo
> directorio para la base: el bundle Pi 2.5+net y las fases F1–F5 del
> cockpit). Acá está el estado real y preciso para continuar.

---

## 0. TL;DR — dónde estamos y qué sigue

El bundle Pi 2.5+net (cockpit/autopilot/panel/team/net + singleton) ya
existía (F1–F5, agente anterior). Este agente:

1. **Diagnosticó la causa raíz real** del bug histórico "registrado OK pero
   cockpit STANDBY": NO era la doble instancia del singleton (el fix
   `globalThis` ya estaba y es correcto) sino que **Pi v0.77 no expone el
   nombre del agente en ningún evento**, y el cockpit/cortex-net lo leían
   (`event.agentName` → `undefined`) y pisaban `myRole` cada turno.
2. **Round A — fix fundamental (VALIDADO por el usuario, COMMITEADO):** el
   role loop ahora persiste.
3. **Round B — `/cortex-team` + panel (VALIDADO parcialmente, en working tree):**
   spawn sin `just`, detección de WezTerm, el panel ejecuta de verdad.
4. **Round C — rediseño de coordinación, FASES 1-3 (esbuild-clean, NO
   validado en runtime todavía — el usuario está por probarlo):** gate humano
   sobre los envíos + cola de inbound disciplinada + indicador en el cockpit.
5. **PENDIENTE INMEDIATO → FASE 4: actualizar los 7 prompts de agentes** en
   `cortex-pi/.pi/agents/` para que el comportamiento de los agentes use el
   nuevo modelo (ver § 6 y § 8). Esto es lo próximo a hacer cuando el usuario
   confirme que la mecánica (Fases 1-3) anda.

**Branch:** `feature/nuevo-modo-autonomo`. **Round A commiteado**; **Round B
y C en working tree (sin commitear)** — verificá con `git status`.

---

## 1. Quién es el usuario + entorno

- Dev Windows 11, habla español (rioplatense), decisiones rápidas y claras.
- Repo Cortex en `C:\Cortex`. Adopter de prueba en `C:\AppFutbol` (una PWA
  de tácticas de fútbol; ahí corre Pi sobre el bundle inyectado).
- **Arranca Pi con `pi` pelado, NUNCA con `just`** (no lo tiene instalado).
  Por eso la UX carga vía `settings.json` `defaultExtensions`, no vía recetas
  `just`. NO le sugieras flujos basados en `just`.
- **Su terminal es WezTerm** (Windows, con config gráfica propia). No usa
  Windows Terminal por default.
- Modelo en el adopter: `opencode-go/qwen3.7-max` (no Claude). El IDE host es
  "opencode-go" y **no expone Task tool de subagentes** en ese entorno.
- **Quiere humano-en-el-loop** pero comunicación autónoma entre agentes.
- Trabaja iterativo: diseña → debate → da OK → recién ahí se codea. Respetá
  ese ritmo. No commitea salvo que se lo pidas (lo hace él).
- Le importa que la documentación vaya a la par del código.

---

## 2. Hechos VERIFICADOS de la API de Pi v0.77 (ground truth — NO re-descubrir)

Verificados contra los tipos instalados en
`C:\Users\chuch\AppData\Roaming\npm\node_modules\@earendil-works\pi-coding-agent\dist\core\extensions\types.d.ts`:

1. **NINGÚN evento expone el agente activo.** `BeforeAgentStartEvent` =
   `{type, prompt, images?, systemPrompt, systemPromptOptions}` — **sin
   `agentName`**. `AgentStartEvent` = `{type}`. `SessionStartEvent` =
   `{type, reason, previousSessionFile?}`. `ExtensionContext` (el `ctx`) no
   tiene campo de agente. `BuildSystemPromptOptions` tampoco. → La identidad
   de rol la administra **system-select** (única fuente de verdad).
2. **No hay API para invocar un slash command ni una tool desde una
   extensión.** Por eso: (a) los alias cortos (`/cx-team`, `/cx-mode`,
   `/cx-role`) se **co-registran en la extensión dueña del comando real**
   (mismo handler); (b) las acciones cross-extensión se exponen vía un
   **registro en el singleton** (ver `NetActions`/`TeamActions` en
   `cortex-state.ts`).
3. **`tool_call` PUEDE bloquear**: el handler puede devolver
   `{ block: true, reason }` (`ToolCallEventResult`), y `event.input` es
   **mutable** in-place. El handler es async → podés `await ctx.ui.confirm/
   select/editor` antes de decidir. ESTE es el mecanismo del gate de salida.
4. **`pi.sendUserMessage(content, {deliverAs?})` siempre dispara un turno.**
   Es el mecanismo para que el receptor de un inbound **ejecute directo**
   (auto-trigger).
5. **UI disponible** (`ctx.ui`): `select(title, options[])`, `confirm`,
   **`input(title, placeholder?)`** (texto libre), **`editor(title, prefill?)`**
   (multilínea), `notify(msg, level)`, `setStatus`, `setWidget`, `custom`.
6. **`ctx.isIdle()`** dice si el agente está libre (no streameando).
   `ctx.hasPendingMessages()` también existe.
7. El paquete instalado es **`@earendil-works/pi-coding-agent`**; el código
   importa tipos de ahí y de `@mariozechner/pi-tui` (este último resuelve en
   runtime — el cockpit renderiza, está probado).
8. **Verificación de sintaxis sin runtime:** `npx esbuild <archivo>.ts
   --outdir=/tmp/x` transpila sin resolver imports → atrapa errores de
   sintaxis. Usalo después de cada edición (yo lo hice en cada paso).

Más detalle en las memorias `[[pi-no-agent-identity-in-events]]` y
`[[cortex-net-coordination-redesign]]`.

---

## 3. Línea de tiempo de esta sesión (qué se hizo, en orden)

### Diagnóstico (read-only + workflow)
Análisis forense de las 8 piezas del bundle + verificación contra los tipos
de Pi. Conclusión central: el agente anterior **diagnosticó mal** (perseguía
la doble instancia del singleton). La causa real del STANDBY era el clobber de
`agentName` (§2.1). También se documentaron ~20 problemas (cluster crítico +
medium/low) — ver § 10.

### Round A — fix fundamental (✅ VALIDADO, ✅ COMMITEADO)
El role loop ahora persiste entre turnos. Archivos:
- **`cortex-cockpit.ts`**: ELIMINADO el handler `before_agent_start` que
  pisaba `myRole`/`activeAgentName` con `null` (leía el `event.agentName`
  inexistente). El cockpit es **lector puro**. También: status bar muestra
  `STANDBY` (no `WORKER`) cuando `myRole===null`.
- **`cortex-net.ts`**: `before_agent_start` deriva el rol de
  `cortexState.activeAgentName` (no del evento). Comentario clave en el código.
- **`cortex-autopilot.ts`**: el gate `tool_call` leía `event.tool?.name`
  (inexistente) → corregido a `event.toolName` (el shape real, igual que
  `damage-control.ts`).
- **system-select** es la única fuente de `activeAgentName`/`myRole`.

### Round B — `/cortex-team` + panel (✅ spawn VALIDADO por el usuario; resto esbuild-clean)
El usuario confirmó: el documenter spawnea en una **pestaña de WezTerm** con
su agente y rol correctos. Cambios:
- **`cortex-team.ts`**: el spawn ya **NO usa `just`** — lanza `pi` directo con
  `CORTEX_NET_ROLE=<rol>` **y** `CORTEX_AGENT=<agente>` en el env (así el peer
  carga el stack UX completo de `settings.json` y system-select activa la
  persona). **Detección de WezTerm**: `weztermCli()` resuelve `wezterm.exe`
  (¡OJO! `WEZTERM_EXECUTABLE` apunta a `wezterm-gui.exe`, que NO tiene el
  subcomando `cli`; hay que usar `wezterm.exe` del mismo dir o del PATH). Usa
  `spawnSync` (no `spawn` async) para saber **de verdad** si abrió y mostrar el
  error real si falla. Fallback PowerShell-safe. **Coordinated shutdown**: el
  master, al cerrar (reason `quit`), marca `team.json`; los workers de la misma
  `session_id` avisan (no se auto-cierran). Co-registra **`/cx-team`** (mismo
  handler que `/cortex-team`). Publica `registerTeamActions({spawn})` para el panel.
- **`system-select.ts`**: en `session_start`, si está la env `CORTEX_AGENT`,
  **auto-activa esa persona** (match case-insensitive) → arregla el
  "agent: (ninguno)" del worker.
- **`cortex-net.ts`**: publica `registerNetActions({isReady, listPeers, send,
  broadcast})` para que el panel ejecute de verdad; **propaga teardown** al
  singleton en `/cortex-mode Solo`, `/cortex-role Auto`, `/cortex-net-shutdown`
  (antes dejaban rol/peers fantasma); co-registra **`/cx-mode`** y **`/cx-role`**.
- **`cortex-autopilot.ts`**: la sugerencia se refresca vía `subscribe` al
  singleton (antes quedaba stale); texto corregido (sin hotkeys muertos
  `:t`/`:l` ni `just role-*`); **sacó los alias inertes** `/cx-team`/`/cx-role`/
  `/cx-mode` (ahora viven en sus extensiones reales). Quedan `/cx-next`,`/cx-help`.
- **`cortex-panel.ts`**: las acciones EJECUTAN de verdad — "Mandar mensaje" y
  "Broadcast" usan `ctx.ui.input` + `getNetActions()`; "Agregar peers" usa
  `getTeamActions().spawn`; "Audit log"/"Ver transcript" leen los logs reales.
- **`cortex-state.ts`**: agregó `ROLE_TO_AGENT`/`agentForRole`, `NetActions`/
  `TeamActions` + `registerNetActions`/`getNetActions`/`registerTeamActions`/
  `getTeamActions` (registros anclados al mismo `globalThis` anchor del singleton).

### Round C — rediseño de coordinación, FASES 1-3 (✅ esbuild-clean, ⏳ NO validado runtime)
Ver § 6 (el diseño) y § 7 (qué se tocó). El usuario está por probar la mecánica.

---

## 4. Por qué el rediseño de coordinación (el problema que motivó Round C)

El usuario corrió una sesión real (transcripta en **`conversacion.md`** de
este dir — OJO: NO `conversacion1.md`, que es una sesión vieja de análisis de
AppFutbol). Pasó esto:
- SDDwork (master) + documenter (worker observer) spawneados OK.
- SDDwork leyó la sesión, **detectó Deep Track**, revisó la red, vio que **no
  había designer/implementer** y que su IDE no tiene Task tool → **hizo TODO
  solo** sin comunicarse con nadie. El documenter nunca recibió un mensaje.

Dos problemas que el usuario marcó:
1. **El flujo no funciona**: los agentes no se comunican. Causa profunda
   (verificada en `cortex-net.ts`): la red era **pasiva** — un inbound solo se
   encolaba y NO disparaba un turno; el receptor no reaccionaba sin que su
   humano tipeara algo. Y los prompts modelaban delegación **solo IDE-native
   (Task tool)**, no multi-terminal.
2. **SDDwork degradó a solo en silencio**: el prompt le ordena "si no hay
   peers, seguí solo en Fast Track". El usuario quiere que en **Deep** FRENE y
   le **recomiende un equipo**, y que él decida.

---

## 5. El DISEÑO ACORDADO (el contrato — debatido y cerrado con el usuario)

Esto es lo que hay que cumplir. Está también en la memoria
`[[cortex-net-coordination-redesign]]`.

1. **Gate de SALIDA (humano aprueba todo lo que sale).** Todo
   `cortex_net_send`/`cortex_net_broadcast` que invoca un agente se intercepta
   con un handler `tool_call` → diálogo 3-vías **Enviar / Editar / No enviar**
   (loop: "Editar" abre `ctx.ui.editor` y re-pregunta). "No enviar" →
   `block:true`. La comunicación es **autónoma** (el agente decide qué/a quién)
   pero **prohibida sin confirmación del humano emisor**.
2. **El RECEPTOR ejecuta DIRECTO** (sin re-confirmar: el humano emisor ya
   aprobó). El inbound **auto-dispara un turno** (`pi.sendUserMessage`) cuando
   el agente está **libre** (knob elegido: **(a)** directo si libre).
3. **Cola de inbound disciplinada** (resuelve la preocupación de concurrencia
   del usuario): (a) **nunca interrumpe** un turno en vuelo (si está ocupado,
   encola); (b) **uno por turno, FIFO** (no mezcla mensajes sin relación); (c)
   al terminar **NO encadena solo** → avisa "📨 N en cola" y el usuario libera
   el siguiente con **`/cx-inbox`** (esa pausa es la **ventana de revisión**;
   liberar ≠ re-aprobar contenido, es solo control de ritmo); (d) **visible en
   el cockpit** ("📨 N en cola").
4. **Mensajes = instrucción + contexto, NUNCA código/archivos** (eso vive en el
   filesystem). **Tope ~1500 chars**; si excede, el gate avisa y deja editar.
5. **Auto-reply implícita ELIMINADA** → envíos **explícitos** gated. Si el
   receptor quiere responder, manda un `cortex_net_send` (que pasa por SU gate).
   Esto **corta loops** (cada hop necesita un humano que diga "sí").
6. **Gate de consulta SOLO en Deep.** En Fast, SDDwork va directo (sabe que lo
   hace solo). En Deep: **conoce los presets de equipo, recomienda uno y FRENA**
   hasta que el usuario arme el team (`/cortex-team`) o diga "hacelo solo".
   SDDwork **guía** la composición.
7. **Actualizar TODOS los prompts** de `cortex-pi/.pi/agents/`.

---

## 6. Estado de implementación detallado (qué se tocó en Round C — Fases 1-3)

Todo esbuild-clean. Símbolos clave (referencio por nombre, no por línea, que
se mueve):

### `cortex-pi/.pi/lib/cortex-state.ts`
- Nuevo `interface InboundSnapshot { from; type; preview }` + campo
  `inbound: InboundSnapshot[]` en `CortexState` (inicializado en `getAnchor` y
  en `reset()`). Es **solo visibilidad** (la cola real vive en cortex-net).

### `cortex-pi/.pi/extensions/cortex-net.ts` (el grueso)
- **Clase `CortexNetClient`**: se eliminó `inboundForReply` y `sendAutoReply`
  (auto-reply). Se agregó `onInbound: (() => void) | null` (callback al
  handler de Pi), `dequeueInbound()` (saca uno FIFO) e `inboundCount()`.
  `processInbound` ahora encola y llama `this.onInbound?.()` (ya no setea
  inboundForReply).
- **Factory**: 
  - `let lastCtx: any` — último ctx visto (lo capturan session_start,
    before_agent_start, turn_start, turn_end, tool_call, /cx-inbox); lo usan
    los callbacks async para `ctx.isIdle()`/`ctx.ui.notify()`.
  - `syncInboundSnapshot()` — refleja la cola del cliente al singleton.
  - `deliverNextInbound()` — saca UNO de la cola y lo entrega vía
    `pi.sendUserMessage(...)` (dispara turno; instruye al agente a ejecutar
    directo y, si responde, usar cortex_net_send).
  - `handleNewInbound()` — al llegar un inbound: notifica; si `lastCtx.isIdle()`
    y es el único en cola → `deliverNextInbound()` (knob a). Se cablea con
    `client.onInbound = handleNewInbound` en `ensureRegisteredAs` (al lado de
    `onPeerEvent`).
  - **Gate de salida**: `pi.on("tool_call", ...)` que, para
    `cortex_net_send`/`cortex_net_broadcast`, hace el loop
    `ctx.ui.select(["✅ Enviar","✏️ Editar","❌ No enviar"])` + `ctx.ui.editor`,
    con aviso si `body.length > NET_MSG_CAP` (1500). Mutar `input.body` al
    enviar; `{block:true}` al rechazar.
  - **`/cx-inbox`**: comando que libera el siguiente de la cola (si idle).
  - `before_agent_start`: se **quitó** la inyección de inbounds al systemPrompt
    (ahora se entrega por sendUserMessage). Quedó solo la lógica de registro.
  - `turn_start`/`turn_end`: capturan lastCtx; turn_end ya no hace auto-reply,
    y si quedan inbounds en cola avisa "📨 N en cola · /cx-inbox" (no encadena).
  - `session_shutdown`: limpia `inbound: []` en el singleton.
- **OJO — consecuencia**: al sacar la auto-reply, el patrón `cortex_net_await`/
  `cortex_net_get` (request-response por `reply`) quedó **en desuso** (ya nadie
  manda `kind:"reply"` salvo... nadie). Los prompts de Fase 4 deben redirigir a
  envíos explícitos. Las tools siguen registradas (no rompen), pero el `await`
  va a timeoutear. Decidir en Fase 4 si se deprecan formalmente.

### `cortex-pi/.pi/extensions/cortex-cockpit.ts`
- Render del widget: línea "📨 N en cola (de X) · /cx-inbox" cuando
  `cortexState.inbound.length > 0`. Status bar: sufijo "📨N" en el slot de peers.

---

## 7. FASE 4 — PENDIENTE (lo próximo a hacer)

Actualizar los prompts en `cortex-pi/.pi/agents/` para que el COMPORTAMIENTO
de los agentes use el modelo de § 5. Los nombres exactos (frontmatter `name:`)
están confirmados: `cortex-sync`, `cortex-SDDwork`, `cortex-code-designer`,
`cortex-code-explorer`, `cortex-code-implementer`, `cortex-security-auditor`,
`cortex-test-verifier`, `cortex-documenter`.

### 7.1 `cortex-SDDwork.md` (el más importante)
- **Deep Track**: reescribir para que, al detectar Deep, **FRENE y recomiende
  un equipo** conociendo los presets de `/cortex-team` (que están en
  `cortex-team.ts` → `PRESETS`: *Deep full = designer+implementer+documenter*,
  *Deep + audit*, *Design pair*, *Audit pair*, *Explorer*, *Documenter
  observer*). Flujo: recomendar → **parar** → el usuario arma el team
  (`/cortex-team`) y avisa, o dice "hacelo solo".
- **QUITAR** las instrucciones que lo mandan a ir solo en silencio (hoy en el
  Pre-flight: *"si no hay peers, seguís funcionando... trabajando solo"* y en
  Mecanismos de delegación: *"Si tu IDE NO soporta delegación nativa: ejecutá
  el flujo en Fast Track"*).
- **Fast Track queda igual** (directo, sin gate de consulta).
- Reglas de comunicación nuevas (ver 7.3).

### 7.2 — invariante a corregir en TODOS los prompts del medio
Hoy los prompts **PROHÍBEN** "responder a inbounds con cortex_net_send" (era
la era de la auto-reply: *"tu próximo mensaje es auto-empaquetado como reply,
NO llames cortex_net_send"*). Eso hay que **INVERTIRLO**: ahora la auto-reply
NO existe; para comunicar/responder, el agente **SÍ** usa `cortex_net_send`
explícito (que pasa por el gate del humano). Buscá y reemplazá esas reglas en
SDDwork, designer, explorer, implementer, security, test-verifier, documenter.

### 7.3 Reglas de comunicación nuevas (para los 7 del medio)
Redactar (adaptado por rol):
- "Para coordinar con un peer, usá `cortex_net_send(to_role, msg_type, body)`.
  **El humano va a confirmar/editar/rechazar cada envío** — no sale nada sin su
  OK. No es loop: respondé/coordiná con sends explícitos."
- "Los mensajes son **instrucción + contexto, ≤ ~1500 chars, NUNCA código ni
  archivos** (eso vive en el filesystem / la Cortex Session)."
- "**Cuando recibís un mensaje, ejecutá la instrucción directamente** (el
  humano emisor ya lo aprobó). Si necesitás responder, mandá un cortex_net_send."
- (documenter) Mantener modo observer: solo `question`/`observe`, ahora gated;
  ejecutar directo al recibir; sin auto-reply.

### 7.4 `cortex-sync.md`
Vive **fuera de la red** (B' anchor, secuencial al inicio). Probablemente solo
una aclaración de que la coordinación cortex-net arranca después de él. Revisar,
no reescribir.

### 7.5 `system.md` / `AGENTS.md`
Si describen el protocolo cortex-net (auto-reply, "señales no payloads",
delegación), alinearlos con el modelo nuevo.

> **Recordatorio del usuario:** ritmo iterativo. Tras Fase 4, esperá su OK /
> testing antes de dar por cerrado. No commitees salvo que lo pida.

---

## 8. Cómo propagar al adopter + cómo probar

El usuario corre `pi` en `C:\AppFutbol` (que tiene su propia copia del bundle
en `C:\AppFutbol\.pi\`). **No puedo escribir en `C:\AppFutbol` (el harness lo
bloquea — está fuera del repo); el usuario corre la copia.** Patrón:

```powershell
$s = 'C:\Cortex\cortex-pi\.pi'; $d = 'C:\AppFutbol\.pi'
# Round C (Fases 1-3) — los 3 archivos de la mecánica:
Copy-Item "$s\lib\cortex-state.ts"          "$d\lib\cortex-state.ts"          -Force
Copy-Item "$s\extensions\cortex-net.ts"     "$d\extensions\cortex-net.ts"     -Force
Copy-Item "$s\extensions\cortex-cockpit.ts" "$d\extensions\cortex-cockpit.ts" -Force
# (Round B ya fue propagado y probado; Fase 4 son .md de agents → copiarlos cuando estén)
```
Después: cerrar TODAS las terminales pi (master + workers comparten cortex-net)
y reabrir. `cortex-state.ts` de AppFutbol ya tiene el anchor `globalThis`
(idéntico al canónico) — verificable con `grep GLOBAL_KEY`.

**Test de la mecánica (Fases 1-3)** — lo que el usuario está por hacer:
1. Gate de salida: pedirle al agente (master) que mande un cortex_net_send →
   debe aparecer **Enviar/Editar/No enviar**.
2. Recepción directa: al Enviar, el documenter recibe (notif "📨…") y arranca solo.
3. Cola + review window: 2 mensajes seguidos con el receptor ocupado → 2º
   encola → cockpit "📨 1 en cola" + barra "📨1" → al terminar avisa →
   `/cx-inbox` libera.
4. Cockpit: indicador "📨 N en cola" (widget) + "📨N" (status bar).

---

## 9. Estado de VALIDACIÓN

| Round | Qué | Estado |
|---|---|---|
| A | Role loop / clobber fix | ✅ Validado por el usuario + **commiteado** |
| B | Team spawn WezTerm + persona | ✅ Spawn validado (documenter abre con agente+rol) |
| B | Panel ejecuta / `/cx-*` / teardown / registries | ⚠️ esbuild-clean, runtime no probado a fondo |
| C | Fases 1-3 (gate/cola/cockpit) | ⏳ esbuild-clean, **NO validado runtime** (usuario probando) |
| 4 | Prompts | ❌ No empezado |

---

## 10. Gaps conocidos / deferred (NO bloqueantes para el rediseño)

**Backend / MCP (lo de `conversacion1.md`, el usuario lo dejó para después):**
- `cortex_create_spec` **timeouts** (la op completa pero la respuesta tarda).
- `verification_hooks`: el schema dice `type: string` pero el server valida
  cada elemento como `object` → el agente entró en loop de ~6 intentos.
- `cortex_session_checkpoint` rechaza `source` fuera de un enum (faltan roles
  como `cortex-code-security`/`test-verifier`/`documenter` en el enum).

**Pi, del audit de ~20 problemas (medium/low, no tocados):**
- Race de arranque del `session.lock` (ventana hasta 15s) (#7).
- Fuga de subscribers en `reload`/`fork` (el cockpit re-suscribe sin guarda).
- `resolveSessionId` no valida frescura/PID del lock (lock huérfano → hub muerto).
- `spawn` (no-wezterm) sin `.on('error')` (#9) — éxito optimista.
- `isMaster` puede quedar stale (#11); el `catch` de registro resetea myRole (#12).
- `cortex_net_await`/`get` en desuso tras quitar auto-reply (ver § 6).

**Higiene:**
- El `README.md` y `HANDOFF.md` (viejos) de este dir todavía cuentan la teoría
  del `globalThis` como "solución definitiva" — quedaron desactualizados frente
  a la causa raíz real (§2.1). Conviene anotarlo.
- Las recetas `just role-*` cargan stack ciego, pero el usuario no usa `just`.

---

## 11. Archivos clave para leer (en orden)

1. **Este handoff.**
2. Memorias en `C:\Users\chuch\.claude\projects\C--Cortex\memory\`:
   `cortex-net-coordination-redesign.md`, `pi-no-agent-identity-in-events.md`,
   `user-runs-pi-not-just.md` (el índice está en `MEMORY.md`).
3. **`conversacion.md`** (este dir) — la sesión real que motivó el rediseño.
4. `cortex-pi/.pi/lib/cortex-state.ts` — el singleton + registros.
5. `cortex-pi/.pi/extensions/cortex-net.ts` — la pieza central (gate, cola,
   registro, hooks). Leer la clase `CortexNetClient` + el factory.
6. `cortex-pi/.pi/agents/cortex-SDDwork.md` y `cortex-documenter.md` — los que
   hay que reescribir en Fase 4.
7. `HANDOFF.md` + `README.md` (viejos, agente anterior) — base F1–F5.

---

## 12. Resumen para arrancar rápido

> El próximo paso es **Fase 4: reescribir los 7 prompts** (§7) para que los
> agentes usen el modelo de § 5 — **pero primero confirmá con el usuario que
> la mecánica de Fases 1-3 (gate/cola/cockpit) anda en runtime**, porque eso
> no está validado todavía. No commitees sin pedírselo. Respetá el ritmo
> diseño→debate→OK→código.

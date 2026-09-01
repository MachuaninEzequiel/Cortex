
# Revisión profunda — Subsistema 12: `cortex-pi/**`, README/CHANGELOG del repo, `docs/vision/*`, `.cortex/*`, plugins IDE

> Revisor: agente experto en el entorno Pi + narrativa/visión del proyecto Cortex.
> Alcance leído completo: `cortex-pi/AGENTS.md`, `cortex-pi/README.md`, `cortex-pi/justfile`,
> `cortex-pi/.pi/**` (system.md, settings.json, mcp.json, damage-control-rules.yaml, 8 agents,
> 10 extensiones TS, lib/cortex-state.ts, 2 skills, teams.yaml, agent-chain.yaml,
> cortex-model-overrides.json), `cortex-pi/extensions/*.ts` (4), `README.md` (repo),
> `CHANGELOG.md`, `docs/vision/*.md` (5), `.cortex/AGENT.md`, `.cortex/system-prompt.md`,
> `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, `.cursor-plugin/plugin.json`.
> Solo lectura: no se modificó nada del repo.

---

## 1. Propósito y arquitectura interna

### 1.1 Qué es `cortex-pi/`

Es el **bundle de salida** de `cortex inject --ide pi`: la configuración completa del
**Pi Coding Agent** (`@mariozechner/pi-coding-agent`) adaptada a la gobernanza Cortex
"Release 2.5 + cortex-net". El propio README lo define como "la salida esperada de
`cortex setup agent` con CLI=pi", generada por `cortex/ide/adapters/pi.py`
(`cortex-pi/README.md` § "Por qué hay un ADAPTER_CONTRACT.md separado").

Capas internas:

| Capa | Archivos | Responsabilidad |
|---|---|---|
| Gobernanza declarativa | `AGENTS.md`, `.pi/system.md`, `.cortex/AGENT.md`, `.cortex/system-prompt.md` | Reglas: pre-flight obligatorio con `cortex_sync_ticket`, aislamiento de ecosistema ("si no empieza con `cortex_`, no entra"), anchors fijos sync/documenter |
| Personas de agente | `.pi/agents/*.md` (8) | sync, SDDwork (orquestador), explorer, designer, implementer, security-auditor, test-verifier, documenter. Frontmatter con `name/description/tools` |
| Red peer-to-peer | `.pi/extensions/cortex-net.ts` (2301 líneas) | Hub+clientes por Unix socket / Named Pipe Windows; roles canónicos; mensajes-señal ≤1500 chars |
| Bridge al backend | `.pi/extensions/cortex-tools.ts` (CLI por subprocess), `.pi/extensions/cortex-mcp.ts` (cliente MCP stdio embebido) | Expone `cortex_*` como tools nativas de Pi |
| UI/UX | `cortex-cockpit.ts`, `cortex-panel.ts`, `cortex-footer.ts`, `cortex-autopilot.ts` (hotkeys/sugerencias), `system-select.ts`, `cortex-team.ts` (spawn multi-terminal) | Widgets y paneles TUI, todo client-side (0 tokens) |
| Seguridad runtime | `damage-control.ts` + `.pi/damage-control-rules.yaml` | Intercepta `tool_call` de bash: bloquea/pide confirmación según patrones y rutas |
| Estado compartido | `.pi/lib/cortex-state.ts` | Singleton anclado a `globalThis` con pub/sub entre extensiones |
| Fallback secuencial | `agent-chain.ts` + `.pi/agents/agent-chain.yaml` | Pipelines secuenciales para IDEs sin red (Codex) |
| Legacy "Premium UI" | `cortex-pi/extensions/*.ts` (dashboard, memory-widget, spec-tracker, subagent-widget) | Versión anterior del stack UX; **no está referenciada por settings.json** |

### 1.2 Modelo de ejecución (diseño B′: dos anchors + red en el medio)

```
cortex-sync (ANCHOR INICIO — FUERA de la red, secuencial)
   ↓ abre Session (.cortex/sessions/<id>.yaml + .cortex/session.lock) + persiste Spec
[humano arma equipo con /cortex-team → la red se enciende]
   ↓
SDDwork ⇄ designer ⇄ explorer ⇄ implementer ⇄ security ⇄ test-verifier ⇄ documenter(observer)
   ↓ coordinan por cortex-net; cada envío lo aprueba el humano; estado oficial = checkpoints
[usuario corre cortex finish-session o /cortex-documenter]
   ↓
cortex-documenter (ANCHOR FIN — cierra la red y persiste)
```

Evidencia: `cortex-pi/AGENTS.md:23-40` (modelo), `.pi/system.md:29-32` (sync fuera de la red),
`.pi/extensions/cortex-net.ts:84-92` (`CORTEX_ROLES` sin sync).

### 1.3 Clases/módulos clave de `cortex-net.ts`

- `CortexNetHub` (`cortex-net.ts:366-717`): servidor por workspace. El primer proceso que
  arranca gana el socket (`tryStart`, :371-417, connect-test de 500ms). Mantiene
  `Map<CortexRole, Peer>`, hace relay 1:1 (`send`/`reply`, :557-635), fanout
  (`broadcast`, :523-555), push de eventos de peers (`broadcastPeerEvent`, :666-685),
  pruning por heartbeat vencido (`pruneStale`, :687-702; HEARTBEAT_MS=5s, STALE_AFTER_MS=15s, :100-101).
- `CortexNetClient` (:721-1047): socket inbound por rol+pid, registro en hub, heartbeat con
  status (idle/busy/observe), cola FIFO de inbounds entregada UNO por turno vía
  `pi.sendUserMessage` (:1135-1146), buffer de replies (`getReply`/`awaitReply`, :1006-1027).
- Gate de salida humano-en-el-loop: hook `tool_call` que intercepta `cortex_net_send`
  y `cortex_net_broadcast` con diálogo Enviar/Editar/No enviar (`cortex-net.ts:1538-1582`),
  cap NET_MSG_CAP=1500.
- Logs: audit (sin cuerpos, `cortex-net.log`) y transcript (con cuerpos,
  `cortex-net-transcript.log`), ambos en `.pi/agent-sessions/` (:219-273). El transcript es
  fuente de documentación diferenciada para el documenter (tool `cortex_net_transcript`, :1861-1987).
- Recuperación de master: `/cortex-make-master` (:2239-2299) + single-flight en init
  (`initInFlight`, :1271-1291) para la race de doble init documentada en comentarios jun-2026.

### 1.4 Estado compartido (`cortex-state.ts`)

Singleton anclado a `globalThis` (`__cortex_pi_state_v1__`, `cortex-state.ts:506-606`)
porque el loader de Pi v0.77 evalúa el módulo una vez por extensión que lo importa
(:508-524). Publica `registerNetActions`/`registerTeamActions` (:610-630) para que el panel
`/cortex` ejecute acciones reales sin LLM. Los comentarios documentan dos bugfix históricos:
mover el archivo fuera de `.pi/extensions/` (autoload) y anclarlo a globalThis.

---

## 2. Flujo de datos y puntos de entrada/salida

### Entradas al subsistema

1. **Usuario** → TUI de Pi (prompt, slash commands `/system`, `/cortex`, `/cortex-team`,
   `/cx-inbox`, shortcut `ctrl+shift+k`).
2. **Backend Cortex MCP** → levantado por `cortex-mcp.ts` leyendo `.pi/mcp.json`
   (comando virtual `pipx-bin:cortex-memory:cortex` resuelto a mano contra pipx,
   `cortex-mcp.ts:213-232`). Registra cada tool MCP como tool Pi con colapso de prefijo
   `mcp_cortex_cortex_*` → `cortex_*` (:417-426).
3. **CLI Cortex** → `cortex-tools.ts` ejecuta `search/context/remember/save-session/
   create-spec/forget/stats/doctor/agent-guidelines/sync-vault` vía `spawnSync` con
   timeout 60s (:79-111).
4. **Filesystem** → `.cortex/session.lock` (fuente de session_id,
   `cortex-net.ts:343-357`; polling de respaldo del cockpit cada 3s,
   `cortex-cockpit.ts:333-355`), `.pi/agents/*.md`, `.pi/agent-sessions/{*.sock, logs, team.json}`.

### Salidas

1. Checkpoints/notes al backend vía tools MCP (`cortex_session_checkpoint`,
   `cortex_write_doc`, `cortex_close_session` — ver prompts de los agentes).
2. Mensajes P2P entre procesos Pi (relay por hub).
3. Logs de auditoría/transcript en `.pi/agent-sessions/`.
4. Terminales hijas spawneadas (`cortex-team.ts:141-363`: WezTerm → wt/cmd → osascript →
   tmux → alacritty/kitty/gnome-terminal/konsole/xterm → clipboard fallback), trackeadas en
   `.pi/agent-sessions/team.json` con flag coordinated-shutdown (:365-404, :640-687).

### Quién llama a este subsistema

- El usuario final (arranque `just cortex` / `pi`).
- `cortex inject --ide pi` / `cortex setup agent` generan/copian este bundle
  (mirror canonical `.cortex/subagents/` → `.pi/agents/`, ver CHANGELOG 0.5.0 Plan 05).
- Tests del repo lo tratan como artefacto: `tests/unit/test_ide_adapters.py::TestPiBundleHasTripartitaRefinada`
  y `tests/integration/test_cross_ide_smoke.py` referencian `cortex-pi`.

---

## 3. Invariantes y decisiones de diseño importantes

1. **Sync nunca entra a la red** (modelo B′). Triple declaración: `AGENTS.md:23-27,58`,
   `.pi/system.md:29-32,54`, `cortex-net.ts:315-321` (retorna null para `cortex-sync`).
   El cockpit muestra "sync (B′ — afuera de la red)" (`cortex-cockpit.ts:138-140`).
2. **Los mensajes son señales, no payloads**: ≤1500 chars, nunca código/archivos;
   el contrato persistente es la Cortex Session + checkpoints (`AGENTS.md:63-67`,
   `cortex-net.ts:18-22`).
3. **Humano en el loop para toda salida**: cada `cortex_net_send` pasa por el gate
   interactivo (`cortex-net.ts:1538-1582`). Los inbounds se ejecutan directo porque
   "el emisor ya lo aprobó" (`AGENTS.md:41-46`).
4. **Sin auto-reply**: el rediseño may-2026 eliminó `sendAutoReply`; responder exige un
   `cortex_net_send` explícito gated (`cortex-net.ts:1031-1034`, :1496-1499).
   ⚠️ Pero `cortex-pi/README.md` (sección "Auto-reply implícita") aún documenta la mecánica
   vieja — contradicción directa con `AGENTS.md` y el código (ver §5.3).
5. **Estado oficial ≠ conversación**: checkpoints > mensajes; el documenter cita el
   transcript solo como fuente "🔗 in-flight", y "prevalece siempre lo verificable"
   (`cortex-documenter.md:216-260, 344-360`).
6. **Deny-list de tools nativas por rol** (no allow-list, para no romper las MCP):
   `system-select.ts:150-162,225-262`; SDDwork pierde write/edit si hay implementer en la
   red (regla S1, :235-240).
7. **Override opt-in de modelo/thinking por rol**, persistido en
   `.pi/cortex-model-overrides.json` (hoy `{}`), default = modelo de sesión
   (`system-select.ts:19-22,508-571`).
8. **Compatibilidad dual Linux/Windows** en toda la capa de red: Named Pipes con hash djb2
   del cwd para evitar colisiones (`cortex-net.ts:181-217`), guards `IS_WINDOWS` alrededor de
   `existsSync/rmSync` (inútiles sobre `\\.\pipe\`).
9. **Fallback secuencial preservado**: `agent-chain.yaml` + `agent-chain.ts` para IDEs sin
   red; steps terminan en checkpoint, no en YAML AgentHandoff (`agent-chain.yaml:11-16`).
10. **Deprecación consistente de YAML AgentHandoff**: prohibido en los 8 prompts de agente;
    `damage-control-rules.yaml:83-120` mantiene `handoffRules` heredadas de 0.5.0.

---

## 4. Evolución histórica (README + CHANGELOG + docs/vision)

- **CHANGELOG** muestra la línea: 2.0.0 (RRF real, embeddings vectoriales) → 2.4.0
  (Facade/DI, pipeline module, delegate MCP experimental) → 2.5.0 (enterprise org.yaml +
  "Pi Premium Edition") → 0.3.0-normalización de versionado → 0.4.0 (early adopters) →
  0.5.0 Tripartita Refinada (AgentHandoff schema, validate_handoff) → 0.6.0 Multi-IDE/MCP
  Hardening (**elimina el delegate experimental** que detonó el incidente 2026-05-15) →
  Pluggable Middle Fases 00–04 (Session primitive, mata YAML inline, deprecó gran parte de
  autopilot) → Fase 05 opencode hooks → 06 TUI → 07 CI plugin → 08 quality gates →
  09 proposal/design/tasks.
- Ironía histórica útil: `AgentHandoff` fue **introducido** en 0.5.0 y **deprecado** en el
  Pluggable Middle pocas fases después; `damage-control-rules.yaml:88-120` conserva las
  `handoffRules` muertas.
- **docs/vision**: documentos estratégicos de abril-2026. `ARQUITECTURA-GLOBAL-CORTEX.md`
  describe el backbone ONNX compartido y el promotion pipeline (aún válido);
  `Cortex-Vision-DevSecOps-a-DevSecDocOps.md` y `Cortex-Plan-DevSecDocOps.md` describen un
  estado previo (`cortex-memory.py`, extensión VS Code, `vault/` en raíz = layout legacy) y
  proponen módulos (`pr_capture`, `doc_generator`, `pr-context`) que ya existen en otra forma.
  `PLAN_CORTEX_MAXIMO_IMPACTO.md` es el más honesto: documenta versionado inconsistente
  (pyproject 3.0.0 vs `__version__` 0.1.0), suite roja (5 tests), promotion pipeline roto,
  falta de threat model — varios items luego addressados (normalización 0.3.0 Alpha).

---

## 5. Bugs potenciales, código muerto, duplicación, riesgos (con file:line)

### 5.1 Rotos / alta probabilidad de fallo en runtime

1. **`cortex-pi/extensions/cortex-subagent-widget.ts` no compila**:
   - `:366` y `:414` usan `args?.trim() ? ? ""` (nullish coalescing escrito `? ?` con
     espacio → SyntaxError).
   - `:23` importa `./themeMap.ts` que **no existe** en `cortex-pi/extensions/`.
   - `:19` usa `require()` en módulo ESM (mezcla de sistemas).
   Conclusión: este archivo está muerto en su estado actual; cualquier intento de cargarlo
   con `-e` falla.
2. **Los tres `plugin.json` apuntan a directorios inexistentes**:
   `.claude-plugin/plugin.json:47-51` (idem `.codex-plugin`, `.cursor-plugin`) declaran
   `"hooks": {"directory": "cortex/autopilot/hooks"}`, pero `cortex/autopilot/hooks/` fue
   eliminada (CHANGELOG, sección "Removed" del Pluggable Middle). Verificado: el directorio
   no existe. Cualquier instalador que honre esos manifiestos fallará o ignorará hooks.
3. **`CORTEX_CONFIG_PATH` es una variable muerta**: grep en `cortex/**/*.py` da **cero**
   lecturas de esa env. Se setea en `.pi/mcp.json:8` (`${cwd}/config.yaml`) y en
   `cortex-tools.ts:90-93`. Además `${cwd}/config.yaml` **no existe en layout v2** (el config
   vive en `.cortex/config.yaml`, ver README "Workspace Layout v2"). Funciona hoy solo porque
   el backend ignora la env y descubre el layout (`cortex/core.py:157-192`). Riesgo: alguien
   confía en esa env para apuntar a otro config y no pasa nada.
4. **`cortex-spec-tracker.ts:210,360,399` lee `.cortex/specs/`** pero en layout v2 los specs
   viven en `.cortex/vault/specs/` (README "Layout v2": `vault/ ← specs/`). En un proyecto
   nuevo el widget mostrará siempre "No hay SPEC activo".
5. **`justfile:14` fija `set shell := ["powershell", "-Command"]`**: todas las recetas
   (incluidas `role-*` con sintaxis `$env:`) son Windows-only, mientras `cortex-pi/README.md`
   (Prerrequisitos) y el README principal (`brew install just` para Mac/Linux) venden uso
   cross-platform. En Linux/macOS `just cortex` falla al interpretar las recetas.
6. **Contradicción de precedencia de rol** entre docs y código: `justfile:25-31` y
   `cortex-team.ts:144-152` dicen que `CORTEX_NET_ROLE` "gana sobre el agent activo… queda
   clavada en ese rol pase lo que pase"; el docstring de `resolveRole`
   (`cortex-net.ts:294-314`) dice lo mismo. Pero el código (`cortex-net.ts:315-321`) retorna
   el rol derivado del `activeAgentName` del singleton **siempre que exista**, y
   `system-select` auto-activa persona por `CORTEX_AGENT` en las terminales hijas
   (`system-select.ts:362-381`), escribiendo `activeAgentName`. Resultado: en cualquier
   terminal donde haya persona activa (incluidas las hijas), el pin de `CORTEX_NET_ROLE` se
   ignora silenciosamente; si el usuario cambia de agente con `/system` en una terminal
   "clavada", el rol cambia igual.

### 5.2 Código muerto / duplicación

7. **Todo `cortex-pi/extensions/` (4 archivos, ~1100 líneas) es legacy no cargado**:
   `settings.json:4-15` lista solo extensiones de `.pi/extensions/`. Además usan una API
   distinta y presumiblemente vieja de Pi (`Extension` objeto con `ctx.addCommand("/sdd")`,
   `ctx.ui.showAlert`, `ctx.ui.createWidget`, `ctx.on("input")` — `cortex-dashboard.ts:105-156`,
   `cortex-memory-widget.ts:108`) frente a la API actual (`pi.registerCommand`,
   `pi.registerTool`, `ctx.ui.select/notify/setWidget`). Alto riesgo de confusión: el README
   de cortex-pi los describe como parte del árbol vigente (`cortex-pi/README.md:17-22`).
8. **Duplicación de constantes de roles**: `CORTEX_ROLES`/`AGENT_TO_ROLE` definidos dos veces
   (`cortex-net.ts:84-92,284-292` y `lib/cortex-state.ts:357-392`) con comentario
   "Mantener alineado" — drift garantizado a mediano plazo. Ídem `ROLE_TO_AGENT` solo existe
   en el singleton.
9. **Dos resolutores de binario pipx casi idénticos**: `resolveCortexBin`
   (`cortex-tools.ts:33-75`) y `resolvePipxBin`/`resolvePipxPython` (`cortex-mcp.ts:85-167`)
   repiten la misma cascada de candidatos con ligeras divergencias.
10. **`handoffRules` en `damage-control-rules.yaml:88-120` no tiene enforcement en este
    bundle**: el parser de `damage-control.ts:663-722` solo lee `bashToolPatterns`,
    `zeroAccessPaths`, `readOnlyPaths`, `noDeletePaths`; la sección `handoffRules` se ignora.
    Es contrato declarativo huérfano (herencia de 0.5.0 post-deprecación de AgentHandoff).
11. **Referencias rotas en `cortex-pi/README.md`**: menciona `CHANGES.md` y
    `ADAPTER_CONTRACT.md` en el árbol del directorio (`cortex-pi/README.md:20-24` y §final),
    pero ambos archivos **no existen** en `cortex-pi/` (verificado; sobrevivieron renombrados
    en `docs/multi-ide-mcp-hardening/ADAPTER_CONTRACT-netupdate.md`, `CHANGES-netupdate.md`).
12. **`cortex-model-overrides.json` vacío (`{}`)**: mecanismo completo implementado
    (`system-select.ts:171-208`) sin ningún override configurado — no es bug, pero hoy es
    superficie sin uso ni cobertura.

### 5.3 Documentación contradictoria / drift

13. **Auto-reply**: `cortex-pi/README.md` § "Filosofía de cortex-net" dice "Auto-reply
    implícita … NO llamés `cortex_net_send` para responder — eso crea ping-pong". `AGENTS.md:44-48`
    y `.pi/system.md:44-47` dicen exactamente lo contrario ("No hay auto-reply"). El código
    confirma la versión nueva (`cortex-net.ts:1031-1034`). El README del bundle quedó viejo.
14. **`cortex-pi/README.md` (Setup paso 3) instruye `cortex session status`**, comando que no
    existe en la CLI documentada del repo (existe `cortex session current/list/show/status`…
    el README principal lista `current`, no `status`). Drift menor pero afecta onboarding.
15. **Docs de visión desactualizadas respecto del código actual**: `docs/vision/Cortex-Plan-DevSecDocOps.md`
    propone crear `cortex/pr_capture.py`, `doc_generator.py` y templates propios, cuando el
    producto actual resolvió eso con `cortex ci`, Session primitive y `cortex/documenter`;
    habla de `vault/` en raíz (legacy) y de una extensión VS Code que no está en el árbol.
    Sirven como contexto histórico, no como especificación.
16. **CHANGELOG con 5 entradas `[Unreleased]` apiladas en orden no cronológico**
    (Phase 07 arriba, luego Phase 05, 09, 06, 08…) — imposible reconstruir el orden real de
    integración; complica bisección y release notes.

### 5.4 Riesgos técnicos / seguridad

17. **El hub cortex-net no autentica peers**: cualquiera que conecte al socket
    (Unix domain world-accessible dentro del repo, o Named Pipe global en Windows) puede
    hacer `register` con cualquier rol (`dispatch` case register, `cortex-net.ts:443-471` no
    valida identidad más allá del session_id del emisor) y enviar mensajes a los agentes,
    que los ejecutan directo ("el emisor ya lo aprobó"). Amenaza local-only, pero
    inconsistente con la postura `zeroAccessPaths` del mismo bundle.
18. **El transcript guarda cuerpos completos en plaintext** en
    `.pi/agent-sessions/cortex-net-transcript.log` (`cortex-net.ts:259-273`) dentro del
    workspace — puede terminar commiteado si el `.gitignore` no cubre `.pi/agent-sessions/`
    (el README pide agregarlo manualmente, `cortex-pi/README.md` § Setup paso 2).
19. **Parser YAML a mano por regex** (`damage-control.ts:663-722`): sensible a formato
    (indentación, comillas, comentarios inline). Un cambio inocente del YAML puede dejar
    reglas sin cargar silenciosamente (fallback a DEFAULT_RULES solo si lanza excepción).
    Además patrones como `eval\s*\(` bloquean cualquier comando bash que mencione `eval(`
    incluso en un `echo`, y `matchesPath` convierte globs a regex naive (`*`→`.*`),
    por lo que `**/.env` matchea también `.env.example` en cualquier comando.
20. **Acoplamiento total a versiones concretas de Pi**: múltiples comentarios dependen de
    bugs/comportamientos de "Pi v0.70/v0.77" (`cortex-state.ts:508-524`,
    `cortex-net.ts:1460-1467`, `cortex-cockpit.ts:381-390`, `cortex-autopilot.ts:468-480`,
    `justfile` "pi v0.70+"). No hay guard de versión; un upgrade de Pi puede romper
    silenciosamente el stack UX (ya pasó: `(event as any).agentName` era siempre undefined).
21. **Race residual master/worker**: mitigada con single-flight (`cortex-net.ts:1271-1291`)
    y `/cortex-make-master`, pero el propio comentario admite el síntoma observado en
    jun-2026 ("dueño del hub pero queda como WORKER"). La recuperación es manual.
22. **Heartbeat/status propagados con latencia**: `setStatus` espera el próximo heartbeat de
    5s (`cortex-net.ts:777-782`); el pruning de 15s significa que un peer muerto sigue
    listándose hasta 15s y los envíos hacia él se pierden silenciosamente
    (`relayTo` traga errores, :639-658). No hay ack end-to-end de delivery al receptor.

---

## 6. Deudas y oportunidades de refactor

1. **Unificar el mapa de roles** en `lib/cortex-state.ts` y hacer que `cortex-net.ts`
   importe de ahí (borrar duplicados). Ya existe el patrón de import `../lib/`.
2. **Extraer un módulo `pipx-resolve.ts` compartido** para `cortex-tools.ts` y
   `cortex-mcp.ts`.
3. **Decidir el destino de `cortex-pi/extensions/`**: borrarlas o portarlas a la API actual.
   Hoy son 1100 líneas de ruido con un archivo que ni compila.
4. **Regenerar `cortex-pi/README.md` desde el adapter** (el ADAPTER_CONTRACT dice que ese doc
   es el checklist del mantenedor): corregir CHANGES/ADAPTER_CONTRACT faltantes,
   auto-reply viejo, `cortex session status`, y documentar que el justfile es Windows-only
   (o hacerlo portable con detección de shell).
5. **Reemplazar el parser regex de damage-control por un YAML real** (bun tiene yaml
   disponible o embeber un mini-parser probado) + tests unitarios del parser.
6. **Autenticación ligera del hub**: token compartido escrito en `.pi/agent-sessions/` con
   permisos 600, verificado en `register`/`send`.
7. **Normalizar CHANGELOG**: colapsar los `[Unreleased]` en versiones ordenadas o usar
   Keep-a-Changelog de verdad.
8. **Marcar `docs/vision/` como histórico** (banner "estado de 2026-04, no especificación")
   o moverlos a `docs/history/`, como el propio PLAN_CORTEX_MAXIMO_IMPACTO sugiere separar
   visión de roadmap.
9. **Eliminar `CORTEX_CONFIG_PATH`** o hacer que el backend realmente la lea; hoy es
   placebo en tres lugares.
10. **Guard de compatibilidad de versión de Pi**: chequear `process.env`/API disponible al
    session_start y degradar con mensaje claro en vez de comportamientos fantasma.

---

## 7. Preparación para un cambio grande: qué tocaría primero y qué es frágil

### Orden sugerido

1. **Higiene de muertos (barato, alto valor)**: borrar/portar `cortex-pi/extensions/`;
   arreglar o eliminar `cortex-subagent-widget.ts`; limpiar `plugin.json`s (hooks inexistentes);
   quitar `handoffRules` huérfanas.
2. **Fuente única de verdad de roles y resolución pipx** (§6.1–6.2) antes de tocar cualquier
   cosa de cortex-net: casi todas las extensiones leen el singleton.
3. **Regenerar docs del bundle desde `cortex/ide/adapters/pi.py`** e incluir un test de
   consistencia (ya existe el patrón `TestPiBundleHasTripartitaRefinada`; extenderlo a
   existencia de archivos referenciados y comandos CLI citados).
4. **Solo entonces** evolucionar cortex-net (auth, acks, recovery automática).

### Qué es frágil

- **`cortex-net.ts` (2301 líneas)** concentra protocolo, transporte, logging y UI en un
  archivo; cualquier cambio de formato de `NetMessage` impacta hub, cliente, transcript y
  cockpit a la vez. No hay tests automatizados de la capa de red (todo el subsistema TS está
  fuera de `pytest`; solo se testean markers de texto del bundle).
- **El singleton globalThis** funciona por efecto colateral del loader; un cambio en cómo Pi
  carga extensiones rompe la sincronización cockpit/net sin error visible (el síntoma
  documentado: "registrado como sddwork" pero cockpit en "STANDBY").
- **Los prompts de agentes son contratos operativos**: cambian el comportamiento del sistema
  tanto como el código. El mirror canonical→bundle (`inject --ide pi`) cubre `.pi/agents/`,
  pero **no** las extensiones ni `AGENTS.md`/skills del bundle: esa mitad se edita a mano y
  es donde ya se acumuló el drift.
- **Windows/Linux dual-path**: cada fix de sockets se hizo dos veces; un refactor de
  transporte debería abstraer el transporte antes de crecer.

### Salud general del subsistema

Conceptualmente excelente (anchors fijos, señales-no-payload, humano-en-el-loop, fallback
secuencial, observabilidad client-side sin tokens) y con evidencia de debugging serio
(bugfixes documentados in-place con causa raíz). Pero la higiene del bundle está deteriorada:
~1300 líneas de código muerto/roto en `extensions/`, docs del bundle contradictorias con el
código en puntos clave (auto-reply, precedencia de rol), configs placebo (`CORTEX_CONFIG_PATH`),
manifiestos de plugin rotos y cero cobertura de tests sobre la capa TypeScript. El núcleo
(`.pi/extensions` vigentes + lib singleton) funciona y está bien comentado; el riesgo está
en el perímetro documental y en el acoplamiento a versiones de Pi no verificadas.

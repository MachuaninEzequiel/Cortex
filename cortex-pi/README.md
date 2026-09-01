# Cortex Pi — Release 2.5 + cortex-net

> **Tu Pi, clonada a la filosofía de Cortex Release 2.5 con red peer-to-peer.**  
> Sistema de Gobernanza para DevAgents con Memoria Híbrida RRF, Intelligent Routing, y coordinación distribuida.

## ¿Qué hay aquí?

Este directorio contiene la configuración completa de **Pi Coding Agent**
construida específicamente para el proyecto Cortex Release 2.5 con la
extensión `cortex-net`: un protocolo peer-to-peer que permite a los
agentes de Cortex coordinarse en tiempo real durante el trabajo.

```
cortex-pi/
├── AGENTS.md                       # Governance Rules (Release 2.5+net)
├── README.md                       # Este archivo
├── justfile                        # Recetas (incluye role-* por rol)
├── extensions/                     # Premium UI (dashboard, widgets)
│   ├── cortex-dashboard.ts
│   ├── cortex-memory-widget.ts
│   ├── cortex-spec-tracker.ts
│   └── cortex-subagent-widget.ts
└── .pi/
    ├── system.md                   # Global Governance Prompt
    ├── settings.json               # Config Pi (carga cortex-net por default)
    ├── mcp.json                    # MCP server config (binario nativo cortex-cli)
    ├── damage-control-rules.yaml   # Reglas de seguridad runtime
    ├── cortex-model-overrides.json # Overrides de modelo del workspace
    ├── agents/
    │   ├── teams.yaml              # Definición de teams
    │   ├── agent-chain.yaml        # FALLBACK para IDEs sin red
    │   ├── cortex-sync.md          # ANCHOR INICIO (fuera de la red)
    │   ├── cortex-SDDwork.md       # Orquestador (en la red)
    │   ├── cortex-code-designer.md # Designer (en la red)
    │   ├── cortex-code-explorer.md # Explorer (en la red)
    │   ├── cortex-code-implementer.md # Implementer (en la red)
    │   ├── cortex-security-auditor.md # Security (en la red)
    │   ├── cortex-test-verifier.md # Test verifier (en la red)
    │   └── cortex-documenter.md    # ANCHOR FIN + observer (en la red)
    ├── extensions/                 # 11 extensiones activas
    │   ├── cortex-net.ts           # ⭐ protocolo peer-to-peer
    │   ├── cortex-tools.ts         # Bridge al CLI de Cortex (nativo)
    │   ├── cortex-mcp.ts           # Adaptador MCP (nativo)
    │   ├── cortex-panel.ts         # Panel de estado
    │   ├── cortex-cockpit.ts       # Cockpit de sesión
    │   ├── cortex-autopilot.ts     # Acciones auto-ok del motor
    │   ├── cortex-team.ts          # Equipos/roles
    │   ├── cortex-footer.ts        # Footer de estado
    │   ├── agent-chain.ts          # Cadena de agentes (fallback)
    │   ├── system-select.ts        # Selector de agente activo
    │   └── damage-control.ts       # Auditoría runtime de bash
    ├── lib/
    │   └── cortex-state.ts         # Estado compartido del workspace
    ├── skills/                     # Skills Obsidian + Cortex
    └── themes/
        └── cortex-dark.json
```

## Filosofía Release 2.5+net

### El cambio principal: **dos anchors + red en el medio**

Antes (Release 2.5 pre-net) los agentes pasaban output entre sí
secuencialmente (`sync → SDDwork → security → test → documenter`).
Ahora, el medio del flujo es una **red peer-to-peer**: los agentes se
hablan entre sí en vivo cuando necesitan coordinarse, sin pasar por un
orquestador central.

Los anchors **se mantienen inmovibles**:

- 🔒 **`cortex-sync` al inicio**, secuencial, **fuera de la red**: protege
  la integridad del pre-flight y hace la spec inmutable durante el resto
  de la sesión.
- 🔒 **`cortex-documenter` al final**, con un modo nuevo: **observer
  in-flight**. Está en la red desde temprano escuchando lo que pasa
  entre los demás agentes. Llega al cierre con contexto fresco, no solo
  con el briefing read-only.

### 🟢 Fast Track

Para tareas simples (1-2 archivos): SDDwork implementa directamente.
**La red no se activa** — sos un solo agente trabajando solo.

### 🔴 Deep Track

Para tareas complejas: SDDwork delega a designer/explorer/implementer.
**Los tres viven en la red simultáneamente** y pueden preguntarse cosas,
proponer ajustes y reportar bloqueos sin esperar a SDDwork.

### ⚠️ Modo SDD Forzado

Si el usuario pide explícitamente "vía SDD", se usa Deep Track obligatorio.

## Filosofía de cortex-net

**Los mensajes son señales, no payloads.** El contrato real entre agentes
sigue siendo la **Cortex Session + checkpoints** persistidos en backend.
La red solo mueve coordinación liviana: preguntas, propuestas, bloqueos,
handoffs.

5 tipos de mensaje:

| Tipo | Significado | Quién lo usa |
|---|---|---|
| `question` | "necesito aclaración" | Todos los del medio |
| `proposal` | "propongo X, espero accept/reject" | Designer principalmente |
| `blocker` | "no puedo continuar" | Implementer, security, test |
| `handoff` | "delego turno explícitamente" | SDDwork en Deep Track |
| `observe` | "me suscribo silencioso" | Documenter |

**Auto-reply implícita**: si recibís un inbound, tu próximo mensaje
assistant es auto-empaquetado como reply al sender. NO llamés
`cortex_net_send` para responder — eso crea ping-pong loops. Esta
mecánica está copiada literal de `disler/pi-vs-claude-code`.

## Instalación

### Prerrequisitos

```bash
# Pi Coding Agent
npm install -g @mariozechner/pi-coding-agent

# just (task runner)
brew install just      # macOS
winget install Casey.Just  # Windows
cargo install just     # cualquier OS

# Bun (runtime para extensiones TypeScript)
curl -fsSL https://bun.sh/install | bash

# Cortex backend (Release 2.5+)
pipx install cortex-memory  # o desde tu fork local
```

### Setup

```bash
# 1. Copiá esta carpeta al root de tu proyecto Cortex
cp -r cortex-pi/.pi /path/to/Cortex/
cp -r cortex-pi/extensions /path/to/Cortex/
cp cortex-pi/AGENTS.md cortex-pi/justfile /path/to/Cortex/

# 2. Asegurate de que .pi/agent-sessions/ esté en .gitignore
echo ".pi/agent-sessions/" >> /path/to/Cortex/.gitignore

# 3. Verificá que tenés una sesión activa de Cortex
cortex session status

# 4. Iniciá Cortex Pi
cd /path/to/Cortex
just cortex
```

## Modos de uso

### 🟢 Camino canónico: solo `pi`

Una vez injectado el bundle al workspace (vía `cortex inject pi` o
copiando manualmente), todo lo que necesitás es:

```bash
cd /path/to/Cortex
pi
```

Y listo. Pi lee `.pi/settings.json` y carga automáticamente las 5
extensiones (cortex-tools, cortex-mcp, cortex-net, system-select,
damage-control), las skills, y los 8 agents. Arranca con
`cortex-sync` como persona default.

Después, todo se maneja desde slash commands dentro de Pi:

| Slash command | Función |
|---|---|
| `/system` | Selector TUI: cambiar de agent (sync → SDDwork → designer → …) |
| `/system-list` | Listar agents disponibles |
| `/cortex-net` | Estado de la red: peers conectados, sesión actual, rol propio, últimas 5 entradas del audit log |
| `/cortex-mode` | Toggle Full / Solo: encender o apagar cortex-net sin reiniciar Pi |
| `/cortex-role` | Forzar rol o volver a modo auto (selector TUI con todos los roles disponibles) |
| `/cortex-net-shutdown` | Cerrar el hub si este proceso lo levantó (afecta a TODOS los peers del workspace) |
| `/cortex-tools` | Lista las tools Cortex registradas |
| `/mcp` | Estado de los servidores MCP |
| `/chain` | Selector de pipeline fallback (solo con agent-chain.ts cargado) |

### Flujo típico paso a paso (sin tocar terminal)

```
1. Abrís terminal en el workspace, escribís: pi
   → Pi arranca con cortex-sync activo y la red en standby (no hay sesión todavía)

2. Le pedís a sync que arme una spec
   → cortex-sync crea Session, escribe .cortex/session.lock, persiste spec en Vault

3. Slash: /system
   → Selector TUI · elegís cortex-SDDwork
   → before_agent_start detecta el cambio, la extensión cortex-net se entera,
     levanta el hub y se registra como rol "sddwork"
   → Notificación: "⬢ cortex-net: registrado como 'sddwork' en sesión a4f2…"

4. SDDwork decide Deep Track e invoca subagents (designer, explorer, implementer)
   → Cada subagent que activás vía /system o Task tool se registra
     automáticamente con su rol
   → Pueden hablarse vía cortex_net_send

5. Slash: /cortex-net
   → Te muestra peers conectados, audit log reciente, tu rol actual

6. Cuando terminás: /system → cortex-documenter
   → El documenter recibe el briefing + lo que escuchó como observer
   → cortex_close_session cierra la red y la Session

7. (Opcional) /cortex-net-shutdown
   → Si querés cerrar el workspace limpio antes de salir de Pi
```

### 🔵 Camino alternativo: just (para usuarios que prefieren shell)

El `justfile` sigue existiendo como conveniencia pero **es opcional**.
Las recetas son útiles principalmente para:

- **Multi-terminal demo-style** (IndyDevDan video): abrís varias
  terminales y cada una se conecta con un rol clavado.
  ```bash
  # Terminal 1
  just role-sddwork
  # Terminal 2
  just role-designer
  # Terminal 3
  just role-implementer
  ```
  En este modo, `CORTEX_NET_ROLE` se exporta y la extensión la respeta
  como override sobre el agent activo.

- **Modo Solo desde el principio** (sin red, para hotfix Fast Track):
  ```bash
  just cortex-solo
  ```
  Equivalente a `pi` + `/cortex-mode` → Solo, pero en un comando.

- **Solo cortex-net para debug** (sin tools ni MCP):
  ```bash
  just net
  ```

Si no querés usar `just`, todo lo de arriba se logra con `pi` + slash
commands dentro de la TUI. La única limitación: **abrir varias
terminales requiere abrir varias terminales** (eso es cosa del SO, no
algo que Pi pueda resolver).

## Tools registradas

### Tools Cortex (desde `cortex-tools.ts`)

`cortex_search`, `cortex_context`, `cortex_remember`,
`cortex_save_session`, `cortex_create_spec`, `cortex_forget`,
`cortex_stats`, `cortex_doctor`, `cortex_agent_guidelines`,
`cortex_sync_vault`.

### Tools MCP (desde `cortex-mcp.ts`, expuestas dinámicamente)

`cortex_sync_ticket`, `cortex_emit_proposal`, `cortex_session_status`,
`cortex_session_checkpoint`, `cortex_review_checkpoint`,
`cortex_documenter_briefing`, `cortex_write_doc`, `cortex_close_session`,
`cortex_self_review_note`, `cortex_ping`, `cortex_session_task_update`,
y demás.

### Tools cortex-net (NUEVAS, desde `cortex-net.ts`)

| Tool | Comportamiento |
|---|---|
| `cortex_net_list` | Lista peers actuales en la red |
| `cortex_net_send(to_role, msg_type, body)` | Envía mensaje, devuelve msg_id |
| `cortex_net_get(msg_id)` | Lee respuesta sin bloquear |
| `cortex_net_await(msg_id, timeout_seconds)` | Bloquea hasta recibir respuesta |

## Damage Control (sin cambios)

El sistema intercepta automáticamente operaciones peligrosas:

- 🚫 `rm -rf vault/` o `.cortex/`
- 🚫 Uso de herramientas de memoria externas (`engram`, `mem_`)
- 🚫 Secrets en código (detectados por Security Auditor)

## Teams

| Team | Agentes | Uso |
|---|---|---|
| `cortex-sddwork` | todos | Feature completa |
| `cortex-hotfix` | sync + SDDwork + documenter | Fix urgente Fast Track |
| `cortex-byo` | sync + documenter | Bring Your Own agent en el medio |
| `cortex-audit` | sync + explorer + security + documenter | Auditoría sin implementación |

## Por qué hay un `ADAPTER_CONTRACT.md` separado

Esta carpeta es la **salida esperada** de `cortex setup agent` con CLI=pi.
El adapter Python en `cortex/ide/adapters/pi.py` es quien la genera. El
`ADAPTER_CONTRACT.md` describe exactamente qué archivos genera el adapter,
qué placeholders usa, qué env vars setea, y qué archivos del usuario NO
debe sobreescribir.

Si vos sos quien mantiene Cortex: cuando actualices el adapter, ese doc
es tu checklist.

---

**Cortex Pi Release 2.5+net**: IDE de gobernanza con Intelligent Routing,
auditoría proactiva, memoria corporativa, **y coordinación peer-to-peer
en tiempo real**.

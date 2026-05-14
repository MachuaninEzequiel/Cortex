---
title: Getting started — primera instalación de Cortex
date: 2026-05-13
audience: Early adopters de Cortex (primera vez usando el framework)
---

# Cortex — primera instalación

Esta guía te lleva de **cero** a un workspace Cortex completamente funcional en menos de 5 minutos. Incluye los **tres pilares** que recomendamos para early adopters: capa agentic + WebGraph + Pipeline CI/CD.

## Prerrequisitos

Necesitás tener instalado:

- **Python 3.10 o superior** — [descargar](https://www.python.org/downloads/)
- **Git 2.30+** — [descargar](https://git-scm.com/downloads)
- **pipx** — recomendado para instalar Cortex como herramienta global

Verificación rápida:

```bash
python --version    # 3.10+
git --version
pipx --version
```

Si alguno falla, instalalo antes de continuar.

## Paso 1 — Instalar Cortex

Cloná el repo de Cortex y instalalo con pipx:

```bash
# 1. Clonar (esto se hace una vez)
git clone https://github.com/MachuaninEzequiel/Cortex.git C:\Cortex

# 2. Instalar (editable: tirás git pull para actualizar)
pipx install --editable C:\Cortex

# 3. Verificar
cortex --version
```

Cortex queda disponible globalmente como comando `cortex` desde cualquier directorio.

## Paso 2 — Setup en tu proyecto

Andá al directorio de tu proyecto (web, Python, lo que sea) y corré:

```bash
cd /ruta/a/tu/repo
cortex setup full --non-interactive --ide claude-code --git-depth 50
```

Esto crea los **tres pilares** automáticamente:

1. **Workspace agentic** en `.cortex/`:
   - `config.yaml`, `workspace.yaml`, `org.yaml` (configs).
   - `vault/` (knowledge base Markdown).
   - `memory/` (ChromaDB persistente).
   - `vault-enterprise/`, `enterprise-memory/` (para promotion futuro).
   - `skills/`, `subagents/` (asistentes Cortex).
   - `AGENT.md`, `system-prompt.md` (gobernanza tripartita).
   - `webgraph/` (UI de visualización).
   - `scripts/devsecdocops.sh` (helper bash).
2. **5 workflows GitHub Actions** en `.github/workflows/` (ya stack-aware: detecta si tu repo es Node/Python/Go/etc.).
3. **`.gitignore`** actualizado con las rutas de Cortex que no deben commiteare.

Reemplazá `--ide claude-code` por el IDE que vayas a usar (`opencode`, `pi`, `codex` son los oficialmente soportados).

## Paso 3 — Verificar

```bash
cortex doctor
```

Debería mostrar todo en `[OK]`. Si hay un `[FAIL]` o `[WARN]`:
- Releé el mensaje, suele incluir la acción concreta para resolverlo.
- Probá `cortex doctor --scope all` para incluir checks enterprise.

## Paso 4 — Conectar tu IDE

Si tu IDE soporta MCP (Model Context Protocol), inyectá la config de Cortex:

```bash
cortex inject --ide claude-code   # o opencode, pi, codex
```

Esto agrega las skills + agents + MCP config para que tu agente IA reconozca las herramientas `cortex_*` (search, sync_ticket, create_spec, save_session, etc.).

Documentación específica por IDE:

- [Cortex + Claude Code](./ide-claude-code.md)
- [Cortex + OpenCode](./ide-opencode.md)
- [Cortex + Pi Coding Agent](./ide-pi.md)
- [Cortex + Codex CLI](./ide-codex.md)

## Paso 5 — Primer flujo tripartito

Desde tu IDE, pedile al agente que implemente algo simple. Por ejemplo: "agregá un endpoint /health al server".

El agente debe:

1. Llamar `cortex_sync_ticket` con tu pedido (paso 1 obligatorio — Cortex bloquea sin esto).
2. Llamar `cortex_create_spec` para persistir un spec antes de codear.
3. Implementar el código.
4. **(Tripartita Refinada / 0.5.0)** Llamar `cortex_verify_session_claims` con la lista de claims sobre el cambio (Verification Gate). El tool cruza cada claim contra el `git diff` real y devuelve `verified` (≥2 tokens del claim aparecen en el diff) o `asserted` (sin evidencia).
5. Llamar `cortex_save_session` (o `cortex_autopilot_finish --auto`) para persistir la sesión. A partir de 0.5.0 acepta 5 parámetros opcionales (`handoff`, `blockers`, `verified_state`, `unverified_claims`, `suggested_skills`) — si la verificación detecta trabajo abierto, cerrar con `handoff=True` para que el próximo turno sepa retomarlo.

Verificá que se persistió:

```bash
cortex search "endpoint health"
```

Debería retornar el spec y la session note que se acabaron de crear. A partir de 0.5.0 los hits muestran un label `[verified]` / `[asserted]` / `[contradicted]` junto al `memory_type` cuando la memoria pasó por el Verification Gate.

### Tripartita Refinada (qué cambió en 0.5.0)

A partir de Cortex **0.5.0** (release "Tripartita Refinada"), los contratos entre subagents son **verificables**, no solo descriptivos:

- **Handoffs estructurados.** Cada agent (sync → SDDwork → explorer/implementer → documenter) cierra su turno con un bloque YAML conforme al schema `cortex.handoff.AgentHandoff`. El siguiente agent valida con `cortex_validate_handoff` antes de procesar — handoffs malformados detienen el chain.
- **Verification Gate del documenter.** El documenter no puede invocar `cortex_save_session` sin antes pasar por `cortex_verify_session_claims`. El resultado decide el `confidence` de cada memoria que persiste.
- **Confidence labels en búsquedas.** Los hits de `cortex search` y `cortex context` muestran `[verified]` / `[asserted]` / `[contradicted]` cuando la memoria pasó por el Gate. Memorias sin label son pre-0.5.0.
- **Status `handoff` first-class.** Si un check falla o el trabajo es parcial, la sesión se cierra con `status: handoff` (no `completed`). Eso le permite al próximo turno retomar exactamente donde quedó la anterior.
- **CONTEXT.md awareness.** Si tu repo tiene `.cortex/CONTEXT.md` (auto-creado por `setup full`), los agents lo leen antes de inventar términos. El documenter actualiza el archivo cuando un término pasa a ser canonical.

Las 4 doc-guides por IDE (`docs/guides/ide-{claude-code,opencode,pi,codex}.md`) tienen una sección "Tripartita Refinada (0.5.0)" con detalles específicos de cómo se materializa cada contrato en cada IDE.

## Paso 6 — WebGraph (opcional)

Para visualizar el grafo de conocimiento de tu proyecto:

```bash
cortex webgraph serve
```

Abrí http://127.0.0.1:8765 en el navegador. Vas a ver los nodos episódicos + semánticos + enterprise, con los arcos de referencia entre ellos.

## Flujo diario

Desde tu repo, una vez configurado:

```bash
# Desde tu IDE: el agente hace todo el flujo tripartito automáticamente.
# Desde la CLI:
cortex search "lo que necesito recordar"
cortex create-spec --title "Mi Feature" --goal "..."
# ...codear...
cortex save-session --title "Mi Feature" --spec-summary "Lo que hice"
```

## Troubleshooting

### "Cortex no está configurado en este directorio"

Significa que estás fuera del workspace o que el setup nunca corrió. Soluciones:

```bash
# Opción 1: andate al repo Cortex y corré ahí
cd /ruta/a/tu/repo
cortex search "..."

# Opción 2: pasá --project-root explícito (a partir de Ola 3 / 2026-05-13)
cortex search "..." --project-root /ruta/a/tu/repo  # disponible en algunos comandos
cortex stats --project-root /ruta/a/tu/repo
```

### `setup pipeline` se cuelga preguntando algo

A partir de Ola 3, usá `--non-interactive`:

```bash
cortex setup pipeline --non-interactive
cortex setup full --non-interactive --git-depth 50
```

### "VIOLACIÓN DE GOBERNANZA: cortex_create_spec sin cortex_sync_ticket"

El agente saltó el paso 1. **No es un bug** — Cortex fuerza el orden. Pedile al agente que ejecute `cortex_sync_ticket` primero con tu pedido inicial, luego `cortex_create_spec`. Ver `cortex/mcp/server.py:_GOVERNANCE_VIOLATION_MESSAGE`.

### `cortex doctor` reporta gitignore en FAIL

A partir de Ola 3, `cortex setup full` agrega automáticamente las rutas correctas a tu `.gitignore`. Si seguís viendo FAIL:

```bash
# Forzá la actualización:
cortex setup full --non-interactive --git-depth 0
```

(`--git-depth 0` salta el preseed para que sea rápido.)

### El IDE no detecta las herramientas `cortex_*`

```bash
# Re-inyectá:
cortex inject --ide <tu-ide>

# O arrancá el MCP server manualmente:
cortex mcp-server --project-root /ruta/a/tu/repo
```

Y revisá los logs en `.cortex/logs/mcp_calls_*.log`.

### `cortex setup full` se descarga ONNX y tarda mucho la primera vez

Esperado: la primera vez que cualquier comando hace un embedding, el modelo ONNX MiniLM se descarga (~10MB). Subsecuentes corridas son instantáneas (cacheado por chromadb).

Si estás sin red, podés saltar el preseed con `--git-depth 0`. El setup completará pero las búsquedas iniciales no van a tener contexto histórico hasta que el modelo se descargue.

## Próximos pasos

- Configurá tu equipo de gobernanza en `.cortex/org.yaml` (`governance.ci_profile`: observability / advisory / enforced).
- Activá Autopilot: `cortex autopilot install --ide claude-code && cortex autopilot start --mode assist`.
- Reuníte con tu equipo para definir qué memorias se promueven al `vault-enterprise/` con `cortex promote-knowledge`.

## Soporte

Issues: https://github.com/MachuaninEzequiel/Cortex/issues

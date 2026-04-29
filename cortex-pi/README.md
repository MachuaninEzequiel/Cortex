# Cortex Pi — Personal Intelligence configurada para Cortex Release 2.5

> **Tu Pi, clonada a la filosofía de Cortex Release 2.5.**  
> Sistema de Gobernanza para DevAgents con Memoria Híbrida RRF e Intelligent Routing.

## ¿Qué hay aquí?

Este directorio contiene la configuración completa de **Pi Coding Agent** construida específicamente para el proyecto Cortex Release 2.5. No es una instalación genérica — cada extensión, agent y skill está diseñado para seguir exactamente la filosofía de Cortex con **Intelligent Routing** y **Gobernanza Total**.

```
cortex-pi/
├── AGENTS.md                    # Governance Rules (Release 2.5)
├── extensions/
│   ├── cortex-dashboard.ts      # Dashboard principal (Premium Edition)
│   ├── cortex-memory-widget.ts  # Widget RRF en tiempo real
│   ├── cortex-spec-tracker.ts   # Tracker de criterios de aceptación
│   └── cortex-subagent-widget.ts # Background subagents management
├── .pi/
│   ├── system.md                # Global Governance Prompt
│   ├── agents/
│   │   ├── teams.yaml           # Definición de equipos (Release 2.5)
│   │   ├── agent-chain.yaml     # Pipelines secuenciales (Release 2.5)
│   │   ├── cortex-sync.md       # PRE-FLIGHT: Spec Creation Only
│   │   ├── cortex-SDDwork.md    # IMPLEMENTATION ORCHESTRATOR: Intelligent Routing
│   │   ├── cortex-code-explorer.md    # Subagente: Análisis de arquitectura
│   │   ├── cortex-code-implementer.md # Subagente: Implementación
│   │   ├── cortex-security-auditor.md # Subagente: Auditoría OWASP/Secrets
│   │   ├── cortex-test-verifier.md    # Subagente: Cobertura >85% y Tipado
│   │   └── cortex-documenter.md # Subagente: Documentación empresarial
│   ├── skills/
│   │   ├── cortex-vault.md      # Interacción con memoria híbrida
│   │   ├── cortex-python.md     # Convenciones Python del proyecto
│   │   └── cortex-testing.md    # Patrones de testing
│   ├── themes/
│   │   └── cortex-dark.json     # Tema visual de Cortex
│   ├── damage-control-rules.yaml # Reglas de seguridad Pi
│   └── settings.json            # Config Pi workspace
└── justfile                     # Task runner (just)
```

## Filosofía Cortex Release 2.5

Cortex introduce **Intelligent Routing** y **Gobernanza de 5 Capas** para garantizar la integridad del código:

### 🟢 Fast Track (Vía Rápida)
Para tareas simples (1-2 archivos): el orquestador implementa directamente y pasa a validación.

### 🔴 Deep Track (Vía Profunda)
Para tareas complejas: el orquestador delega a un equipo especializado (Explorer → Implementer → Security → Test).

### ⚠️ Excepción (Modo SDD Forzado)
Si el usuario pide explícitamente "mediante SDD", se usa obligatoriamente Deep Track.

## Instalación

### Prerrequisitos

```bash
# Pi Coding Agent
npm install -g @mariozechner/pi-coding-agent

# just (task runner)
brew install just      # macOS
# o: cargo install just

# Bun (runtime para extensiones TypeScript)
curl -fsSL https://bun.sh/install | bash
```

### Setup

```bash
# 1. Copia este directorio al root de tu proyecto Cortex
cp -r cortex-pi/* /path/to/Cortex/
cp -r cortex-pi/.pi /path/to/Cortex/

# 2. Inicia Cortex Pi
just cortex
```

## Modos de Uso

### Desarrollo normal (modo principal)
```bash
just cortex
```
Carga el **Premium Dashboard** con boot sequence + memory widget + spec tracker. Usa `/sdd <tarea>` para iniciar.

### Pipeline SDDwork completo
```bash
just sdd
```
Ciclo completo: Sync → SDDwork → Security → Test → Documenter.

### Hotfix urgente
```bash
just hotfix
```
Fast Track directo: implementación rápida con auditoría de seguridad y tests mínima.

### Auditoría de calidad
```bash
just audit
```
Revisa cobertura, deuda técnica y seguridad del código existente.

## Flujo de Trabajo (Gobernanza Total)

```
1. just cortex                    # Abre Pi con el motor de gobernanza activo
2. /sdd "Implementar feature X"   # Inicia pipeline SDDwork
   → cortex-sync: Ticket Sync → SPEC
3. cortex-SDDwork evalúa complejidad:
   - 🟢 FAST TRACK: implementa directamente
   - 🔴 DEEP TRACK: explorer → implementer
4. cortex-security-auditor: Valida secretos y OWASP
5. cortex-test-verifier: Valida cobertura >85%
6. cortex-documenter: Persiste al vault (save-session)
7. ✅ Pipeline completado
```

## Comandos Premium Disponibles

| Comando               | Descripción                                 |
| --------------------- | ------------------------------------------- |
| `/sdd <tarea>`        | Inicia el pipeline SDDwork completo         |
| `/cortex stats`       | Ver estadísticas de memoria RRF             |
| `/spec-load`          | Carga el tracker de criterios de aceptación |
| `/sub <tarea>`        | Spawnea un subagente en background          |
| `/team <nombre>`      | Activa un team de agentes                   |
| `/reset`              | Resetea el estado de gobernanza             |

## Damage Control

El sistema intercepta automáticamente operaciones peligrosas:
- 🚫 `rm -rf vault/` o `.cortex/`
- 🚫 Uso de herramientas de memoria externas (`engram`, `mem_`)
- 🚫 Secrets en código (detectados por Security Auditor)

## Teams del Agente (Release 2.5)

| Team              | Agentes                                                        | Uso                      |
| ----------------- | -------------------------------------------------------------- | ------------------------ |
| `cortex-sddwork`  | sync → SDDwork → explorer → implementer → security → test → doc | Feature completa         |
| `cortex-hotfix`   | SDDwork → security → test → doc                                | Fix urgente (Fast Track) |
| `cortex-research` | sync → doc                                                     | Investigación            |
| `cortex-audit`    | sync → explorer → security → test → doc                        | Auditoría                |

---

**Cortex Pi Release 2.5**: Tu IDE de gobernanza definitiva con Intelligent Routing, auditoría proactiva y memoria corporativa.

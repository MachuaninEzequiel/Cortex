# El Manifiesto Cortex: Enterprise Memory Productization

<div align="center">

**Cortex — Enterprise Edition**

*Calidad, Seguridad, Documentación y Memoria Corporativa como sistema de gobernanza para Organizaciones y DevAgents*


</div>

---

## ¿Por qué Cortex?

| Problema | Solución Cortex |
| --- | --- |
| Agentes olvidan contexto entre sesiones | Memoria Híbrida RRF persistente (local + enterprise) |
| Código sin documentación actualizada | `save-session` obligatorio post-tarea |
| Sin trazabilidad de decisiones arquitectónicas | Especificaciones técnicas (`create-spec`) |
| Vulnerabilidades detectadas tarde | SecuritySubAgent en tiempo real |
| Tests como afterthought | TestSubAgent integrado en flujo |
| Conocimiento aislado por proyecto | Promotion Pipeline hacia vault corporativo |
| Sin visibilidad sobre salud de memoria | `memory-report` con JSON estable |
| Configuración enterprise compleja | Setup guiado con presets por industria |
| Gobernanza CI inexistente | Perfiles `advisory` / `enforced` en CI |

---

## El Modelo de Ejecución Tripartito

La arquitectura de ejecución divide la responsabilidad en tres roles especializados:

### 1. `Cortex-sync` (El Analista / SPECsWriter)

Su misión es la **preparación**. Recupera contexto histórico del Vault y de la memoria episódica para refinar los requisitos.

- **Output**: Generación de una **Especificación Técnica (`create-spec`)** validada antes de tocar una sola línea de código.
- **Responsabilidades**:
  - Análisis de memorias previas relacionadas
  - Detección de patrones arquitectónicos existentes
  - Identificación de dependencias y riesgos
  - Refinamiento de requisitos con contexto histórico

### 2. `Cortex-SDDwork` (El Orquestador)

Coordina la implementación técnica con **Intelligent Routing**:

- **Fast Track** 🟢: Para tareas simples (1-2 archivos), implementa directamente y pasa a validación.
- **Deep Track** 🔴: Para tareas complejas, delega a un equipo especializado:
  - **CodeExplorer**: Analiza arquitectura y encuentra archivos relevantes.
  - **CodeImplementer**: Diseña y escribe el código.
  - **SecuritySubAgent**: Revisa vulnerabilidades y cumplimiento OWASP/SEC.
  - **TestSubAgent**: Asegura cobertura >80% y estabilidad.

```
Especificación → [Fast Track | Deep Track] → SecuritySubAgent → TestSubAgent → [Loop hasta aprobar]
```

### 3. `Cortex-documenter` (El Guardián)

Paso final **obligatorio**. Ninguna tarea se considera terminada sin persistir el conocimiento.

- **Output**: **Notas de Sesión (`save-session`)** estructuradas que alimentan la memoria futura.
- **Contenido generado**: Decisiones técnicas, cambios realizados, TODOs, links a issues/PRs, métricas de cobertura.

---

## Pilares Tecnológicos

### Memoria Híbrida RRF (Reciprocal Rank Fusion)

Cortex combina dos capas cognitivas con soporte multi-nivel (local + enterprise):

- **Capa Episódica**: Eventos de CI, logs y resúmenes de PRs en **ChromaDB** con embeddings ONNX.
- **Capa Semántica**: Conocimiento profundo en archivos **Markdown** (Obsidian-compatible).
- **Fusión Inteligente**: Motor de búsqueda cruzada con **RRF verdadero cross-source**, con pesos configurables por scope.

**Características técnicas:**

- ✅ Embeddings locales via ONNX Runtime (`<1ms` latency)
- ✅ Multi-backend: ONNX (default), sentence-transformers, OpenAI
- ✅ Búsqueda semántica + BM25 fallback híbrida
- ✅ True RRF: competición justa entre fuentes episódicas y semánticas
- ✅ Retrieval multi-nivel: scopes `local`, `enterprise`, `all`
- ✅ Trazabilidad de origen por hit (scope, project_id, origin_vault)

### Enterprise Memory Layer

La capa enterprise permite a las organizaciones operar memoria institucional:

- **`.cortex/org.yaml`**: Configuración organizacional declarativa con schema versionado.
- **Topologías**: `small-company`, `multi-project-team`, `regulated-organization`, `custom`.
- **Retrieval multi-nivel**: Consulta simultánea de vault local y corporativo.
- **Promotion Pipeline**: Flujo auditable de conocimiento local → institucional con estados (`candidate` → `reviewed` → `promoted`).
- **Gobernanza CI**: Perfiles de enforcement (`observability`, `advisory`, `enforced`).
- **Observabilidad**: Comando `memory-report` con salida humana y JSON estable.

### Aislamiento y Anti-Amnesia

- ❌ No usa memoria de sesión volátil
- ❌ No depende de context windows externos
- ✅ Vault local como source of truth
- ✅ Git-tracked memoria para auditoría completa
- ✅ Enterprise vault separado para conocimiento corporativo

### Eficiencia ONNX

```
Modelo:           all-MiniLM-L6-v2 (384 dimensions)
Latencia:         <1ms por embedding (CPU)
Memory footprint: ~50MB (vs ~2.5GB PyTorch)
API keys:         No requeridas
```

### Context Enricher Proactivo

- **Detección de dominio/tópico** mediante análisis semántico
- **Co-occurrence boost** basado en grafos de archivos modificados conjuntamente
- **Multi-strategy search**: topic, files, keywords, PR titles, graph expansion
- **Budget control**: max items y max chars configurables

---

## CLI Reference Completa

### Comandos Core

| Comando | Ciclo de Vida | Descripción |
| --- | --- | --- |
| `cortex setup agent` | **Cognitive** | Configura Vault, Memoria, Skills y el Servidor MCP en tu IDE. |
| `cortex setup pipeline` | **DevOps** | Configura Workflows de GitHub y scripts de auditoría. |
| `cortex setup full` | **Total** | Instalación completa (Agente + Pipeline). |
| `cortex setup webgraph` | **Visual** | Configura el módulo de visualización de grafos. |
| `cortex setup enterprise` | **Enterprise** | Setup de topología enterprise con wizard o presets. |
| `cortex init` | **Bootstrap** | Alias rápido para `cortex setup agent`. |
| `cortex create-spec` | **Pre-Work** | Define metas, requerimientos y criterios de aceptación. |
| `cortex save-session` | **Post-Work** | Persiste cambios, decisiones y TODOs en el Vault. |
| `cortex search` | **Retrieve** | Búsqueda híbrida RRF en ambas capas de memoria. |
| `cortex context` | **Enrich** | Inyecta contexto temprano basado en archivos modificados. |
| `cortex doctor` | **Operate** | Valida entorno Cortex, vault, Git y gobernanza. |
| `cortex validate-docs` | **Governance** | Valida frontmatter y estructura Markdown del vault. |
| `cortex verify-docs` | **CI** | Verifica presencia de documentación de agente en PRs. |
| `cortex index-docs` | **Index** | Indexa docs del vault como memoria semántica. |
| `cortex remember` | **Store** | Almacena memorias episódicas manualmente. |
| `cortex forget` | **Delete** | Elimina memorias por ID con confirmación. |
| `cortex stats` | **Monitor** | Muestra estadísticas del vault y memoria episódica. |
| `cortex install-skills` | **Coach** | Inyecta habilidades de Obsidian en `.cortex/skills/`. |
| `cortex mcp-server` | **Bridge** | Inicia el servidor MCP universal para IDEs. |
| `cortex agent-guidelines` | **Guide** | Muestra las guidelines de comportamiento del agente. |

### Comandos Enterprise

| Comando | Ciclo de Vida | Descripción |
| --- | --- | --- |
| `cortex org-config` | **Config** | Muestra la configuración enterprise resuelta. |
| `cortex promote-knowledge` | **Promote** | Promueve conocimiento local al vault enterprise. |
| `cortex review-knowledge` | **Review** | Aprueba o rechaza candidatos de promoción. |
| `cortex sync-enterprise-vault` | **Sync** | Valida e indexa el vault enterprise. |
| `cortex memory-report` | **Observe** | Reporte de salud de memoria y promociones. |

### Comandos Work Items

| Comando | Ciclo de Vida | Descripción |
| --- | --- | --- |
| `cortex hu import` | **Import** | Importa HU/work items externos (read-only). |
| `cortex hu list` | **List** | Lista work items importados. |
| `cortex hu show` | **Show** | Muestra una nota de work item específica. |

### Comandos PR Context (DevSecDocOps)

| Comando | Ciclo de Vida | Descripción |
| --- | --- | --- |
| `cortex pr-context capture` | **Capture** | Captura metadata de PR y guarda como JSON. |
| `cortex pr-context store` | **Store** | Almacena contexto PR en memoria episódica. |
| `cortex pr-context search` | **Search** | Busca PRs similares anteriores en memoria. |
| `cortex pr-context generate` | **Generate** | Genera documentación desde contexto PR. |
| `cortex pr-context full` | **Pipeline** | Pipeline completo: capture + store + search + generate. |

### Comandos IDE

| Comando | Ciclo de Vida | Descripción |
| --- | --- | --- |
| `cortex inject` | **Setup** | Inyecta perfiles de agente Cortex en IDEs. |
| `cortex sync-ide` | **Sync** | Regenera configuración IDE desde skills actuales. |
| `cortex install-ide` | **Install** | Instala configuración Cortex en IDEs soportados. |

### Comandos WebGraph

| Comando | Ciclo de Vida | Descripción |
| --- | --- | --- |
| `cortex webgraph serve` | **Visualize** | Inicia servidor de visualización de grafos. |
| `cortex webgraph export` | **Export** | Exporta snapshot del grafo con filtro por scope. |

---

## Guía de Instalación Completa

### Prerrequisitos

- **Python 3.10** o superior
- **Git 2.30** o superior
- **pip 22.0** o superior
- _(Opcional)_ Para LLM summarization: API key de OpenAI/Anthropic/Ollama

### Opción A: Desarrollo Local (Recomendado para contribuir)

```bash
# 1. Clonar repositorio
git clone https://github.com/MachuaninEzequiel/Cortex.git
cd Cortex

# 2. Crear entorno virtual
python -m venv .venv

# Linux / macOS:
source .venv/bin/activate

# Windows (PowerShell):
.venv\Scripts\Activate.ps1

# Windows (CMD):
.venv\Scripts\activate.bat

# 3. Instalar en modo desarrollo con dependencias de desarrollo
pip install -e ".[dev]"

# 4. Instalar pre-commit hooks (obligatorio para contribuir)
pre-commit install

# 5. Verificar que todo funciona
ruff check .        # Linting
pytest              # Tests con coverage
mypy cortex/        # Type checking

# 6. Setup inicial — elegí tu perfil
cortex setup agent        # Para desarrolladores (Vault + Skills + MCP)
cortex setup pipeline     # Para DevOps (GitHub Actions + auditoría)
cortex setup full         # Instalación completa (recomendado)
cortex setup enterprise   # Para topología enterprise corporativa
```

### Opción B: Usuario Final (pip install)

```bash
pip install cortex-memory

# Quick start
cortex setup agent

# Enterprise quick start con preset
cortex setup enterprise --preset small-company
```

### Opción C: Enterprise con Preset No-Interactivo

```bash
# Setup enterprise sin wizard interactivo
cortex setup enterprise --preset regulated-organization --non-interactive

# Setup enterprise con overrides YAML personalizados
cortex setup enterprise --preset multi-project-team --org-config ./my-org-overrides.yaml

# Dry-run para ver qué se generaría
cortex setup enterprise --preset small-company --dry-run --json
```

### Dependencias Opcionales

```bash
# Embedding backend alternativo (PyTorch ~2.5GB)
pip install cortex-memory[local]

# Integraciones LLM
pip install cortex-memory[openai]     # OpenAI GPT-4
pip install cortex-memory[anthropic]  # Claude
pip install cortex-memory[ollama]     # Local LLMs

# WebGraph UI (visualización de knowledge graphs)
pip install cortex-memory[webgraph]

# Todo junto
pip install cortex-memory[all]
```

### Verificación Post-Instalación

```bash
# Verificar que el entorno está sano
cortex doctor

# Verificar enterprise (si aplica)
cortex doctor --scope enterprise

# Ver configuración enterprise resuelta
cortex org-config

# Ver estadísticas de memoria
cortex stats

# Verificar servidor MCP
cortex mcp-server --project-root .
```

---

## Configuración por IDE

### Pi Coding Agent (RECOMENDADO)

Pi es el CLI y entorno de ejecución **recomendado** por Cortex. Ofrece una filosofía Open Source con capacidad de configuración extrema. Cortex proporciona un setup de inyección al detalle en `cortex-pi/` que convierte a Pi en un nodo de gobernanza total con:

- **Premium Dashboard**: Boot sequence, memory widget y spec tracker.
- **Intelligent Routing**: Fast Track / Deep Track automático.
- **Subagentes completos**: sync, SDDwork, explorer, implementer, security, test, documenter.
- **Task Runner**: Justfile con modos `cortex`, `sdd`, `hotfix`, `audit`.

```bash
# Instalación de Pi
npm install -g @mariozechner/pi-coding-agent
brew install just   # Task runner (macOS)
curl -fsSL https://bun.sh/install | bash  # Runtime para extensiones TS

# Iniciar Cortex Pi
just cortex
```

### Cursor

1. `Settings` → `MCP` → `Add Server`
2. Name: `cortex`, Command: `python`, Args: `-m cortex.cli.main mcp-server --project-root C:\ruta\absoluta\al\proyecto`
3. Verificar `Connected: true` en la sección MCP.

### Antigravity / Claude Desktop

```json
{
  "mcpServers": {
    "cortex": {
      "command": "python",
      "args": ["-m", "cortex.cli.main", "mcp-server", "--project-root", "/ruta/absoluta/al/proyecto"]
    }
  }
}
```

### VSCode (Cline / Roo)

Crear `.vscode/mcp.json`:
```json
{
  "servers": {
    "cortex": {
      "command": "python",
      "args": ["-m", "cortex.cli.main", "mcp-server", "--project-root", "${workspaceFolder}"]
    }
  }
}
```

### Herramientas MCP Disponibles

- **`cortex_search`**: Búsqueda híbrida en memorias (palabras clave instantánea)
- **`cortex_search_vector`**: Búsqueda semántica profunda (requiere carga de modelo ONNX)
- **`cortex_context`**: Enriquecer contexto basado en archivos modificados
- **`cortex_sync_ticket`**: Inyectar contexto histórico para preparar specs
- **`cortex_create_spec`**: Crear especificaciones técnicas
- **`cortex_save_session`**: Persistir sesiones de trabajo
- **`cortex_import_hu`**: Importar una HU/work item externo en modo read-only
- **`cortex_get_hu`**: Obtener la nota local ya importada de una HU/work item
- **`cortex_sync_vault`**: Sincronizar y re-indexar el vault

---

## Arquitectura del Sistema

```
Cortex/
├── cortex/                        # Núcleo del Sistema (AgentMemory)
│   ├── cli/                       # Interfaz Typer (Comandos CLI)
│   │   └── main.py                # 30+ comandos, subcomandos y grupos
│   ├── core.py                    # Fachada Principal (AgentMemory)
│   ├── models.py                  # Modelos Pydantic (datos compartidos)
│   ├── enterprise/                # Capa Enterprise Corporativa
│   │   ├── config.py              # Carga/validación de org.yaml
│   │   ├── models.py              # EnterpriseOrgConfig, topologías
│   │   ├── retrieval_service.py   # Retrieval multi-nivel enterprise
│   │   ├── sources.py             # Fuentes de datos enterprise
│   │   ├── knowledge_promotion.py # Pipeline de promoción auditable
│   │   ├── promotion_models.py    # Modelos de promoción Pydantic
│   │   └── reporting.py           # Observabilidad y reporting
│   ├── services/                  # Servicios de dominio inyectados
│   │   ├── spec_service.py        # Ciclo de vida de especificaciones
│   │   ├── session_service.py     # Ciclo de vida de sesiones
│   │   └── pr_service.py          # Intake de PRs y docs fallback
│   ├── pipeline/                  # Abstracciones DevSecDocOps (CI/CD)
│   ├── episodic/                  # Memoria episódica (ChromaDB + RRF)
│   ├── semantic/                  # Memoria semántica (Vault Markdown)
│   ├── retrieval/                 # Motor de búsqueda híbrida adaptativo
│   │   ├── hybrid_search.py       # Adaptive RRF con pesos dinámicos
│   │   └── intent.py              # Detección de intención de búsqueda
│   ├── embedders/                 # Factory de backends de embeddings
│   ├── context_enricher/          # Enriquecimiento proactivo de contexto
│   ├── mcp/                       # Servidor Model Context Protocol
│   ├── setup/                     # Orquestador de instalación
│   │   ├── orchestrator.py        # Modos: Agent, Pipeline, Full, Enterprise, WebGraph
│   │   ├── enterprise_wizard.py   # Wizard interactivo enterprise
│   │   ├── enterprise_presets.py  # Presets por industria
│   │   ├── templates.py           # Templates de workflows y configs
│   │   ├── cold_start.py          # Bootstrap inteligente desde git history
│   │   └── cortex_workspace.py    # Gestión de workspaces federados
│   ├── webgraph/                  # Visualización de grafos de conocimiento
│   │   ├── service.py             # Servicio core + nodos enterprise
│   │   ├── federation.py          # Federación multi-proyecto + scope filter
│   │   └── server.py              # Servidor Flask con seguridad CSRF
│   ├── workitems/                 # Integración Work Items (Jira, etc.)
│   ├── hooks/                     # Extensiones via decoradores
│   ├── ide/                       # Adaptadores IDE (Cursor, VSCode, etc.)
│   ├── skills/                    # Habilidades Obsidian embebidas
│   ├── doctor.py                  # Diagnóstico de salud (project + enterprise)
│   ├── doc_validator.py           # Validación de docs Markdown
│   ├── doc_verifier.py            # Verificación de docs en PRs
│   ├── doc_generator.py           # Generación automática de docs
│   ├── feedback_loop.py           # Loop de retroalimentación cognitiva
│   ├── memory_decay.py            # Decaimiento temporal de memorias
│   └── git_policy.py              # Políticas Git enterprise
├── cortex-pi/                     # Entorno Pi Agent (Premium Edition)
│   ├── AGENTS.md                  # Governance Rules (Release 2.5)
│   ├── extensions/                # Dashboard, widgets, trackers TS
│   ├── .pi/                       # Agentes, skills, themes, settings
│   └── justfile                   # Task runner con modos cortex/sdd/hotfix/audit
├── tests/                         # Suite de pruebas
│   ├── unit/                      # Pruebas unitarias y Hypothesis
│   ├── integration/               # Pruebas de integración MCP/CLI
│   └── e2e/                       # Pruebas de flujo completo
├── docs/enterprise/               # Documentación enterprise
│   ├── BACKLOG-*.md               # Backlog ejecutable
│   ├── PLAN-EPIC-[1-7].md         # Planes de cada épica
│   └── AVANCE-EPIC-[1-6]-*.md     # Bitácoras de implementación
├── .github/workflows/             # CI/CD Pipelines
│   ├── ci-pull-request.yml        # Gate de calidad en PRs
│   ├── ci-enterprise-governance.yml # Gobernanza enterprise
│   ├── ci-security.yml            # Auditoría de seguridad
│   └── ci-release.yml             # Pipeline de releases
├── vault/                         # Knowledge base (Obsidian compatible)
├── .cortex/                       # Config de skills y local-memory
├── pyproject.toml                 # Empaquetado y dependencias
├── config.yaml                    # Configuración runtime local
└── README.md                      # Documentación principal
```

---

## Configuración Avanzada

### config.yaml (Runtime Local)

```yaml
episodic:
  persist_dir: .memory/chroma
  collection_name: cortex_episodic
  embedding_model: all-MiniLM-L6-v2
  embedding_backend: onnx         # onnx | local | openai
  namespace_mode: project          # project | branch | custom

semantic:
  vault_path: vault

retrieval:
  top_k: 5
  episodic_weight: 1.0
  semantic_weight: 1.0

context_enricher:
  min_score: 0.1
  domain_confidence: 0.5
  max_items: 8
  max_chars: 2000
  strategies:
    topic: true
    files: true
    keywords: true
    pr_title: true
    graph_expansion: true

llm:
  provider: none                   # none | openai | anthropic | ollama
  model: ""

pipeline:
  abort_early: true
  stages:
    security:
      enabled: true
      block_on_failure: true
    lint:
      enabled: true
      block_on_failure: true
    test:
      enabled: true
      block_on_failure: true
      min_coverage: 0
    documentation:
      enabled: true
      block_on_failure: false

integrations:
  jira:
    enabled: false
    base_url: ""
    email_env: JIRA_EMAIL
    token_env: JIRA_API_TOKEN
```

### .cortex/org.yaml (Enterprise)

```yaml
schema_version: 1
organization:
  name: "Mi Empresa"
  slug: "mi-empresa"
  profile: "multi-project-team"    # small-company | multi-project-team | regulated-organization | custom

memory:
  mode: layered
  enterprise_vault_path: vault-enterprise
  enterprise_memory_path: .memory/enterprise/chroma
  enterprise_semantic_enabled: true
  enterprise_episodic_enabled: false
  project_memory_mode: isolated
  branch_isolation_enabled: false
  retrieval_default_scope: all     # local | enterprise | all
  retrieval_local_weight: 1.0
  retrieval_enterprise_weight: 1.2

promotion:
  enabled: true
  allowed_doc_types: [spec, decision, runbook, hu, incident]
  require_review: true
  default_targets: [enterprise_vault]

governance:
  git_policy: balanced             # balanced | strict | custom
  ci_profile: advisory             # observability | advisory | enforced
  version_sessions_in_git: false

integration:
  github_actions_enabled: true
  webgraph_workspace_enabled: true
  ide_profiles: []
```

---

## Testing y Calidad

- **Coverage objetivo**: >85%
- **Linting**: Ruff (velocidad extrema)
- **Type checking**: Mypy (seguridad tipado)
- **Pre-commit hooks**: Automáticos en dev mode
- **CI/CD**: GitHub Actions con pipeline DevSecDocOps + Enterprise Governance
- **Property-Based Testing**: Hypothesis para algoritmos complejos (RRF)

```bash
ruff check .                                    # Linting estático
ruff format .                                   # Formateo automático
pytest --cov=cortex --cov-report=term-missing   # Tests con coverage
mypy cortex/                                    # Type checking
cortex doctor --scope all                       # Diagnóstico completo
cortex memory-report --json                     # Reporte de salud enterprise
```

---

## Enterprise Memory Productization — Resumen de Épicas

| Epic | Estado | Descripción |
| --- | --- | --- |
| E1 - Modelo Organizacional | ✅ Completado | Topología formal declarativa (`.cortex/org.yaml`) |
| E2 - Retrieval Multi-nivel | ✅ Completado | Consulta local + enterprise con trazabilidad |
| E3 - Promotion Pipeline | ✅ Completado | Promoción auditable de conocimiento |
| E4 - Gobernanza y CI | ✅ Completado | Políticas automáticas de memoria en CI |
| E5 - Setup Enterprise | ✅ Completado | Instalación guiada con wizard y presets |
| E6 - Observabilidad | ✅ Completado | Salud de memoria, promotion reporting, WebGraph |
| E7 - Presets, Docs, Hardening | ✅ Completado | Documentación final, adopción, cierre |

---

<div align="center">

**Cortex: La memoria dejó de ser el pasado. Ahora es infraestructura corporativa.**

</div>

<div align="center">
  <br />
    <a href="https://github.com/MachuaninEzequiel/Cortex" target="_blank">
      <img src="assets/logo.png" alt="Cortex Logo" width="500">
    </a>
  <br />

  <h1>CORTEX  — Enterprise Edition</h1>

  <p>
    <strong>Calidad, Seguridad, Documentación y Memoria Corporativa como sistema de gobernanza para Organizaciones y DevAgents</strong>
  </p>

  <p>
    <a href="https://github.com/MachuaninEzequiel/Cortex"><img src="https://img.shields.io/badge/Release-3.0.0--Enterprise-blueviolet.svg" alt="Release 3.0.0" /></a>
    <a href="https://github.com/MachuaninEzequiel/Cortex"><img src="https://img.shields.io/badge/Architecture-Hybrid--Enterprise--Memory-orange.svg" alt="Architecture" /></a>
    <a href="https://github.com/MachuaninEzequiel/Cortex"><img src="https://img.shields.io/badge/Coverage->85%25-brightgreen.svg" alt="Coverage" /></a>
    <a href="https://github.com/MachuaninEzequiel/Cortex"><img src="https://img.shields.io/badge/Python-3.10+-blue.svg" alt="Python 3.10+" /></a>
    <a href="https://github.com/MachuaninEzequiel/Cortex"><img src="https://img.shields.io/badge/CI%2FCD-DevSecDocOps-red.svg" alt="CI/CD" /></a>
    <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT" /></a>
  </p>

</div>

---

## El Manifiesto Cortex: Gobernanza Total + Memoria Corporativa

En la era de los agentes de IA, la **Amnesia de Sesión** es el mayor enemigo de la productividad. Los agentes convencionales inician cada tarea en blanco, ignorando las decisiones arquitectónicas pasadas, las vulnerabilidades detectadas y el contexto histórico de tu negocio.

**Cortex redefine la relación humano-agente.** No es solo una base de conocimientos; es un **Sistema de Gobernanza** que obliga a la IA a seguir un ciclo de vida disciplinado de ingeniería de software. Con la v3.0, Cortex escala esta gobernanza al nivel **corporativo**: memoria institucional, promoción auditable de conocimiento, retrieval multi-nivel y observabilidad operativa, todo gobernado por una topología declarativa (`org.yaml`).

>  Para un documento exhaustivo del estado completo de Cortex Enterprise, consultá el [Manifiesto Cortex Enterprise](docs/enterprise/MANIFIESTO-CORTEX-ENTERPRISE.md).

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

---

## El Modelo de Ejecución Tripartito

### 1. `Cortex-sync` (El Analista / SPECsWriter)

Recupera contexto histórico del Vault y de la memoria episódica para refinar los requisitos.

- **Output**: Especificación Técnica (`create-spec`) validada antes de tocar código.
- Análisis de memorias previas, detección de patrones, identificación de riesgos.

### 2. `Cortex-SDDwork` (El Orquestador)

Coordina la implementación con **Intelligent Routing**:

- **Fast Track** 🟢: Tareas simples (1-2 archivos) → implementación directa + validación.
- **Deep Track** 🔴: Tareas complejas → Explorer → Implementer → Security → Test.

```
Especificación → [Fast Track | Deep Track] → SecuritySubAgent → TestSubAgent → [Loop]
```

### 3. `Cortex-documenter` (El Guardián)

Paso final **obligatorio**. Persiste decisiones, cambios, TODOs y métricas en el Vault via `save-session`.

---

## Pilares Tecnológicos

### Memoria Híbrida RRF + Enterprise

- **Capa Episódica**: ChromaDB con embeddings ONNX (`<1ms` latency).
- **Capa Semántica**: Vault Markdown (Obsidian-compatible).
- **Capa Enterprise**: Vault corporativo con retrieval multi-nivel y scopes `local`/`enterprise`/`all`.
- **Fusión**: True RRF cross-source con pesos configurables por scope.

### Enterprise Memory Layer

- **`.cortex/org.yaml`**: Topología declarativa con schema versionado.
- **Presets**: `small-company`, `multi-project-team`, `regulated-organization`, `custom`.
- **Promotion Pipeline**: `candidate` → `reviewed` → `promoted` con trazabilidad completa.
- **Gobernanza CI**: Perfiles `observability` / `advisory` / `enforced`.
- **Observabilidad**: `cortex memory-report` con salida humana y JSON.

### Eficiencia ONNX

```
Modelo:           all-MiniLM-L6-v2 (384 dimensions)
Latencia:         <1ms por embedding (CPU)
Memory footprint: ~50MB (vs ~2.5GB PyTorch)
API keys:         No requeridas
```

### Context Enricher Proactivo

Detección de dominio, co-occurrence boost, multi-strategy search con budget control.

---

## CLI Reference

### Comandos Core

| Comando | Descripción |
| --- | --- |
| `cortex setup agent` | Configura Vault, Memoria, Skills y MCP. |
| `cortex setup pipeline` | Configura GitHub Actions y auditoría. |
| `cortex setup full` | Instalación completa (Agent + Pipeline). |
| `cortex setup webgraph` | Configura visualización de grafos. |
| `cortex setup enterprise` | Setup enterprise con wizard o presets. |
| `cortex init` | Alias rápido para `setup agent`. |
| `cortex create-spec` | Define metas y criterios de aceptación. |
| `cortex save-session` | Persiste cambios y decisiones en el Vault. |
| `cortex search` | Búsqueda híbrida RRF (`--scope local\|enterprise\|all`). |
| `cortex context` | Inyecta contexto basado en archivos modificados. |
| `cortex doctor` | Valida entorno (`--scope project\|enterprise\|all`). |
| `cortex validate-docs` | Valida frontmatter y estructura Markdown. |
| `cortex verify-docs` | Verifica documentación de agente en PRs. |
| `cortex index-docs` | Indexa docs del vault como memoria semántica. |
| `cortex remember` | Almacena memorias episódicas (`--summarize`). |
| `cortex forget` | Elimina memorias por ID. |
| `cortex stats` | Estadísticas del vault y memoria. |
| `cortex install-skills` | Inyecta habilidades Obsidian. |
| `cortex mcp-server` | Inicia servidor MCP para IDEs. |
| `cortex agent-guidelines` | Muestra guidelines del agente. |

### Comandos Enterprise

| Comando | Descripción |
| --- | --- |
| `cortex org-config` | Muestra configuración enterprise resuelta (`--json`). |
| `cortex promote-knowledge` | Promueve conocimiento al vault enterprise (`--dry-run\|--apply`). |
| `cortex review-knowledge` | Aprueba/rechaza candidatos de promoción (`--approve\|--reject`). |
| `cortex sync-enterprise-vault` | Valida e indexa el vault enterprise. |
| `cortex memory-report` | Reporte de salud y promociones (`--scope`, `--json`). |

### Comandos Adicionales

| Comando | Descripción |
| --- | --- |
| `cortex hu import/list/show` | Gestión de Work Items (Jira read-only). |
| `cortex pr-context capture/store/search/generate/full` | Pipeline DevSecDocOps de PRs. |
| `cortex inject` / `cortex sync-ide` | Configuración de IDEs. |
| `cortex webgraph serve/export` | Visualización de grafos de conocimiento. |



---

## Integración Universal (MCP Server)

> Cortex expone sus capacidades via **Model Context Protocol (MCP)**.

## Configuración por IDE

### Pi Coding Agent  (RECOMENDADO)

Pi es el entorno de ejecución **recomendado** por Cortex. Ofrece Intelligent Routing, Gobernanza de 5 Capas y un Premium Dashboard dedicado. Cortex proporciona un setup completo en `cortex-pi/` con agentes, skills, extensiones TypeScript y un task runner integrado.

```bash
# Prerrequisitos
npm install -g @mariozechner/pi-coding-agent
brew install just      # Task runner

# Iniciar
just cortex            # Dashboard principal
just sdd               # Pipeline SDDwork completo
just hotfix            # Fast Track directo
just audit             # Auditoría de calidad
```

**Teams disponibles:**

| Team | Uso |
| --- | --- |
| `cortex-sddwork` | Feature completa (sync → SDDwork → security → test → doc) |
| `cortex-hotfix` | Fix urgente (Fast Track) |
| `cortex-research` | Investigación |
| `cortex-audit` | Auditoría de código |

---

### Cursor

`Settings` → `MCP` → `Add Server`: Name=`cortex`, Command=`python`, Args=`-m cortex.cli.main mcp-server --project-root C:\ruta\al\proyecto`

#### Antigravity / Claude Desktop

```json
{
  "mcpServers": {
    "cortex": {
      "command": "python",
      "args": ["-m", "cortex.cli.main", "mcp-server", "--project-root", "/ruta/al/proyecto"]
    }
  }
}
```

---

### VSCode (Cline / Roo)

`.vscode/mcp.json`:
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

---

### Herramientas MCP disponibles

`cortex_search`, `cortex_search_vector`, `cortex_context`, `cortex_sync_ticket`, `cortex_create_spec`, `cortex_save_session`, `cortex_import_hu`, `cortex_get_hu`, `cortex_sync_vault`.

---

## Instalación — Guía para Nuevos Usuarios

Esta guía te lleva desde cero hasta tener Cortex funcionando en tu máquina. No necesitás experiencia previa con el proyecto.

### Paso 0: Prerrequisitos

Antes de empezar, asegurate de tener instalado:

- **Python 3.10 o superior** — [Descargar Python](https://www.python.org/downloads/)
- **Git** — [Descargar Git](https://git-scm.com/downloads)

> **Tip**: Para verificar que los tenés, abrí una terminal y corré `python --version` y `git --version`. Si aparecen versiones, estás listo.

---

### Paso 1: Obtener el código fuente de Cortex

Primero, descargá el código de Cortex en algún lugar de tu equipo. Esto solo se hace una vez.

```bash
# Elegí dónde guardar el código base (ejemplo: tu carpeta personal)
cd ~

# Clonar el repositorio
git clone https://github.com/MachuaninEzequiel/Cortex.git C:\Cortex
```

---

### Paso 2: Preparar TU proyecto

Cortex está diseñado para instalarse como una herramienta dentro del entorno virtual de **tu propio proyecto**. 

```bash
# 1. Navegá a la carpeta de TU proyecto (donde vas a desarrollar)
cd D:\MiProyecto

# 2. Creá un entorno virtual específico para tu proyecto
python -m venv .venv
```

---

### Paso 3: Activar el entorno virtual

**Cada vez** que abras una terminal nueva para trabajar en tu proyecto, tenés que activar su entorno:

**Windows (PowerShell):**
```powershell
.venv\Scripts\Activate.ps1
```

**Windows (CMD):**
```cmd
.venv\Scripts\activate.bat
```

**Linux / macOS:**
```bash
source .venv/bin/activate
```

> Sabés que está activado cuando ves `(.venv)` al inicio de la línea de tu terminal.

---

### Paso 4: Instalar Cortex en tu proyecto

Con el entorno de tu proyecto activado, instalá Cortex apuntando a la carpeta donde lo clonaste (Paso 1):

```bash
pip install -e C:\Cortex
```

*(Si usás dependencias extra, podés usar `pip install -e "C:\Cortex[all]"`).*

A partir de ahora, el comando `cortex` está disponible exclusivamente cuando tenés este `.venv` activado, manteniendo tu sistema limpio.

---

### Paso 5: Inicializar Cortex

Ahora que la herramienta está instalada en el entorno, inicializá la memoria en tu proyecto:

```bash
cortex setup agent
```

Esto crea en tu proyecto:
- `config.yaml` — Configuración de Cortex
- `vault/` — Tu base de conocimiento (archivos Markdown)
- `.cortex/skills/` — Habilidades de escritura de documentación
- `.memory/` — Base de datos de memoria episódica (ChromaDB)

**A partir de acá, todos los comandos se corren desde la carpeta de tu proyecto:**

```bash
# Crear una especificación técnica antes de codear
cortex create-spec --title "Auth JWT" --goal "Implementar refresh tokens"

# Guardar una sesión de trabajo al terminar
cortex save-session --title "JWT Auth" --spec-summary "Refresh tokens implementados"

# Buscar en tu memoria (episódica + semántica)
cortex search "error handling en middleware"

# Verificar que todo esté sano
cortex doctor

# Ver estadísticas de tu memoria
cortex stats
```

---

### Paso 6: Conectar Cortex con tu IDE (Opcional)

Si usás un IDE con soporte MCP (Cursor, VSCode con Cline, Claude Desktop, Pi), Cortex puede funcionar como un servidor de herramientas para tu agente de IA:

```bash
# Desde la carpeta de tu proyecto:
cortex inject --ide cursor        # Para Cursor
cortex inject --ide claude-code   # Para Claude Desktop
cortex inject                     # Menú interactivo para elegir IDE
```

O podés iniciar el servidor MCP manualmente:

```bash
cortex mcp-server --project-root D:\MiProyecto
```

---

### Resumen del flujo diario

```bash
# 1. Abrir terminal
# 2. Activar entorno (una vez por sesión de terminal)
cd ~/Cortex && .venv\Scripts\Activate.ps1   # Windows
cd ~/Cortex && source .venv/bin/activate     # Linux/Mac

# 3. Ir a tu proyecto
cd D:\MiProyecto

# 4. Trabajar con Cortex
cortex search "lo que necesito recordar"
cortex create-spec --title "Mi Feature"
# ... codear ...
cortex save-session --title "Mi Feature" --spec-summary "Lo que hice"
```

---

### ¿Querés contribuir al desarrollo de Cortex?

Si querés contribuir con código al proyecto, necesitás instalar las dependencias de desarrollo y los hooks de pre-commit. Lee la guía completa en [CONTRIBUTING.md](CONTRIBUTING.md).

### Enterprise

Para configurar Cortex en modo corporativo con topologías organizacionales, consultá la sección Enterprise del [Manifiesto Cortex](docs/enterprise/MANIFIESTO-CORTEX-ENTERPRISE.md#guía-de-instalación-completa).

---

## Integración Jira (read-only)

```yaml
# En config.yaml
integrations:
  jira:
    enabled: true
    base_url: "https://TU-DOMINIO.atlassian.net"
    email_env: JIRA_EMAIL
    token_env: JIRA_API_TOKEN
```

```bash
cortex hu import PROJ-123
cortex hu list
cortex hu show PROJ-123
```

---

## 📁 Estructura del Proyecto

```
Cortex/
├── cortex/                    # Núcleo del Sistema (AgentMemory)
│   ├── cli/                   # Interfaz Typer (30+ comandos)
│   ├── core.py                # Fachada Principal (Inyección de Servicios)
│   ├── enterprise/            # Capa Enterprise Corporativa (org.yaml, promotion, reporting)
│   ├── services/              # Lógica de negocio (spec, session, pr)
│   ├── pipeline/              # Abstracciones DevSecDocOps (CI/CD Gates)
│   ├── episodic/              # Memoria episódica (ChromaDB + RRF)
│   ├── semantic/              # Memoria semántica (Vault Markdown)
│   ├── retrieval/             # Motor de búsqueda híbrida adaptativo
│   ├── embedders/             # Factory de backends (ONNX, local, openai)
│   ├── context_enricher/      # Enriquecimiento proactivo de contexto
│   ├── mcp/                   # Servidor Model Context Protocol
│   ├── setup/                 # Orquestador (Agent/Pipeline/Full/Enterprise/WebGraph)
│   ├── webgraph/              # Visualización de grafos + nodos enterprise
│   ├── workitems/             # Integración Work Items (Jira)
│   └── ide/                   # Adaptadores IDE (Cursor, VSCode, Claude, Pi)
├── cortex-pi/                 # Entorno Pi Agent (Premium Edition)
├── tests/                     # Suite (unit/, integration/, e2e/)
├── docs/enterprise/           # Documentación Enterprise (Plans, Avances, Backlog)
├── .github/workflows/         # CI/CD Pipelines (PR, Enterprise, Security, Release)
├── vault/                     # Knowledge base (Obsidian compatible)
├── .cortex/                   # Skills, org.yaml, local-memory
└── pyproject.toml             # Configuración de empaquetado
```

---

## Testing y Calidad

```bash
ruff check .          # Linting estático
ruff format .         # Formateo automático
pytest --cov=cortex   # Tests con coverage
mypy cortex/          # Type checking
```

Coverage objetivo: >85%. Suite dividida en `unit/`, `integration/`, `e2e/`. Property-Based Testing con Hypothesis.

---

## 🤝 Contribuir

¡Las contribuciones son bienvenidas! Lee [CONTRIBUTING.md](CONTRIBUTING.md) para setup, estándares y guía de PRs.

---

## 📄 Licencia

MIT — ver [LICENSE](LICENSE).

## 👥 Autor

**MachuaninEzequiel** — [@MachuaninEzequiel](https://github.com/MachuaninEzequiel)

## Agradecimientos

- **ChromaDB** por el excelente vector database
- **ONNX Runtime** por hacer embeddings lightning-fast
- **Obsidian** por inspirar el formato de vault
- Todos los contribuyentes early-adopters de Cortex

---

<div align="center">
  <p>¿Problemas? ¿Ideas? ¡<a href="https://github.com/MachuaninEzequiel/Cortex/issues">Abre un issue</a>!</p>
  <p><strong>Cortex: La memoria dejó de ser el pasado. Ahora es infraestructura corporativa.</strong></p>
</div>

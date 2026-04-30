# Plan: Cortex Tutor & Hint — Sistema de Adopción Offline

## Metadata

- **Rama**: `feat/additional-service-integrations`
- **Dependencias**: Ninguna nueva (usa `rich` via Typer, `pathlib`, `pydantic`)
- **Tokens consumidos**: Cero. Todo es offline y estático.
- **Épica padre**: Post-Productización — Adopción y Onboarding

---

## 1. Visión General

Dos comandos complementarios que atacan momentos distintos del ciclo de adopción:

| Comando | Momento | Propósito |
| --- | --- | --- |
| `cortex tutor` | **Aprendizaje** — "¿Cómo funciona X?" | TUI interactivo navegable con resúmenes concisos por tópico |
| `cortex hint` | **Acción** — "¿Qué debería hacer ahora?" | Tip contextual basado en el estado actual del proyecto |

**Principio de diseño**: La terminal muestra un **super-resumen** (máximo 20-25 líneas por sección). Para profundizar, cada sección incluye un link `📖 Guía completa: docs/guides/<archivo>.md`.

---

## 2. Arquitectura

### 2.1 Estructura de archivos

```
cortex/
├── cli/
│   └── main.py                      # Registrar comandos tutor y hint
├── tutor/                           # Nuevo módulo
│   ├── __init__.py                  # Exports
│   ├── engine.py                    # TUI engine (menú, navegación, render)
│   ├── hint.py                      # Lógica de detección de estado + tips
│   └── topics/                      # Contenido de cada tópico del tutor
│       ├── __init__.py              # Registry de tópicos
│       ├── getting_started.py       # Primeros pasos
│       ├── commands.py              # Cheatsheet de comandos
│       ├── workflow.py              # Modelo tripartito
│       ├── pipeline.py              # CI/CD gates y módulos custom
│       ├── vault.py                 # Estructura del vault
│       ├── enterprise.py            # Enterprise memory model
│       └── ide_integration.py       # Configuración de IDEs / MCP
docs/
└── guides/                          # Documentación completa (lectura en GitHub)
    ├── getting-started.md           # Guía expandida de primeros pasos
    ├── pipeline-setup.md            # Pipeline CI/CD completo
    ├── pipeline-custom-modules.md   # Cómo intercambiar módulos
    ├── vault-structure.md           # Anatomía del vault
    ├── enterprise-vault.md          # Modelo enterprise local vs corporativo
    └── configuration-reference.md   # Referencia config.yaml + org.yaml
```

### 2.2 Flujo de datos

```
┌──────────────┐     render()     ┌────────────────────┐
│ topics/*.py  │ ──────────────→ │  rich.Console      │
│ (resúmenes)  │                  │  (terminal output)  │
└──────────────┘                  └────────────────────┘
                                         │
                                    link: 📖
                                         │
                                         ▼
                                  ┌────────────────────┐
                                  │  docs/guides/*.md  │
                                  │  (lectura completa) │
                                  └────────────────────┘
```

**Decisión clave**: Los tópicos del tutor NO son los markdown files directamente. Son funciones Python que usan `rich` para renderizar paneles, tablas y código con formato optimizado para terminal. Los `docs/guides/*.md` son documentación extendida para leer en GitHub/editor.

**Razón**: Renderizar markdown genérico en terminal nunca queda bien. Controlando el output con `rich` podemos hacer paneles compactos, tablas alineadas y colores que se ven perfectos en cualquier terminal.

---

## 3. Implementación por Fases

### Fase 1: Infraestructura del Tutor (engine + CLI)

**Archivos**: `cortex/tutor/__init__.py`, `cortex/tutor/engine.py`, `cortex/cli/main.py`

#### 3.1.1 TUI Engine (`engine.py`)

Motor minimalista de navegación:

```python
class TutorEngine:
    """Motor de navegación del tutor interactivo."""

    def __init__(self, console: Console):
        self.console = console
        self.topics: list[TutorTopic] = []

    def register(self, topic: TutorTopic) -> None:
        """Registrar un tópico navegable."""
        self.topics.append(topic)

    def show_menu(self) -> None:
        """Mostrar menú principal con panel rich."""
        # Panel con tabla de tópicos numerados
        # Prompt: "Elegí un tema (1-N) o 'q' para salir"

    def show_topic(self, index: int) -> None:
        """Renderizar un tópico específico."""
        topic = self.topics[index]
        topic.render(self.console)
        # Prompt: "[Enter] Volver al menú | [q] Salir"

    def run(self) -> None:
        """Loop principal del TUI."""
        while True:
            self.show_menu()
            choice = input()
            if choice == 'q':
                break
            # Validar y mostrar tópico
```

#### 3.1.2 Contrato de Tópico

```python
from dataclasses import dataclass
from typing import Protocol
from rich.console import Console

class TutorTopic(Protocol):
    """Contrato que cada tópico del tutor debe cumplir."""
    
    @property
    def title(self) -> str: ...
    
    @property
    def icon(self) -> str: ...
    
    @property
    def one_liner(self) -> str: ...
    
    @property
    def guide_path(self) -> str | None: ...
    
    def render(self, console: Console) -> None: ...
```

#### 3.1.3 Registro en CLI (`main.py`)

```python
@app.command()
def tutor(
    topic: str | None = typer.Argument(
        None,
        help="Tópico directo (ej: 'pipeline', 'vault', 'commands'). Sin argumento abre el menú.",
    ),
) -> None:
    """Guía interactiva offline de Cortex. Zero tokens."""
    from cortex.tutor.engine import TutorEngine
    engine = TutorEngine.default()
    
    if topic:
        engine.show_topic_by_name(topic)
    else:
        engine.run()
```

---

### Fase 2: Tópicos del Tutor (contenido)

Cada tópico es un módulo Python con una clase que implementa `TutorTopic`.

#### 3.2.1 Tópico: Primeros Pasos (`getting_started.py`)

Resumen en terminal (max 20 líneas):

```
┌─────────────────────────────────────────────────────┐
│  🚀 PRIMEROS PASOS                                  │
├─────────────────────────────────────────────────────┤
│                                                      │
│  1. Activar entorno:  source .venv/bin/activate      │
│  2. Ir a tu proyecto: cd /mi/proyecto                │
│  3. Inicializar:      cortex setup agent             │
│  4. Crear spec:       cortex create-spec --title ... │
│  5. Trabajar y guardar: cortex save-session ...      │
│  6. Buscar contexto:  cortex search "mi query"       │
│                                                      │
│  📖 Guía completa: docs/guides/getting-started.md    │
└─────────────────────────────────────────────────────┘
```

#### 3.2.2 Tópico: Comandos (`commands.py`)

Cheatsheet en formato tabla `rich`:

```
┌───────────────────────────────────────────────────────────────┐
│  📋 COMANDOS ESENCIALES                                      │
├──────────────────────┬────────────────────────────────────────┤
│ Comando              │ Para qué sirve                         │
├──────────────────────┼────────────────────────────────────────┤
│ cortex setup agent   │ Inicializar Cortex en tu proyecto      │
│ cortex create-spec   │ Crear especificación antes de codear   │
│ cortex save-session  │ Guardar sesión de trabajo              │
│ cortex search        │ Buscar en tu memoria                   │
│ cortex context       │ Inyectar contexto por archivos         │
│ cortex doctor        │ Verificar salud del proyecto           │
│ cortex stats         │ Ver estadísticas de memoria            │
│ cortex tutor         │ Esta guía que estás viendo ahora       │
│ cortex hint          │ Tip contextual: qué hacer ahora        │
├──────────────────────┴────────────────────────────────────────┤
│ Más comandos: cortex --help | Enterprise: cortex tutor enter  │
└───────────────────────────────────────────────────────────────┘
```

#### 3.2.3 Tópico: Workflow Tripartito (`workflow.py`)

```
┌─────────────────────────────────────────────────────────────┐
│  🔄 FLUJO DE TRABAJO — Modelo Tripartito                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  FASE 1 → cortex-sync (El Analista)                         │
│    Recupera contexto histórico y crea una spec.              │
│    Comando: cortex create-spec                               │
│                                                              │
│  FASE 2 → cortex-SDDwork (El Orquestador)                   │
│    Implementa con Fast Track (simple) o Deep Track (complejo)│
│    Fast Track: edita directo. Deep Track: delega a subagentes│
│                                                              │
│  FASE 3 → cortex-documenter (El Guardián)                   │
│    Persiste lo que se hizo en el vault.                      │
│    Comando: cortex save-session                              │
│                                                              │
│  📖 Detalle completo: docs/enterprise/MANIFIESTO-CORTEX...  │
└─────────────────────────────────────────────────────────────┘
```

#### 3.2.4 Tópico: Pipeline CI/CD (`pipeline.py`)

```
┌─────────────────────────────────────────────────────────────┐
│  🔧 PIPELINE CI/CD — DevSecDocOps                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Cortex ejecuta 4 stages en orden:                          │
│    Security → Lint → Test → Documentation                   │
│                                                              │
│  Cada stage se configura en config.yaml:                    │
│    pipeline.stages.security.enabled: true/false             │
│    pipeline.stages.security.block_on_failure: true/false    │
│                                                              │
│  Módulos intercambiables:                                   │
│    Security: npm audit (default) o tu propio script         │
│    Lint: ruff (default) o eslint, pylint, etc.              │
│    Test: pytest (default) o jest, vitest, etc.              │
│                                                              │
│  📖 Setup completo: docs/guides/pipeline-setup.md           │
│  📖 Módulos custom: docs/guides/pipeline-custom-modules.md  │
└─────────────────────────────────────────────────────────────┘
```

#### 3.2.5 Tópico: Vault (`vault.py`)

```
┌─────────────────────────────────────────────────────────────┐
│  📁 VAULT — Tu Base de Conocimiento                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  vault/                                                      │
│  ├── specs/        → Especificaciones técnicas              │
│  ├── sessions/     → Notas de sesiones de trabajo           │
│  ├── decisions/    → Registro de decisiones arquitectónicas │
│  ├── runbooks/     → Guías operativas                       │
│  └── hu/           → Work items importados (Jira, etc.)     │
│                                                              │
│  ¿Qué va a Git/Master?                                     │
│    ✅ Todo el vault/ (es tu knowledge base versionada)      │
│    ✅ config.yaml (configuración del proyecto)              │
│    ✅ .cortex/org.yaml (si usás enterprise)                 │
│    ❌ .memory/ (base de datos local, en .gitignore)         │
│                                                              │
│  📖 Estructura detallada: docs/guides/vault-structure.md    │
│  📖 Modelo Enterprise: docs/guides/enterprise-vault.md      │
└─────────────────────────────────────────────────────────────┘
```

#### 3.2.6 Tópico: Enterprise Memory (`enterprise.py`)

```
┌─────────────────────────────────────────────────────────────┐
│  🏢 ENTERPRISE MEMORY — Memoria Corporativa                │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Modelo de 2 niveles:                                       │
│    vault/             → Conocimiento LOCAL del proyecto     │
│    vault-enterprise/  → Conocimiento CORPORATIVO compartido │
│                                                              │
│  Flujo de promoción:                                        │
│    Local spec → candidate → review → promote → enterprise  │
│                                                              │
│  Comandos clave:                                            │
│    cortex setup enterprise   → Configurar topología         │
│    cortex promote-knowledge  → Promover docs (--dry-run)    │
│    cortex review-knowledge   → Aprobar/rechazar candidatos  │
│    cortex memory-report      → Ver salud de memoria         │
│                                                              │
│  📖 Guía enterprise: docs/guides/enterprise-vault.md        │
└─────────────────────────────────────────────────────────────┘
```

#### 3.2.7 Tópico: Integración IDE (`ide_integration.py`)

```
┌─────────────────────────────────────────────────────────────┐
│  🔌 INTEGRACIÓN IDE — Model Context Protocol                │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Cortex se conecta a tu IDE via MCP Server.                 │
│  IDEs soportados: Pi ⭐, Cursor, VSCode, Claude, Windsurf  │
│                                                              │
│  Setup rápido:                                              │
│    cortex inject --ide cursor        # Cursor               │
│    cortex inject --ide claude-code   # Claude Code          │
│    cortex inject                     # Menú interactivo     │
│                                                              │
│  El inject hace merge seguro (no sobreescribe tu config).   │
│                                                              │
│  📖 Configuración detallada: ver README.md sección MCP     │
└─────────────────────────────────────────────────────────────┘
```

---

### Fase 3: Sistema Hint Contextual (`hint.py`)

#### 3.3.1 Detección de Estado

El hint inspecciona el proyecto actual (cwd) y genera tips basados en lo que encuentra o falta:

```python
@dataclass
class ProjectState:
    """Estado detectado del proyecto actual."""
    has_config: bool              # ¿Existe config.yaml?
    has_vault: bool               # ¿Existe vault/?
    has_cortex_dir: bool          # ¿Existe .cortex/?
    has_org_yaml: bool            # ¿Existe .cortex/org.yaml?
    has_memory: bool              # ¿Existe .memory/?
    has_specs: bool               # ¿Hay specs en vault/specs/?
    has_sessions: bool            # ¿Hay sesiones en vault/sessions/?
    has_enterprise_vault: bool    # ¿Existe vault-enterprise/?
    spec_count: int               # Cantidad de specs
    session_count: int            # Cantidad de sesiones
    memory_file_count: int        # Archivos en .memory/
    vault_doc_count: int          # Total docs en vault/
    has_github_workflows: bool    # ¿Existe .github/workflows/?
    has_mcp_config: bool          # ¿Existe algún mcp.json / .mcp.json?

    @classmethod
    def detect(cls, project_root: Path) -> "ProjectState":
        """Detectar estado del proyecto actual."""
        # ... inspección de filesystem ...
```

#### 3.3.2 Motor de Tips

```python
class HintEngine:
    """Genera tips contextuales basados en el estado del proyecto."""
    
    def get_hint(self, state: ProjectState) -> Hint:
        """Retorna el tip más relevante para el estado actual."""
        
        # Prioridad de tips (de más urgente a menos):
        hints = [
            # Nivel 0: No inicializado
            (not state.has_config, Hint(
                icon="🚀",
                title="Cortex no está inicializado en este proyecto",
                body="Corré 'cortex setup agent' para empezar.",
                command="cortex setup agent",
            )),
            
            # Nivel 1: Inicializado pero sin uso
            (state.has_config and not state.has_specs, Hint(
                icon="📝",
                title="No hay especificaciones creadas",
                body="Antes de codear, creá una spec para documentar qué vas a hacer.",
                command="cortex create-spec --title \"Mi Feature\" --goal \"...\"",
            )),
            
            # Nivel 2: Tiene specs pero no sesiones
            (state.has_specs and not state.has_sessions, Hint(
                icon="💾",
                title=f"Tenés {state.spec_count} specs pero 0 sesiones guardadas",
                body="Después de trabajar, guardá tu sesión para alimentar la memoria.",
                command="cortex save-session --title \"...\" --spec-summary \"...\"",
            )),
            
            # Nivel 3: Tiene contenido pero no pipeline
            (state.vault_doc_count > 5 and not state.has_github_workflows, Hint(
                icon="⚙️",
                title="Tu vault está creciendo pero no tenés pipeline CI",
                body="Configurá el pipeline para proteger la calidad automáticamente.",
                command="cortex setup pipeline",
            )),
            
            # Nivel 4: Todo local, sin enterprise
            (state.vault_doc_count > 10 and not state.has_org_yaml, Hint(
                icon="🏢",
                title="Tu knowledge base tiene sustancia. ¿Trabajás en equipo?",
                body="Podés compartir conocimiento con la capa enterprise.",
                command="cortex setup enterprise --preset small-company",
            )),
            
            # Nivel 5: Enterprise configurado, sin promotions
            (state.has_org_yaml and not state.has_enterprise_vault, Hint(
                icon="📤",
                title="Enterprise configurado pero sin conocimiento promovido",
                body="Revisá qué docs están listos para promover al vault corporativo.",
                command="cortex promote-knowledge --dry-run",
            )),
            
            # Nivel 6: No tiene IDE configurado
            (state.has_config and not state.has_mcp_config, Hint(
                icon="🔌",
                title="Cortex no está conectado a ningún IDE",
                body="Conectá tu IDE para que el agente use herramientas Cortex.",
                command="cortex inject",
            )),
            
            # Nivel 7: Todo bien
            (True, Hint(
                icon="✅",
                title="Tu proyecto Cortex está en buena forma",
                body=f"Vault: {state.vault_doc_count} docs | Specs: {state.spec_count} | Sessions: {state.session_count}",
                command="cortex search \"<tu query>\"  # Buscá algo en tu memoria",
            )),
        ]
        
        # Retornar el primer hint que aplique
        for condition, hint in hints:
            if condition:
                return hint
```

#### 3.3.3 Registro en CLI

```python
@app.command()
def hint() -> None:
    """Tip contextual: qué hacer ahora con Cortex. Zero tokens."""
    from cortex.tutor.hint import HintEngine, ProjectState
    
    state = ProjectState.detect(Path.cwd())
    engine = HintEngine()
    tip = engine.get_hint(state)
    
    console = Console()
    # Renderizar con rich panel
    console.print(Panel(
        f"{tip.body}\n\n  $ {tip.command}",
        title=f"{tip.icon} {tip.title}",
        border_style="cyan",
    ))
```

---

### Fase 4: Documentación Extendida (`docs/guides/`)

Estos archivos se escriben en Markdown estándar para lectura en GitHub. Son las versiones expandidas de lo que el tutor muestra resumido.

#### 4.1 `docs/guides/pipeline-setup.md`

Contenido a cubrir:
- Qué es el pipeline DevSecDocOps de Cortex
- Los 4 stages y su orden de ejecución
- Configuración en `config.yaml` (cada campo explicado)
- Cómo funciona `abort_early`
- Cómo cambiar el nivel de auditoría (`audit_level`)
- Ejemplo de configuración advisory vs enforced

#### 4.2 `docs/guides/pipeline-custom-modules.md`

Contenido a cubrir:
- Cómo reemplazar el linter por defecto (ruff) por otro
- Cómo reemplazar el runner de tests (pytest) por otro
- Cómo agregar un step de seguridad custom
- Cómo deshabilitar stages individuales
- Ejemplo: proyecto JS con eslint + jest en vez de ruff + pytest
- Referencia a los templates en `cortex/setup/templates.py`

#### 4.3 `docs/guides/vault-structure.md`

Contenido a cubrir:
- Anatomía completa del vault (cada carpeta y su propósito)
- Qué archivos genera cada comando (create-spec, save-session, etc.)
- Frontmatter requerido vs opcional
- Qué va a Git y qué no (`.gitignore` patterns)
- Cómo funciona el indexing semántico (`sync-vault`)
- Cómo validar docs (`validate-docs`)

#### 4.4 `docs/guides/enterprise-vault.md`

Contenido a cubrir:
- Modelo de 2 niveles: local vs enterprise
- `vault/` vs `vault-enterprise/` — qué vive en cada uno
- Flujo de promoción paso a paso
- Quién puede promover y quién revisar
- Qué pasa con el vault enterprise en Git (¿va a master?)
- Topologías y sus diferencias prácticas
- Retrieval multi-nivel: cómo funciona `--scope all`

#### 4.5 `docs/guides/configuration-reference.md`

Contenido a cubrir:
- Referencia completa de `config.yaml` (campo por campo)
- Referencia completa de `.cortex/org.yaml` (campo por campo)
- Valores por defecto y qué pasa si se omiten
- Ejemplos por perfil: dev individual, equipo pequeño, organización regulada

---

## 4. Orden de Implementación

```
Fase 1 → Infraestructura base (engine.py, TutorTopic protocol, CLI registration)
  │
  ├── Fase 2a → Tópicos core (getting_started, commands, workflow)
  │
  ├── Fase 2b → Tópicos pipeline/vault (pipeline, vault, enterprise)
  │
  ├── Fase 2c → Tópico IDE (ide_integration)
  │
  ├── Fase 3 → Sistema hint (ProjectState.detect(), HintEngine, CLI)
  │
  └── Fase 4 → Documentación extendida (docs/guides/*.md)
```

**Estimación de complejidad:**
- Fase 1: Baja (scaffolding + loop de menú)
- Fase 2: Baja (texto estático con rich formatting)
- Fase 3: Media (detección de filesystem + lógica de priorización)
- Fase 4: Media (redacción de documentación técnica)

---

## 5. Criterios de Aceptación

- [ ] `cortex tutor` abre un menú interactivo con 7 tópicos navegables
- [ ] `cortex tutor <topic>` muestra un tópico directo sin menú
- [ ] Cada tópico ocupa máximo 20-25 líneas de terminal
- [ ] Cada tópico incluye link a documentación extendida
- [ ] `cortex hint` detecta el estado del proyecto y muestra un tip relevante
- [ ] `cortex hint` funciona sin config.yaml (sugiere inicializar)
- [ ] Ningún comando consume tokens de LLM
- [ ] Los docs en `docs/guides/` cubren pipeline, vault, enterprise y configuración
- [ ] Tests unitarios para `ProjectState.detect()` y `HintEngine.get_hint()`

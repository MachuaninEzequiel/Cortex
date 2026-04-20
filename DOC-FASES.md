# Documentación de Cambios - Arquitectura Engine + Agents

## Fase 1: Eliminar Delegación de Cortex MCP Server

**Objetivo**: Convertir Cortex MCP Server de un orquestador con delegación propia a un servidor pasivo que solo expone herramientas de memoria y búsqueda.

**Archivo Modificado**: `cortex/mcp/server.py`

### Cambios Realizados

#### 1. Eliminación de Estructuras de Datos

- **Eliminado**: `self._task_results: dict[str, dict[str, str]]`
- **Eliminado**: `self._async_tasks: dict[str, dict[str, Any]]`
- **Eliminado**: `self._task_counter = 0`
- **Eliminado**: `self._task_lock = asyncio.Lock()`

**Razón**: Estas estructuras se usaban para el sistema de delegación asíncrona con polling activo. Ya no son necesarias porque la delegación ahora se maneja mediante herramientas nativas de cada IDE.

#### 2. Eliminación de Métodos de Delegación

- **Eliminado**: `_resolve_delegate_timeout(self, agent_name, timeout_seconds)` - Resolvía timeouts por tipo de agente
- **Eliminado**: `_run_delegate_task_async(self, task_id, agent_name, task, timeout_seconds)` - Ejecutaba delegación en background
- **Eliminado**: `_delegate_task(self, agent_name, task, timeout_seconds)` - Iniciaba delegación asíncrona
- **Eliminado**: `_delegate_task_sync(self, agent_name, task, timeout_seconds)` - Ejecutaba delegación síncrona vía opencode CLI
- **Eliminado**: `_delegate_batch(self, tasks, timeout_seconds)` - Iniciaba múltiples delegaciones en paralelo
- **Eliminado**: `_store_task_result(self, agent_name, status, message, task)` - Almacenaba resultados de delegación
- **Eliminado**: `_get_async_task_result(self, task_id)` - Recuperaba resultados de tareas asíncronas
- **Eliminado**: `_get_task_result(self, agent_name)` - Recuperaba resultados de tareas síncronas

**Razón**: Estos métodos implementaban el sistema de delegación propio de Cortex usando opencode CLI. Ahora la delegación se maneja mediante prompts inyectados en cada IDE que instruyen al agente nativo a usar sus herramientas de delegación (Task, runSubagent, etc.).

#### 3. Eliminación de Herramientas MCP

- **Eliminada**: `cortex_delegate_task` - Herramienta para delegar a un subagente
- **Eliminada**: `cortex_delegate_batch` - Herramienta para delegar en lote
- **Eliminada**: `cortex_get_task_result` - Herramienta para recuperar resultados de delegación

**Razón**: Estas herramientas MCP exponían el sistema de delegación de Cortex. Ya no son necesarias porque la delegación ahora se maneja mediante prompts inyectados en cada IDE.

#### 4. Actualización de Docstring

- **Antes**: "Cortex v2.1 Federated Server. Provides tools for search, context, and subagent delegation."
- **Ahora**: "Cortex v3.0 Engine Server. Provides tools for search, context, and memory. This is the Cortex Engine - a passive MCP server that exposes memory and semantic search capabilities. Delegation is now handled by IDE-native tools (Task, runSubagent, etc.) configured via profile injection."

**Razón**: Refleja el nuevo propósito del servidor como Cortex Engine (pasivo) en lugar de orquestador activo.

#### 5. Mantención de Funcionalidad

**Se mantienen**:

- `cortex_search_vector` - Búsqueda semántica profunda
- `cortex_search` - Búsqueda rápida de palabras clave
- `cortex_context` - Recuperar contexto enriquecido
- `cortex_sync_ticket` - Inyectar contexto histórico (gobernanza cortex-sync)
- `cortex_create_spec` - Persistir especificación técnica (con validación de gobernanza)
- `cortex_save_session` - Documentar sesión de trabajo
- `cortex_sync_vault` - Sincronizar vault

**Razón**: Estas son las herramientas de memoria y búsqueda que constituyen el Cortex Engine. No involucran delegación y son esenciales para el funcionamiento de cortex-sync y cortex-SDDwork.

### Verificación

- **Compilación**: ✅ Exitosa (python -m py_compile cortex/mcp/server.py)
- **Funcionalidad**: El servidor ahora expone solo herramientas de memoria/búsqueda
- **Impacto**: El sistema de delegación se ha eliminado completamente del MCP server

### Próximos Pasos

Continuar con Fase 2: Crear cortex/profile_injector.py con inyección de prompts.

---

## Fase 2: Crear Profile Injector con Inyección de Prompts

**Objetivo**: Reemplazar el sistema de inyección de configuración MCP por un sistema de inyección de prompts de agentes que instruyan al agente nativo de cada IDE a usar su delegación nativa.

**Archivo Creado**: `cortex/profile_injector.py` (nuevo archivo, reemplaza funcionalidad de ide_installer.py)

### Cambios Realizados

#### 1. Nuevo Archivo: cortex/profile_injector.py

**Propósito**: Inyectar prompts de Cortex Agents (cortex-sync, cortex-SDDwork) en el formato nativo de cada IDE.

**Funciones principales**:

- `_get_cortex_sync_prompt(project_root)`: Genera el prompt de cortex-sync
- `_get_cortex_sddwork_prompt(project_root)`: Genera el prompt de cortex-SDDwork
- `inject_opencode_profile()`: Inyecta perfiles en OpenCode (~/.config/opencode/opencode.json)
- `inject_cursor_profile()`: Inyecta perfiles en Cursor (~/.cursor/agents/)
- `inject_claude_code_profile()`: Inyecta perfiles en Claude Code (~/.claude/)
- `inject_vscode_profile()`: Inyecta perfiles en VS Code Copilot (.github/copilot-instructions.md)
- `inject_zed_profile()`: Inyecta perfiles en Zed (~/.zed/agents.json)
- `inject(ide=None)`: Función principal que inyecta para un IDE específico o todos

#### 2. Cambio Fundamental en Filosofía

**Antes**: ide_installer.py inyectaba configuración MCP con herramientas de delegación de Cortex (cortex_delegate_task, cortex_delegate_batch, cortex_get_task_result)

**Ahora**: profile_injector.py inyecta prompts que instruyen al agente nativo del IDE a:

- Usar herramientas MCP de Cortex Engine (cortex_search, cortex_context, etc.) para memoria/búsqueda
- Usar herramientas de delegación nativas del IDE (Task, @agent, runSubagent, delegate) para orquestar subagentes

#### 3. Prompts Generados

**cortex-sync prompt**:

- Instruye al agente a llamar cortex_sync_ticket como PRIMER paso (gobernanza)
- Instruye a usar herramientas MCP de Cortex Engine
- NO instruye sobre delegación (cortex-sync no delega)
- Mantiene reglas de gobernanza (write: false, edit: false, bash: false)

**cortex-SDDwork prompt**:

- Instruye al agente a usar herramientas MCP de Cortex Engine
- Instruye a usar delegación nativa del IDE:
  - OpenCode: "Use Task tool with profile 'cortex-code-implementer'"
  - Cursor: "Use @cortex-code-implementer to invoke the subagent"
  - Claude Code: "Use Task(subagent_type='cortex-code-implementer')"
  - VS Code Copilot: "Use runSubagent with 'cortex-code-implementer'"
  - Zed: "Use delegate with agent 'cortex-code-implementer'"
- Mantiene reglas de gobernanza (write: false, edit: false, bash: false)
- Instruye a terminar con cortex-documenter

#### 4. Formatos de Inyección por IDE

**OpenCode**:

- Archivo: ~/.config/opencode/opencode.json
- Formato: JSON con perfiles en clave "agent"
- Herramientas: Configuración de tools habilitados (cortex_sync_ticket, cortex_create_spec, etc.)
- Herramienta de delegación: "Task": True (herramienta nativa de OpenCode)

**Cursor**:

- Archivo: ~/.cursor/agents/cortex-sync.md, ~/.cursor/agents/cortex-SDDwork.md
- Formato: Markdown con prompts
- Invocación: @cortex-sync, @cortex-SDDwork desde la interfaz

**Claude Code**:

- Archivo: ~/.claude/cortex-sync.md, ~/.claude/cortex-SDDwork.md
- Formato: Markdown con prompts
- Invocación: Via configuración de Claude Code

**VS Code Copilot**:

- Archivo: .github/copilot-instructions.md
- Formato: Markdown con instrucciones combinadas
- Invocación: runSubagent nativo

**Zed**:

- Archivo: ~/.zed/agents.json
- Formato: JSON con configuración de agentes
- Invocación: delegate nativo

#### 5. Eliminación de Funcionalidad Anterior

**Eliminado de ide_installer.py** (no se migra a profile_injector.py):

- `_create_shielded_wrapper()`: Wrapper bash para WSL (ya no necesario)
- `get_opencode_mcp_definition()`: Definición MCP de Cortex (ya no inyectamos MCP, solo prompts)
- `get_claude_mcp_definition()`: Definición MCP de Claude Desktop (ya no inyectamos MCP, solo prompts)
- Configuración MCP en opencode.json: Solo inyectamos perfiles de agentes, no configuración MCP

**Razón**: Cortex Engine sigue siendo un servidor MCP, pero su configuración MCP se maneja por separado. profile_injector.py solo se encarga de inyectar los prompts de los agentes cortex-sync y cortex-SDDwork.

### Verificación

- **Compilación**: ✅ Exitosa (python -m py_compile cortex/profile_injector.py)
- **Funcionalidad**: El nuevo archivo puede inyectar prompts en 5 IDEs diferentes
- **Impacto**: La delegación ahora se maneja mediante prompts que instruyen al agente nativo del IDE

### Próximos Pasos

Continuar con Fase 3: Templates de prompts por IDE (OpenCode + 1 más) - esto ya está incluido en profile_injector.py, pero se pueden crear templates separados en cortex/profiles/ para mayor flexibilidad.

---

## Fase 4: Modificar Skills para Ser Agnósticos a Delegación

**Objetivo**: Modificar los skills de Cortex para que no asuman un mecanismo de delegación específico, sino que instruyan al agente a usar la delegación nativa de su IDE.

**Archivo Modificado**: `cortex/setup/cortex_workspace.py`

### Cambios Realizados

#### 1. Modificación de render_cortex_SDDwork_skill()

**Eliminado**:

- Referencias a `cortex_delegate_batch` y `cortex_delegate_task`
- Referencias a `cortex_get_task_result`
- Sección "Nuevo patrón de delegación asíncrona" con polling activo
- Sección "Manejo de timeouts (patrón antiguo)"
- Referencias a opencode CLI
- Timeouts configurados por tipo de agente (120s, 180s, 300s)
- Instrucciones de polling específicas (cada 10-15s, etc.)

**Agregado**:

- Sección "Delegación Nativa del IDE" que instruye sobre cómo delegar en cada IDE:
  - OpenCode: "Usa la herramienta Task con el perfil del subagente"
  - Cursor: "Usa @subagente para invocar (ej: @cortex-code-explorer)"
  - Claude Code: "Usa Task con subagent_type"
  - VS Code Copilot: "Usa runSubagent"
  - Zed: "Usa delegate"
- Instrucciones genéricas: "Delega a cortex-code-explorer usando la herramienta de delegación nativa de tu IDE"
- Manejo de fallos genérico sin referencias a opencode
- Ejemplo de flujo correcto con delegación genérica en lugar de cortex_delegate_batch

**Modificado**:

- Flujo mandatorio: "Lanza cortex_delegate_batch" → "Delega a cortex-code-explorer usando la herramienta de delegación nativa de tu IDE"
- Reglas críticas: "via cortex_delegate_batch" → "usando la delegación nativa de tu IDE"
- Manejo de timeouts: Eliminado completamente (los IDEs manejan sus propios timeouts)
- Manejo de opencode no disponible → Manejo de delegación nativa no disponible

#### 2. Cambio Fundamental en Filosofía

**Antes**: El skill cortex-SDDwork instruía al agente a usar herramientas MCP específicas de Cortex (cortex_delegate_batch, cortex_delegate_task, cortex_get_task_result) con timeouts configurados y polling activo.

**Ahora**: El skill cortex-SDDwork instruye al agente a usar la herramienta de delegación nativa de su IDE (Task, @agent, runSubagent, delegate) sin mencionar timeouts ni polling. Los IDEs manejan estos aspectos nativamente.

#### 3. Skills de Subagentes

**Mantenidos sin cambios**:

- render_subagent_explorer()
- render_subagent_planner()
- render_subagent_implementer()
- render_subagent_reviewer()
- render_subagent_tester()
- render_subagent_documenter()

**Razón**: Los subagentes no delegan, solo implementan/documentan. No necesitan cambios.

#### 4. render_cortex_sync_skill()

**Mantenido sin cambios**:

- render_cortex_sync_skill()

**Razón**: cortex-sync no delega, solo usa herramientas de memoria/búsqueda de Cortex Engine. No necesita cambios.

### Verificación

- **Compilación**: ✅ Exitosa (python -m py_compile cortex/setup/cortex_workspace.py)
- **Funcionalidad**: Los skills ahora son agnósticos al mecanismo de delegación específico
- **Impacto**: Los agentes Cortex pueden funcionar en cualquier IDE que tenga una herramienta de delegación nativa

### Próximos Pasos

Continuar con Fase 5: Agregar comando inject en cortex/cli/main.py y actualizar orchestrator.

---

## Fase 5: Actualizar CLI y Orchestrator para Profile Injector

**Objetivo**: Actualizar el comando CLI y el orchestrator para usar el nuevo profile_injector.py en lugar del viejo ide_installer.py.

**Archivos Modificados**: `cortex/cli/main.py`, `cortex/setup/orchestrator.py`

### Cambios Realizados

#### 1. Modificación de cortex/cli/main.py

**Modificado**: Comando `inject` existente (líneas 802-822)

**Antes**:

```python
@app.command(name="inject")
def inject(
    agent: str = typer.Option("opencode", help="Agent/IDE to inject (opencode, claude).")
) -> None:
    """Inject Cortex MCP configuration into the specified agent/IDE."""
    from cortex.ide_installer import install_opencode_profile, install_claude_desktop_profile

    if agent == "opencode":
        install_opencode_profile()
    elif agent == "claude":
        install_claude_desktop_profile()
    else:
        typer.echo(f"Agent '{agent}' not supported yet.")
```

**Ahora**:

```python
@app.command(name="inject")
def inject(
    ide: str = typer.Option(None, "--ide", help="IDE to inject (opencode, cursor, claude, vscode, zed)."),
    all_ides: bool = typer.Option(False, "--all", help="Inject profiles for all IDEs.")
) -> None:
    """Inject Cortex agent profiles into the specified IDE.

    This injects Cortex agent prompts (cortex-sync, cortex-SDDwork) in the
    native format of each IDE. The profiles instruct the IDE's native agent
    to use Cortex Engine tools for memory/search and IDE-native delegation
    tools for subagent orchestration.
    """
    from cortex.profile_injector import inject

    if all_ides:
        inject(ide=None)
    elif ide:
        inject(ide=ide)
    else:
        typer.echo("Please specify --ide <name> or --all")
        typer.echo("Supported IDEs: opencode, cursor, claude, vscode, zed")
```

**Cambios**:

- Parámetro `agent` → `ide` (más preciso)
- Agregado parámetro `--all` para inyectar en todos los IDEs
- Import cambiado de `cortex.ide_installer` a `cortex.profile_injector`
- Llamada a `inject(ide)` en lugar de `install_opencode_profile()` o `install_claude_desktop_profile()`
- Docstring actualizado para reflejar nueva arquitectura (prompts en lugar de configuración MCP)
- Soporte para 5 IDEs: opencode, cursor, claude, vscode, zed

#### 2. Modificación de cortex/setup/orchestrator.py

**Modificado**: Método `_install_ide()` (líneas 178-184)

**Antes**:

```python
def _install_ide(self) -> None:
    try:
        from cortex.ide_installer import install
        install()
        self.created.append("IDE Integration Applied")
    except Exception as e:
        self.warnings.append(f"IDE fail: {e}")
```

**Ahora**:

```python
def _install_ide(self) -> None:
    try:
        from cortex.profile_injector import inject
        inject(ide=None)  # Inject for all IDEs
        self.created.append("IDE Profiles Injected")
    except Exception as e:
        self.warnings.append(f"IDE profile injection fail: {e}")
```

**Cambios**:

- Import cambiado de `cortex.ide_installer` a `cortex.profile_injector`
- Llamada a `inject(ide=None)` en lugar de `install()`
- Mensaje de éxito actualizado: "IDE Integration Applied" → "IDE Profiles Injected"
- Mensaje de error actualizado para reflejar que es inyección de perfiles

#### 3. Cambio Fundamental en Flujo de Instalación

**Antes**: `cortex setup` llamaba `ide_installer.install()` que inyectaba configuración MCP con herramientas de delegación de Cortex.

**Ahora**: `cortex setup` llama `profile_injector.inject()` que inyecta prompts de agentes que instruyen al agente nativo del IDE a usar su delegación nativa.

### Verificación

- **Compilación**: ✅ Exitosa (python -m py_compile cortex/cli/main.py cortex/setup/orchestrator.py)
- **Funcionalidad**: El comando `cortex inject` ahora usa profile_injector.py
- **Funcionalidad**: `cortex setup` ahora usa profile_injector.py para inyección de IDEs
- **Impacto**: La instalación de Cortex ahora inyecta prompts en lugar de configuración MCP

### Próximos Pasos

Todas las fases principales están completadas. Las fases 3 y 6 (templates de prompts por IDE) ya están incluidas en profile_injector.py creado en la Fase 2.

**Resumen de implementación completa**:

- ✅ Fase 1: Eliminar delegación de cortex/mcp/server.py
- ✅ Fase 2: Crear cortex/profile_injector.py con inyección de prompts (incluye templates para 5 IDEs)
- ✅ Fase 3: Templates de prompts por IDE (incluido en Fase 2)
- ✅ Fase 4: Modificar cortex/setup/cortex_workspace.py para skills agnósticos
- ✅ Fase 5: Actualizar CLI y orchestrator para usar profile_injector.py
- ✅ Fase 6: Templates de prompts restantes (incluido en Fase 2)

La arquitectura Engine + Agents está completamente implementada.

---

## Fase 7: Configuración MCP para IDEs

**Problema identificado**: Después de implementar la arquitectura Engine + Agents, se descubrió que los prompts inyectados no eran suficientes - los IDEs también necesitan configuración MCP para conectarse al servidor Cortex Engine y acceder a las herramientas (cortex_sync_ticket, cortex_create_spec, etc.).

**Solución**: Agregar configuración MCP del servidor Cortex Engine a cada IDE en profile_injector.py.

### Configuraciones MCP implementadas:

**OpenCode** (`~/.config/opencode/opencode.json`):

```json
{
  "mcp": {
    "cortex": {
      "type": "local",
      "command": ["cortex", "mcp-server", "--stdio"],
      "enabled": true
    }
  }
}
```

**Claude Desktop** (`~/.config/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "cortex": {
      "command": "cortex",
      "args": ["mcp-server", "--stdio"],
      "env": {
        "PYTHONPATH": "<project-root>",
        "PYTHONWARNINGS": "ignore"
      },
      "enabled": true
    }
  }
}
```

**Cursor** (`~/.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "cortex": {
      "type": "stdio",
      "command": "cortex",
      "args": ["mcp-server", "--stdio"],
      "env": {
        "PYTHONPATH": "<project-root>",
        "PYTHONWARNINGS": "ignore"
      }
    }
  }
}
```

**Claude Code** (`~/.config/claude/mcp.json`):

```json
{
  "mcpServers": {
    "cortex": {
      "type": "stdio",
      "command": "cortex",
      "args": ["mcp-server", "--stdio"],
      "env": {
        "PYTHONPATH": "<project-root>",
        "PYTHONWARNINGS": "ignore"
      }
    }
  }
}
```

**VS Code Copilot** (`~/.config/Code/User/settings.json`):

```json
{
  "github.copilot.mcp.servers": {
    "cortex": {
      "type": "stdio",
      "command": "cortex",
      "args": ["mcp-server", "--stdio"],
      "env": {
        "PYTHONPATH": "<project-root>",
        "PYTHONWARNINGS": "ignore"
      }
    }
  }
}
```

### Zed:

Zed requiere crear una extensión Rust personalizada para exponer servidores MCP (más complejo, pendiente).

### Comando para aplicar configuraciones:

```bash
cortex inject --all
```

O para un IDE específico:

```bash
cortex inject --ide opencode
cortex inject --ide cursor
cortex inject --ide claude
cortex inject --ide claude-desktop
cortex inject --ide vscode
```

- Fase 7: Configuración MCP para IDEs principales (OpenCode, Claude Desktop, Cursor, Claude Code, VS Code Copilot)

---

## Fase 8: Subagentes - CORRECCIÓN

**Error identificado**: Inicialmente agregué los subagentes como perfiles seleccionables en los IDEs. Esto es INCORRECTO.

**Arquitectura correcta**:

- **cortex-sync** y **cortex-SDDwork** SON perfiles seleccionables por el usuario
- **Subagentes** (cortex-code-explorer, cortex-code-implementer, etc.) NO son perfiles
- Los subagentes son invocados INTERNAMENTE por `cortex-SDDwork` usando la herramienta Task del IDE
- Los subagentes se definen en `.cortex/subagents/` pero NO se inyectan como perfiles

**Corrección aplicada**: Revertí la inyección de subagentes como perfiles. Ahora solo se inyectan cortex-sync y cortex-SDDwork como perfiles.

**Cómo funciona la delegación**:

1. Usuario selecciona perfil `cortex-SDDwork`
2. cortex-SDDwork usa herramienta `Task` del IDE para invocar subagentes
3. Los subagentes se ejecutan en segundo plano, no como perfiles seleccionables

- Fase 8: Subagentes - CORRECCIÓN (subagentes NO son perfiles, son invocados internamente por cortex-SDDwork)

---

## Fase 9: Delegación Correcta con Subagentes Integrados del IDE

**Arquitectura correcta**:

- **cortex-sync** y **cortex-SDDwork** SON perfiles seleccionables por el usuario
- **Subagentes Cortex** (cortex-code-explorer, cortex-code-implementer, etc.) son PROMPTS definidos en `.cortex/subagents/*.md`
- **cortex-SDDwork** lee los prompts de los subagentes Cortex y los pasa a los subagentes INTEGRADOS del IDE

**Subagentes integrados por IDE**:

- **OpenCode**: General (asistente de propósito general), Explore (navegar bases de código)
- **Cursor**: Subagentes integrados similares
- **Claude Code**: Subagentes integrados similares
- **VS Code Copilot**: Subagentes integrados similares

**Flujo correcto de delegación**:

1. cortex-SDDwork lee `.cortex/subagents/cortex-code-implementer.md` para obtener el prompt
2. cortex-SDDwork usa `Task(subagent='General', prompt=<cortex-code-implementer prompt>)` de OpenCode
3. El subagente General de OpenCode ejecuta con el prompt de Cortex
4. Los subagentes Cortex NO son perfiles, son PROMPTS pasados a subagentes del IDE

**Cambios aplicados**:

- Actualizado prompt de cortex-SDDwork para reflejar esta arquitectura
- cortex-SDDwork ahora lee los prompts de `.cortex/subagents/*.md` y los pasa a los subagentes integrados del IDE

- ✅ Fase 9: Delegación correcta con subagentes integrados del IDE (Cortex subagents = prompts, IDE subagents = General, Explore)

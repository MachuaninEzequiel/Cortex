# SPEC-REFAC-WORKSPACE-STRUCT v2.0

**Fecha:** 2026-05-03  
**Estado:** Listo para implementar  
**Prioridad:** Alta  
**Complejidad estimada:** Alta  
**Riesgo global si se hace en hard cut:** Alto  
**Riesgo global si se hace con compatibilidad temporal y gates:** Medio  
**Revisión:** Incorpora hallazgos de revisión arquitectónica, conexiones faltantes y requerimiento de contenedor `.cortex/`

---

## 0. Resumen Ejecutivo

Este documento define la refactorización del workspace de Cortex para consolidar toda la infraestructura del proyecto del usuario en un único contenedor `.cortex/`, accesible y navegable, sin archivos ocultos adicionales en su interior.

### Principio rector

> **Un solo directorio, toda la infraestructura, todo accesible.**

```
<repo-root>/
  .cortex/                          ← workspace_root (TODO lo de Cortex aquí)
    config.yaml
    vault/
    vault-enterprise/
    memory/
    enterprise-memory/
    AGENT.md
    system-prompt.md
    org.yaml
    workspace.yaml
    skills/
    subagents/
    webgraph/
    logs/
    scripts/
    promotion/
  .github/
    workflows/                      ← ÚNICO elemento fuera de .cortex/ (requerido por GitHub)
```

### Lo que NO cambia

- La lógica de negocio de Cortex (memoria híbrida, retrieval, enterprise, pipeline, Jira)
- Los comandos de CLI y sus firmas públicas
- Los MCP tools y sus interfaces
- El modelo de ejecución tripartito (sync → SDDwork → documenter)
- La conexión con Jira (lectura por API, escritura en vault)
- El formato y semántica de los documentos del vault

### Lo que SÍ cambia

- La **resolución de rutas** se centraliza en un único contrato
- Los **paths físicos** se mueven de la raíz del repo a `.cortex/`
- Los **generadores de setup** escriben exclusivamente en `.cortex/`
- La ** discovery de proyecto** se adapta al nuevo layout con compatibilidad dual

---

## 1. Problema Actual

Cortex asume un layout distribuido en la raíz del repo del usuario. En esta base aparecen referencias legacy a:

```
<repo-root>/
  config.yaml                    ← Raíz contaminada
  vault/                         ← Raíz contaminada
  vault-enterprise/              ← Raíz contaminada
  .memory/                      ← Raíz contaminada
  scripts/devsecdocops.sh        ← Raíz contaminada
  .cortex/
    skills/                      ← Ya dentro de .cortex
    subagents/                   ← Ya dentro de .cortex
    AGENT.md                     ← Ya dentro de .cortex
    system-prompt.md             ← Ya dentro de .cortex
    org.yaml                     ← Ya dentro de .cortex
    workspace.yaml               ← Ya dentro de .cortex
    webgraph/
      config.yaml
      workspace.yaml
      cache/
    logs/
```

Esto genera cuatro problemas estructurales:

1. **DX pobre en la raiz del proyecto** — Cortex ensucia la raíz con demasiados directorios y archivos operativos.

2. **Resolución de rutas distribuida** — Siete módulos diferentes resuelven paths de forma local y no centralizada:
   - `core.py` → `self.project_root = self._config_path.resolve().parent`
   - `enterprise/config.py` → `DEFAULT_ENTERPRISE_CONFIG_PATH = Path(".cortex") / "org.yaml"`
   - `enterprise/models.py` → `resolve_enterprise_vault_path(project_root)`
   - `webgraph/config.py` → `root / ".cortex" / "webgraph" / "config.yaml"`
   - `ide/__init__.py` → `_find_project_root()` busca `.cortex/`
   - `doctor.py` → busca `config.yaml` en raíz, `.cortex/` en raíz
   - `runtime_context.py` → `resolve_episodic_persist_dir(project_root, cfg)`

3. **Acoplamiento fuerte entre setup y runtime** — No alcanza con cambiar los generadores. Hay que actualizar los consumidores en tiempo de ejecución.

4. **Alto riesgo de regresión silenciosa** — Un proyecto puede inicializar "bien" pero luego fallar en MCP, IDE, WebGraph o doctor porque alguno sigue mirando el layout viejo.

---

## 2. Hallazgos Quirurgicos del Repo Actual (Verificados)

### 2.1 Runtime y resolución de config

| Archivo | Acoplamiento | Detalle |
|---|---|---|
| `cortex/core.py` | **Crítico** | `self.project_root = self._config_path.resolve().parent` — Si config se mueve a `.cortex/config.yaml`, project_root sería `.cortex/` y los paths relativos se duplicarían: `.cortex/vault/` en vez de `.cortex/` + `vault/` |
| `cortex/runtime_context.py` | **Alto** | `resolve_episodic_persist_dir()` usa `project_root / persist_dir_cfg` |
| `cortex/cli/main.py` | **Alto** | `_load_memory()` usa `Path("config.yaml")` y `Path.cwd()` |
| `cortex/doctor.py` | **Alto** | Busca `config.yaml`, `.cortex/`, `vault/`, `.memory/` todos en raíz |

### 2.2 Workspace y activos

| Archivo | Acoplamiento | Detalle |
|---|---|---|
| `cortex/setup/cortex_workspace.py` | **Alto** | Escribe `.cortex/skills/`, `.cortex/subagents/`, `.cortex/AGENT.md`, `.cortex/system-prompt.md` |
| `cortex/setup/orchestrator.py` | **Crítico** | Crea `.memory/`, `vault/`, `vault-enterprise/`, `scripts/`, `config.yaml` — todos en raíz |

### 2.3 Enterprise

| Archivo | Acoplamiento | Detalle |
|---|---|---|
| `cortex/enterprise/config.py` | **Crítico** | `DEFAULT_ENTERPRISE_CONFIG_PATH = Path(".cortex") / "org.yaml"` — hardcoded |
| `cortex/enterprise/models.py` | **Alto** | `resolve_enterprise_vault_path(project_root)` y `resolve_enterprise_memory_path(project_root)` |
| `cortex/enterprise/knowledge_promotion.py` | **Alto** | `from_project_root(root)` construye `PromotionPaths` con `root / "vault-enterprise"` y `enterprise_vault / ".cortex" / "promotion"` |
| `cortex/enterprise/reporting.py` | **Medio** | `_local_source()` usa `project_root / "vault"` hardcoded |

### 2.4 IDE y descubrimiento

| Archivo | Acoplamiento | Detalle |
|---|---|---|
| `cortex/ide/__init__.py` | **Crítico** | `_find_project_root()` busca `(parent / ".cortex").exists()` — es el discovery |
| `cortex/ide/adapters/*.py` (9 archivos) | **Medio** | Cada adapter recibe `project_root` y lo usa para construir paths |
| `cortex/ide/prompts.py` | **Medio** | Genera contenido de prompts que referencia paths |

### 2.5 MCP Server

| Archivo | Acoplamiento | Detalle |
|---|---|---|
| `cortex/mcp/server.py` | **Crítico** | 3 puntos de acoplamiento: (1) busca `config.yaml` en `project_root`, (2) logs en `.cortex/logs/`, (3) subagentes en `.cortex/subagents/` |

### 2.6 WebGraph

| Archivo | Acoplamiento | Detalle |
|---|---|---|
| `cortex/webgraph/config.py` | **Crítico** | `default_path()` = `root / ".cortex" / "webgraph" / "config.yaml"` |
| `cortex/webgraph/service.py` | **Alto** | Construye `SemanticSource` y `EpisodicSource` con `project_root` |
| `cortex/webgraph/setup.py` | **Alto** | `attach_project_root()` escribe en `.cortex/webgraph/workspace.yaml` |
| `cortex/webgraph/cache.py` | **Medio** | Usa `project_root` para cache |
| `cortex/webgraph/federation.py` | **Medio** | Carga enterprise config |
| `cortex/webgraph/episodic_source.py` | **Medio** | Recibe `persist_dir` |
| `cortex/webgraph/semantic_source.py` | **Medio** | Recibe `vault_path` |

### 2.7 Diagnóstico, hinting y política Git

| Archivo | Acoplamiento | Detalle |
|---|---|---|
| `cortex/doctor.py` | **Crítico** | Valida `config.yaml`, `.cortex/`, `vault/`, `.memory/`, `.cortex/org.yaml` — todos en raíz |
| `cortex/tutor/hint.py` | **Alto** | `ProjectState.detect()` busca `config.yaml`, `.cortex/`, `vault/` directamente |
| `cortex/git_policy.py` | **Medio** | `RECOMMENDED_GITIGNORE_PATTERNS` lista `.memory/`, `*.chroma/`, `vault/sessions/` |

### 2.8 Conexiones adicionales no identificadas en el documento original

| Archivo | Acoplamiento | Detalle |
|---|---|---|
| `cortex/mcp/server.py` (logs) | **Alto** | `log_dir = project_root / ".cortex" / "logs"` — hardcoded |
| `cortex/mcp/server.py` (subagentes) | **Alto** | `subagent_file = project_root / ".cortex" / "subagents" / f"{agent_name}.md"` — hardcoded |
| `cortex/tutor/hint.py` | **Alto** | `ProjectState.detect(Path.cwd())` no usa resolvedor |
| `cortex/setup/cold_start.py` | **Medio** | `run_cold_start(project_root, episodic, vault_path)` — usa `project_root` para git log |
| `cortex/semantic/vault_reader.py` | **Medio** | `_INDEX_FILE = ".cortex_index.json"` — hardcoded en vault root |
| `cortex/enterprise/sources.py` | **Medio** | `MultiVaultReader` y `MultiEpisodicReader` reciben paths ya resueltos |
| `cortex/enterprise/reporting.py` | **Medio** | `_local_source()` usa `self.project_root / "vault"` directamente |

---

## 3. Objetivos del Refactor

1. Reducir la contaminación visual de la raíz del repo del usuario.
2. Consolidar toda la infraestructura de Cortex en `.cortex/`.
3. Mantener visibles y accesibles todos los archivos del workspace.
4. Permitir compatibilidad temporal con repos ya inicializados.
5. Centralizar la resolución de rutas en un único contrato (`WorkspaceLayout`).
6. Permitir que setup, runtime, IDE, MCP y WebGraph lean el mismo modelo.
7. Evitar que el cambio dependa de coincidencias accidentales de `cwd`.
8. Que la carpeta `.cortex/` no contenga archivos ocultos adicionales (no `.system/`).
9. Que un desarrollador pueda entrar a `.cortex/` y leer/modificar todo.

## 4. No Objetivos

Este refactor **no** busca:

- cambiar la semántica de memoria híbrida
- cambiar el modelo de promotion enterprise
- rediseñar el formato lógico de los documentos del vault
- rehacer la UX de WebGraph en esta misma especificación
- eliminar soporte legacy en la misma release de la migración
- cambiar la conexión con Jira (funciona igual, lee por API y escribe en vault)
- cambiar los MCP tools ni sus interfaces

---

## 5. Principios de Diseño

1. **Resolver antes de escribir** — Primero se redefine cómo Cortex descubre y resuelve paths. Después se cambian los generadores.

2. **Nuevo layout con compatibilidad temporal** — Los lectores deben entender ambos layouts antes de que los escritores emitan solo el nuevo.

3. **Un solo contrato de layout** — Ningún módulo crítico debe hardcodear `config.yaml`, `.memory`, `vault` sin pasar por `WorkspaceLayout`.

4. **`repo_root` y `workspace_root` no son lo mismo** — El repo del usuario tiene raíz Git. Cortex vive dentro de `workspace_root = repo_root / ".cortex"`.

5. **Los paths relativos deben tener una base declarada** — Todos los paths relativos en config se resuelven contra `workspace_root`.

6. **`.cortex/` no contiene archivos ocultos adicionales** — Todo dentro de `.cortex/` es accesible y navegable por el desarrollador.

7. **Dualidad de nombres** — La carpeta contenedora ya existe como `.cortex/`. Los archivos ya dentro (skills, subagents, org.yaml, etc.) permanecen donde están. Los archivos fuera (config.yaml, vault/, .memory/) se mueven hacia adentro.

8. **`.github/workflows/` permanece en raíz** — GitHub Actions no soporta workflows en subdirectorios arbitrarios.

9. **Soporte Windows y Unix** — `.cortex/` comienza con punto (convención Unix de oculto). En Windows no se oculta automáticamente, pero eso es aceptable: el contenido es accesible por diseño.

---

## 6. Contrato de Layout Objetivo

### 6.1 Layout definitivo

```text
<repo-root>/
  .github/
    workflows/                        ← Fuera de .cortex (requerido por GitHub)
      ci-pull-request.yml
      ci-feature.yml
      cd-deploy.yml
      ci-enterprise-governance.yml
      ci-security.yml
  .cortex/                            ← workspace_root
    config.yaml
    vault/
      architecture.md
      decisions.md
      runbooks.md
      sessions/
      decisions/
      runbooks/
      incidents/
      hu/
      specs/
    vault-enterprise/
      README.md
      runbooks/
      decisions/
      incidents/
      hu/
      promotion/
        records.jsonl
    memory/
      chroma/
    enterprise-memory/
      chroma/
    AGENT.md
    system-prompt.md
    org.yaml
    workspace.yaml
    skills/
      cortex-sync.md
      cortex-SDDwork.md
      cortex-SDDwork-cursor.md
      obsidian-markdown/
      obsidian-cli/
      obsidian-bases/
      json-canvas/
      defuddle/
    subagents/
      cortex-code-explorer.md
      cortex-code-implementer.md
      cortex-documenter.md
    webgraph/
      config.yaml
      workspace.yaml
      cache/
    logs/
    scripts/
      devsecdocops.sh
  .gitignore
  README.md
  pyproject.toml
  requirements.txt
```

### 6.2 Decisión de diseño clave

**Todos los paths relativos declarados por Cortex se resuelven contra `workspace_root = repo_root / ".cortex"`, no contra el parent físico del archivo de config ni contra `cwd`.**

En este modelo, `config.yaml` dentro de `.cortex/` mantiene rutas relativas al workspace root:

```yaml
episodic:
  persist_dir: memory
semantic:
  vault_path: vault
```

Y `org.yaml` dentro de `.cortex/` mantiene:

```yaml
memory:
  enterprise_vault_path: vault-enterprise
  enterprise_memory_path: enterprise-memory
```

### 6.3 Razón de esta decisión

Si `config.yaml` vive dentro de `.cortex/` y los valores relativos son `memory`, `vault`, etc., estos se resuelven como:

```
workspace_root / "memory" → repo_root / ".cortex" / "memory"
workspace_root / "vault"   → repo_root / ".cortex" / "vault"
```

Esto evita la duplicación `cortex/cortex/...` que se produciría si los paths se resolvieran contra `repo_root`.

### 6.4 Mapping completo legacy → nuevo

| Archivo/Directorio Legacy | Ubicación Nueva |
|---|---|
| `config.yaml` | `.cortex/config.yaml` |
| `vault/` | `.cortex/vault/` |
| `vault-enterprise/` | `.cortex/vault-enterprise/` |
| `.memory/chroma/` | `.cortex/memory/chroma/` |
| `.cortex/AGENT.md` | `.cortex/AGENT.md` (sin cambio) |
| `.cortex/system-prompt.md` | `.cortex/system-prompt.md` (sin cambio) |
| `.cortex/org.yaml` | `.cortex/org.yaml` (sin cambio) |
| `.cortex/workspace.yaml` | `.cortex/workspace.yaml` (sin cambio) |
| `.cortex/skills/` | `.cortex/skills/` (sin cambio) |
| `.cortex/subagents/` | `.cortex/subagents/` (sin cambio) |
| `.cortex/webgraph/` | `.cortex/webgraph/` (sin cambio) |
| `.cortex/logs/` | `.cortex/logs/` (sin cambio) |
| `.cortex/webgraph/cache/` | `.cortex/webgraph/cache/` (sin cambio) |
| `.memory/enterprise/` | `.cortex/enterprise-memory/` |
| `scripts/devsecdocops.sh` | `.cortex/scripts/devsecdocops.sh` |
| `.github/workflows/` | `.github/workflows/` (sin cambio, fuera de .cortex) |
| `vault-enterprise/.cortex/promotion/` | `.cortex/vault-enterprise/promotion/` |

**Nota clave:** Los archivos que YA están dentro de `.cortex/` no se mueven. Solo se mueven hacia adentro los que están fuera.

---

## 7. API de WorkspaceLayout

Se introducirá un módulo `cortex/workspace/layout.py` como resolvedor central único.

```python
class WorkspaceLayout:
    """Resolvedor central de rutas del workspace Cortex."""

    # ── Discovery ──
    @classmethod
    def discover(cls, start: Path) -> "WorkspaceLayout":
        """Buscar workspace_root desde start hacia arriba.
        
        Precedencia:
        1. Si existe start/.cortex/.system/workspace.yaml con layout_version >= 2 → nuevo layout
        2. Si existe start/.cortex/config.yaml → nuevo layout (sin workspace.yaml aún)
        3. Si existe start/.cortex/ y start/config.yaml → legacy layout
        4. Si existe start/config.yaml → legacy layout
        5. Bootstrap limpio
        """

    @classmethod
    def from_repo_root(cls, repo_root: Path) -> "WorkspaceLayout":
        """Construir WorkspaceLayout asumiendo repo_root conocido."""

    # ── Roots ──
    repo_root: Path              # Raíz Git / raíz del proyecto del usuario
    workspace_root: Path         # repo_root / ".cortex"
    is_legacy_layout: bool       # True si se detectó layout viejo
    is_new_layout: bool          # True si se detectó layout nuevo

    # ── Config ──
    config_path: Path            # workspace_root / "config.yaml"
    org_config_path: Path        # workspace_root / "org.yaml"

    # ── Vault ──
    vault_path: Path             # workspace_root / "vault"
    enterprise_vault_path: Path  # workspace_root / "vault-enterprise"

    # ── Memory ──
    episodic_memory_path: Path    # workspace_root / "memory"
    enterprise_memory_path: Path  # workspace_root / "enterprise-memory"

    # ── Workspace Assets ──
    skills_dir: Path              # workspace_root / "skills"
    subagents_dir: Path          # workspace_root / "subagents"
    agent_guidelines_path: Path   # workspace_root / "AGENT.md"
    system_prompt_path: Path      # workspace_root / "system-prompt.md"
    workspace_yaml_path: Path     # workspace_root / "workspace.yaml"

    # ── WebGraph ──
    webgraph_dir: Path            # workspace_root / "webgraph"
    webgraph_config_path: Path    # workspace_root / "webgraph" / "config.yaml"
    webgraph_workspace_path: Path # workspace_root / "webgraph" / "workspace.yaml"
    webgraph_cache_dir: Path     # workspace_root / "webgraph" / "cache"

    # ── Runtime ──
    logs_dir: Path                # workspace_root / "logs"
    scripts_dir: Path            # workspace_root / "scripts"

    # ── CI/CD ──
    workflows_dir: Path           # repo_root / ".github" / "workflows"

    # ── Promotion ──
    promotion_records_path: Path  # enterprise_vault_path / "promotion" / "records.jsonl"

    # ── Vault Index ──
    vault_index_path: Path        # vault_path / ".cortex_index.json"

    # ── Git ──
    gitignore_path: Path          # repo_root / ".gitignore"

    # ── Resolution ──
    def resolve_workspace_relative(self, value: str | Path) -> Path:
        """Resolver un path relativo contra workspace_root."""
        return self.workspace_root / value

    # ── Legacy compatibility ──
    def legacy_config_path(self) -> Path:
        """Path de config.yaml en layout legacy (repo_root / config.yaml)."""
        return self.repo_root / "config.yaml"

    def legacy_vault_path(self) -> Path:
        """Path de vault en layout legacy (repo_root / vault)."""
        return self.repo_root / "vault"

    def legacy_memory_path(self) -> Path:
        """Path de .memory en layout legacy (repo_root / .memory)."""
        return self.repo_root / ".memory"
```

### 7.1 Versionado del layout

`workspace.yaml` contendrá un campo `layout_version` que permite distinguir layouts sin ambigüedad:

```yaml
# .cortex/workspace.yaml
layout_version: 2
projects:
  - id: primary
    path: .
    role: owner
```

- `layout_version: 1` (o ausente) = layout legacy (archivos distribuidos en raíz)
- `layout_version: 2` = layout nuevo (todo dentro de `.cortex/`)

### 7.2 Compatibilidad requerida

El resolvedor debe poder descubrir:

1. **Layout nuevo** — si existe `repo_root/.cortex/config.yaml` o `repo_root/.cortex/workspace.yaml` con `layout_version >= 2`
2. **Layout legacy** — si existen `repo_root/config.yaml` o `repo_root/.cortex/` (sin config.yaml dentro)
3. **Boostrap limpio** — si no existe ninguno

### 7.3 Precedencia de discovery

1. Si existe `repo_root/.cortex/workspace.yaml` con `layout_version >= 2` → **nuevo layout**
2. Si existe `repo_root/.cortex/config.yaml` → **nuevo layout** (setup en progreso)
3. Si existen `repo_root/config.yaml` o `repo_root/.cortex/` (sin config.yaml dentro) → **legacy layout**
4. Si no existe ninguno → **boostrap limpio** → setup creará layout nuevo

---

## 8. Semaforo Global por Fases

### 🔴 Rojo — No avanzar sin gate técnico formal

- Fase 0: Contrato de layout
- Fase 1: Compatibilidad dual
- Fase 2: Centralización de resolución de paths
- Fase 8: Retiro de compatibilidad legacy

### 🟡 Amarillo — Requiere smoke tests y validación cruzada

- Fase 3: Runtime crítico
- Fase 4: Setup y generadores
- Fase 5: IDE, MCP y WebGraph
- Fase 6: Docs, doctor, hint, tests

### 🟢 Verde — Activación una vez cerradas las anteriores

- Fase 7: Activar layout nuevo por defecto

---

## 9. Plan de Implementacion por Fases

---

### Fase 0 — Definir el Contrato de Layout

**Semaforo:** 🔴 Rojo  
**Objetivo:** Congelar una única verdad semantica para el nuevo workspace antes de tocar los consumidores.

#### Alcance

- Definir formalmente `repo_root`, `workspace_root` y la API de `WorkspaceLayout`
- Definir la base de resolución de todos los paths relativos
- Definir el arbol objetivo exacto (Sección 6.1)
- Decidir el destino de promotion metadata y WebGraph
- Crear el módulo `cortex/workspace/layout.py` con la API completa

#### Decisiones obligatorias

1. `config.yaml` vive en `.cortex/config.yaml`
2. `org.yaml` vive en `.cortex/org.yaml` (sin cambio)
3. Los valores relativos de config se resuelven contra `workspace_root`
4. WebGraph permanece en `.cortex/webgraph/` (sin cambio)
5. Promotion records viven en `.cortex/vault-enterprise/promotion/records.jsonl`
6. Memory episódica vive en `.cortex/memory/`
7. Enterprise memory vive en `.cortex/enterprise-memory/`
8. Scripts viven en `.cortex/scripts/`
9. `.github/workflows/` permanece en raíz del repo (requerido por GitHub)
10. No se crea `.system/` ni ninguna subcarpeta oculta dentro de `.cortex/`

#### Archivos que deben quedar alineados al terminar la fase

- `cortex/workspace/__init__.py` (nuevo)
- `cortex/workspace/layout.py` (nuevo)
- `docs/refact/REFAC-WORKSPACE-STRUCT.md` (este documento)
- `docs/refact/REFAC-WEBGRAPH.md` (actualizar referencias)

#### Riesgos

- Elegir una base de resolución equivocada y propagar el error a todo el sistema
- Dejar fuera del contrato piezas reales como `AGENT.md`, `system-prompt.md`, `workspace.yaml`, `logs/`, `scripts/`

#### Gate de salida

- [ ] El layout final está documentado sin contradicciones
- [ ] Existe una regla única y declarativa para resolver cualquier path interno
- [ ] `WorkspaceLayout` implementado con discovery, resolución y compatibilidad legacy
- [ ] Tests unitarios de `WorkspaceLayout` pasan con ambos layouts

#### Rollback

- No aplica; esta fase es de definición

---

### Fase 1 — Introducir Compatibilidad Dual

**Semaforo:** 🔴 Rojo  
**Objetivo:** Permitir que Cortex lea tanto el layout nuevo como el legacy durante la transición.

#### Alcance

- Discovery de proyecto (nuevo y legacy)
- Carga de config local (desde `.cortex/config.yaml` o `config.yaml`)
- Carga de config enterprise (desde `.cortex/org.yaml`)
- Descubrimiento de skills, subagentes y guidelines
- Lectura de paths de WebGraph
- Lectura de paths de memoria episódica y enterprise

#### Archivos impactados

```
cortex/workspace/layout.py                          (nuevo — implementar discovery)
cortex/core.py                                      (usar WorkspaceLayout)
cortex/runtime_context.py                            (usar WorkspaceLayout)
cortex/cli/main.py                                   (usar WorkspaceLayout)
cortex/doctor.py                                     (usar WorkspaceLayout)
cortex/enterprise/config.py                           (usar WorkspaceLayout para org.yaml)
cortex/enterprise/models.py                           (usar WorkspaceLayout para paths)
cortex/enterprise/knowledge_promotion.py              (usar WorkspaceLayout para promotion)
cortex/enterprise/reporting.py                        (usar WorkspaceLayout para vaults)
cortex/ide/__init__.py                                (usar WorkspaceLayout para discovery)
cortex/mcp/server.py                                 (usar WorkspaceLayout para config y subagents)
cortex/webgraph/cli.py                               (usar WorkspaceLayout)
cortex/webgraph/config.py                             (usar WorkspaceLayout)
cortex/webgraph/federation.py                         (usar WorkspaceLayout)
cortex/webgraph/setup.py                              (usar WorkspaceLayout)
cortex/webgraph/cache.py                              (usar WorkspaceLayout)
cortex/webgraph/semantic_source.py                    (usar WorkspaceLayout)
cortex/webgraph/episodic_source.py                    (usar WorkspaceLayout)
cortex/semantic/vault_reader.py                       (usar WorkspaceLayout para index path)
cortex/tutor/hint.py                                 (usar WorkspaceLayout para detection)
```

#### Regla operativa

Mientras dure esta fase:

- Los **lectores** entienden ambos layouts
- Los **escritores** todavía pueden seguir emitiendo legacy o nuevo según el estado de implementación
- Ningún comando crítico debe asumir que solo existe uno de los dos

#### Gate de salida

- [ ] Un repo legacy inicializado antes del cambio sigue funcionando
- [ ] Un repo nuevo con layout nuevo puede ser descubierto y leído
- [ ] `doctor` reporta correctamente ambos layouts durante la transición
- [ ] `WorkspaceLayout.discover()` funciona desde cualquier subdirectorio del repo

#### Rollback

- Mantener prioridad legacy si el nuevo layout no se detecta con suficiente confiabilidad

---

### Fase 2 — Centralizar la Resolución de Paths

**Semaforo:** 🔴 Rojo  
**Objetivo:** Eliminar hardcodes estructurales en módulos críticos y reemplazarlos por el resolvedor central.

#### Alcance funcional

- Paths de config local
- Paths de org enterprise
- Paths de vault local y enterprise
- Paths de memoria episódica local y enterprise
- Paths de skills, subagentes, prompts y guidelines
- Paths de WebGraph
- Paths de logs MCP
- Paths de scripts

#### Archivos impactados de forma crítica

```
cortex/core.py                          (project_root → workspace_root)
cortex/runtime_context.py                (resolver con WorkspaceLayout)
cortex/doctor.py                         (resolver con WorkspaceLayout)
cortex/cli/main.py                       (usar WorkspaceLayout en _load_memory)
cortex/mcp/server.py                    (config_path, logs_dir, subagents_dir con WorkspaceLayout)
cortex/enterprise/config.py              (org.yaml path con WorkspaceLayout)
cortex/enterprise/models.py              (resolve_enterprise_vault_path con WorkspaceLayout)
cortex/enterprise/knowledge_promotion.py (PromotionPaths con WorkspaceLayout)
cortex/enterprise/reporting.py           (vaults paths con WorkspaceLayout)
cortex/enterprise/sources.py             (MultiVaultReader paths con WorkspaceLayout)
cortex/semantic/vault_reader.py          (index path con WorkspaceLayout)
cortex/webgraph/cli.py                   (usar WorkspaceLayout)
cortex/webgraph/semantic_source.py        (vault_path con WorkspaceLayout)
cortex/webgraph/episodic_source.py        (persist_dir con WorkspaceLayout)
cortex/webgraph/config.py                (default_path con WorkspaceLayout)
cortex/webgraph/federation.py            (enterprise config con WorkspaceLayout)
cortex/webgraph/cache.py                 (cache dir con WorkspaceLayout)
cortex/tutor/hint.py                     (ProjectState.detect con WorkspaceLayout)
```

#### Reglas de implementación

1. **Ningún módulo debe construir paths de layout con strings hardcodeados** si ya existe un valor equivalente en el resolvedor.
2. **Ningún módulo crítico debe depender implícitamente de `Path.cwd()`** sin pasar por `WorkspaceLayout.discover()`.
3. **Los defaults del runtime deben declararse en términos del contrato nuevo**, no del legacy.
4. **`AgentMemory.project_root` debe renombrarse a `AgentMemory.workspace_root`** con un property `project_root` que emita DeprecationWarning durante la transición.

#### Riesgos

- Resolver correctamente config pero no WebGraph
- Resolver memoria local pero no enterprise
- Dejar paths "pequeños" legacy en mensajes, hints o validaciones

#### Gate de salida

- [ ] Los módulos críticos de lectura usan el resolvedor central
- [ ] Ya no hay dependencia estructural fuerte de `.memory`, `config.yaml` en raíz o `vault` en raíz
- [ ] `AgentMemory.workspace_root` funciona correctamente en ambos layouts
- [ ] DeprecationWarning emitido cuando se usa `project_root`

#### Rollback

- Mantener wrappers de compatibilidad que sigan exponiendo rutas legacy derivadas

---

### Fase 3 — Migrar Runtime Crítico

**Semaforo:** 🟡 Amarillo  
**Objetivo:** Hacer que la operación real de Cortex use el nuevo layout correctamente.

#### Flujos que deben quedar funcionando

- `AgentMemory` init, `remember`, `forget`, `stats`
- `search`, `context` (local y enterprise)
- `sync-vault`, `index-docs`, `validate-docs`
- `create-spec`, `save-session`
- `cortex hu import/list/show`
- retrieval enterprise (`search --scope enterprise/all`)
- promotion (`promote-knowledge`, `review-knowledge`)
- reporting (`memory-report`)
- `doctor`

#### Archivos impactados

```
cortex/core.py
cortex/runtime_context.py
cortex/services/spec_service.py
cortex/services/session_service.py
cortex/services/pr_service.py
cortex/workitems/service.py
cortex/enterprise/knowledge_promotion.py
cortex/enterprise/retrieval_service.py
cortex/enterprise/reporting.py
cortex/doctor.py
cortex/episodic/memory_store.py      (persist_dir con WorkspaceLayout)
cortex/semantic/vault_reader.py       (vault_path con WorkspaceLayout)
cortex/embedders/factory.py           (model cache path)
cortex/context_enricher/enricher.py   (usa episodic y semantic)
cortex/retrieval/hybrid_search.py     (usa episodic y semantic)
cortex/setup/cold_start.py            (project_root → repo_root para git log)
```

#### Requisitos de esta fase

1. `AgentMemory` debe usar `workspace_root` como base de resolución
2. La memoria episódica local debe resolver a `.cortex/memory/chroma`
3. La memoria enterprise debe resolver a `.cortex/enterprise-memory/chroma`
4. El vault local debe resolver a `.cortex/vault`
5. El enterprise vault debe resolver a `.cortex/vault-enterprise`
6. `cold_start.py` debe usar `repo_root` (no `workspace_root`) para `git log`
7. `VaultReader` debe buscar `.cortex_index.json` dentro de `.cortex/vault/`

#### Riesgos

- Ruptura silenciosa de indexing (ChromaDB path duplicado)
- Creación de archivos en rutas duplicadas tipo `.cortex/.cortex/...` o `.cortex/cortex/...`
- Promotion escribiendo records en ubicaciones inconsistentes
- Cold start usando `workspace_root` para `git log` (debe usar `repo_root`)

#### Gate de salida

- [ ] Un proyecto nuevo puede: guardar specs, guardar sesiones, sincronizar vault, recuperar contexto local, cargar configuración enterprise
- [ ] Un proyecto legacy sigue siendo legible
- [ ] `git log` funciona correctamente (usa repo_root, no workspace_root)
- [ ] Promotion records se escriben en `.cortex/vault-enterprise/promotion/`
- [ ] Jira integration funciona (lee por API, escribe en `.cortex/vault/hu/`)

#### Rollback

- Permitir fallback temporal a lectura legacy mientras el resolvedor central decide rutas

---

### Fase 4 — Migrar Setup y Generadores

**Semaforo:** 🟡 Amarillo  
**Objetivo:** Hacer que el bootstrap escriba exclusivamente el layout nuevo.

#### Alcance

- Directorios base
- Config local
- Config enterprise
- Enterprise workspace
- Skills, subagentes, prompts y guidelines
- Scripts
- Workflows
- Templates de docs
- Cold start (git indexing)

#### Archivos impactados

```
cortex/setup/orchestrator.py
cortex/setup/templates.py
cortex/setup/cortex_workspace.py
cortex/setup/cold_start.py
cortex/setup/detector.py
cortex/setup/enterprise_presets.py
cortex/setup/enterprise_wizard.py
cortex/enterprise/config.py            (write_enterprise_config)
cortex/cli/main.py                      (comandos setup)
```

#### Reglas de escritura

1. `cortex setup agent` debe escribir:
   - `.cortex/config.yaml`
   - `.cortex/vault/...`
   - `.cortex/memory/chroma/`
   - `.cortex/AGENT.md`
   - `.cortex/system-prompt.md`
   - `.cortex/skills/...`
   - `.cortex/subagents/...`
   - `.cortex/workspace.yaml` con `layout_version: 2`

2. `cortex setup enterprise` debe escribir:
   - `.cortex/vault-enterprise/...`
   - `.cortex/vault-enterprise/promotion/`
   - `.cortex/org.yaml`
   - `.cortex/enterprise-memory/chroma/` (si enterprise_episodic_enabled)

3. `cortex setup pipeline` debe escribir:
   - `.cortex/config.yaml` (si no existe)
   - `.cortex/scripts/devsecdocops.sh`
   - `.github/workflows/...` (en raíz, NO dentro de .cortex)
   - `.cortex/org.yaml`

4. `cortex setup webgraph` debe escribir:
   - `.cortex/webgraph/config.yaml`
   - `.cortex/webgraph/workspace.yaml`
   - `.cortex/webgraph/cache/`

#### Templates y referencias que deben actualizarse

- Los workflows de GitHub Actions generados por `render_ci_pull_request()` y `render_ci_enterprise_governance()` deben usar `--vault .cortex/vault` o autodetection
- Los scripts generados deben referenciar `.cortex/`
- Los mensajes de `doctor` y `hint` deben mostrar paths del nuevo layout
- Los comandos `install-skills` deben instalar en `.cortex/skills/` (ya es así)
- El `DEVSECDOCSOPS_SCRIPT` template debe usar `.cortex/vault` como `VAULT_PATH`

#### Gate de salida

- [ ] Un repo inicializado desde cero genera exclusivamente el layout nuevo
- [ ] `.github/workflows/` se crea en raíz, no dentro de `.cortex/`
- [ ] `workspace.yaml` tiene `layout_version: 2`
- [ ] Jira integration escribe en `.cortex/vault/hu/`

#### Rollback

- Permitir que setup detecte repos legacy y ofrezca modo de inicialización legacy solo durante la transición

---

### Fase 5 — Migrar IDE, MCP y WebGraph

**Semaforo:** 🟡 Amarillo  
**Objetivo:** Alinear los consumidores externos y de integración con el nuevo modelo de workspace.

#### 5.1 IDE

**Archivos impactados:**

```
cortex/ide/__init__.py                  (discovery con WorkspaceLayout)
cortex/ide/base.py                      (paths con WorkspaceLayout)
cortex/ide/adapters/vscode.py
cortex/ide/adapters/cursor.py
cortex/ide/adapters/claude_code.py
cortex/ide/adapters/claude_desktop.py
cortex/ide/adapters/opencode.py
cortex/ide/adapters/windsurf.py
cortex/ide/adapters/zed.py
cortex/ide/adapters/antigravity.py
cortex/ide/adapters/hermes.py
cortex/ide/adapters/pi.py
cortex/ide/prompts.py                    (paths en contenido de prompts)
```

**Requisitos:**

- `_find_project_root()` debe usar `WorkspaceLayout.discover()`
- Las referencias fuente deben apuntar a `.cortex/skills/...`
- Las referencias a subagentes deben apuntar a `.cortex/subagents/...`
- Los prompts y mensajes deben dejar de instruir layout legacy
- MCP server path debe apuntar a `.cortex/config.yaml`

#### 5.2 MCP

**Archivos impactados:**

```
cortex/mcp/server.py                    (config_path, logs_dir, subagents_dir)
```

**Requisitos:**

- Descubrir `.cortex/config.yaml` via `WorkspaceLayout`
- Logs en `.cortex/logs/` (ya es así, pero vía WorkspaceLayout)
- Subagents en `.cortex/subagents/` (ya es así, pero vía WorkspaceLayout)
- Mantener delegación funcional en modo legacy durante la transición

#### 5.3 WebGraph

**Archivos impactados:**

```
cortex/webgraph/cli.py
cortex/webgraph/config.py               (default_path via WorkspaceLayout)
cortex/webgraph/federation.py
cortex/webgraph/setup.py                 (install_webgraph via WorkspaceLayout)
cortex/webgraph/cache.py
cortex/webgraph/semantic_source.py
cortex/webgraph/episodic_source.py
cortex/webgraph/server.py
```

**Requisitos:**

- WebGraph sigue en `.cortex/webgraph/` (sin cambio de ubicación)
- Pero la resolución de paths debe pasar por `WorkspaceLayout`
- `doctor` y `serve` deben resolver el nuevo layout

#### Gate de salida

- [ ] Al menos un smoke test real por cada integración principal:
  - Cursor
  - VSCode (Cline/Roo)
  - OpenCode
  - MCP delegation
  - WebGraph serve/export/doctor
- [ ] IDEs descubren el proyecto via `WorkspaceLayout.discover()`
- [ ] MCP arranca y encuenta config, subagentes y logs en `.cortex/`

#### Rollback

- Mantener compatibilidad de lectura a rutas legacy en integraciones hasta la release de retiro

---

### Fase 6 — Migrar Diagnóstico, Política Git, Documentación y Tests

**Semaforo:** 🟡 Amarillo  
**Objetivo:** Cerrar el refactor de forma verificable y coherente para usuarios nuevos y existentes.

#### 6.1 Diagnóstico y hinting

**Archivos impactados:**

```
cortex/doctor.py
cortex/tutor/hint.py
cortex/enterprise/reporting.py
```

**Requisitos:**

- `doctor` debe validar el nuevo layout correctamente (`.cortex/config.yaml`, `.cortex/vault/`, `.cortex/org.yaml`, etc.)
- `doctor` debe funcionar en repos legacy (detectar y reportar ambos layouts)
- `hint` debe inspeccionar `.cortex/config.yaml`, `.cortex/vault/`, `.cortex/org.yaml`
- `reporting` debe reportar paths del nuevo layout

#### 6.2 Política Git

**Archivos impactados:**

```
cortex/git_policy.py
.gitignore
```

**Nuevo `.gitignore` con compatibilidad dual:**

```gitignore
# Cortex local state (nuevo layout)
.cortex/memory/
.cortex/enterprise-memory/
.cortex/webgraph/cache/
.cortex/logs/

# Cortex vault policy (nuevo layout)
# Track: .cortex/vault/specs, .cortex/vault/decisions, .cortex/vault/runbooks
# Track: .cortex/vault/hu, .cortex/vault/incidents
.cortex/vault/sessions/

# Cortex local state (legacy layout - compatibilidad)
.memory/
*.chroma/
vault/sessions/
.cortex/logs/
.cortex/webgraph/cache/
```

#### 6.3 Documentación

**Archivos impactados:**

```
docs/guides/configuration-reference.md
docs/guides/enterprise-vault.md
docs/guides/getting-started.md
docs/guides/pipeline-custom-modules.md
docs/guides/pipeline-setup.md
docs/guides/vault-structure.md
docs/ops/Cortex-CI-CD-Infrastructure.md
docs/ops/Cortex-Enterprise-Runbook.md
docs/ops/Cortex-Git-Vault-Policy.md
README.md
CONTRIBUTING.md
```

**Requisitos:**

- La documentación nueva debe explicar el layout nuevo
- Si se menciona el legacy, debe ser explícitamente como compatibilidad o migración
- Los comandos de ejemplo deben usar el nuevo layout

#### 6.4 Tests

**Todos los archivos de tests impactados:**

```
# Tests de setup e integración (CRÍTICOS)
tests/integration/setup/test_cortex_workspace.py
tests/integration/setup/test_detector.py
tests/integration/setup/test_orchestrator.py
tests/integration/setup/test_templates.py
tests/integration/mcp/test_server.py
tests/integration/enterprise/test_promotion_e2e.py
tests/integration/enterprise/test_retrieval_e2e.py

# Tests unitarios de CLI
tests/unit/cli/test_main.py

# Tests unitarios de enterprise (8 archivos)
tests/unit/enterprise/test_config.py
tests/unit/enterprise/test_core_retrieve_scope.py
tests/unit/enterprise/test_enterprise_presets.py
tests/unit/enterprise/test_enterprise_setup.py
tests/unit/enterprise/test_promotion_records.py
tests/unit/enterprise/test_promotion_rules.py
tests/unit/enterprise/test_reporting.py
tests/unit/enterprise/test_retrieval_performance.py
tests/unit/enterprise/test_retrieval_service.py
tests/unit/enterprise/test_sources.py

# Tests unitarios de webgraph (5 archivos)
tests/unit/webgraph/test_service.py
tests/unit/webgraph/test_setup.py
tests/unit/webgraph/test_webgraph_openers.py
tests/unit/webgraph/test_webgraph_server.py
tests/unit/webgraph/test_federation.py

# Tests unitarios adicionales (no mencionados en documento original)
tests/unit/episodic/test_memory_store.py       ← persist_dir hardcodeado
tests/unit/retrieval/test_hybrid_search.py     ← fixture con layout legacy
tests/unit/context_enricher/test_*.py (6 archivos) ← fixtures con layout legacy
tests/unit/test_mcp_server.py                  ← config.yaml en cwd
tests/unit/test_ide_adapters.py                ← .cortex/ discovery
tests/unit/test_ide_module.py                  ← inject/uninstall paths
tests/unit/test_runtime_context.py              ← resolve_episodic_persist_dir
tests/unit/test_doctor_enterprise_governance.py  ← .cortex/org.yaml validation
tests/unit/test_documentation.py                ← vault path

# Tests de webgraph
tests/unit/retrieval/test_adaptive_rrf.py
tests/unit/retrieval/test_rrf_properties.py
tests/unit/semantic/test_markdown_parser.py
tests/unit/semantic/test_vault_reader.py

# Conftest global
tests/conftest.py                              ← fixtures con tmp_path / "vault"
```

**Requisitos de la suite:**

- Tests deben cubrir: discovery layout nuevo, compatibilidad legacy, setup nuevo, runtime nuevo, IDE y MCP, WebGraph, enterprise promotion/reporting
- Se debe agregar un fixture de `workspace_layout` en `conftest.py` en Fase 1 (no Fase 6)
- Tests legacy no se eliminan hasta Fase 8

#### Gate de salida

- [ ] Suite verde en los frentes críticos con nuevo layout
- [ ] Suite verde en los frentes críticos con legacy layout
- [ ] Docs y `doctor` consistentes con el layout nuevo

#### Rollback

- Mantener notas de compatibilidad legacy en docs mientras dure la transición

---

### Fase 7 — Activar el Layout Nuevo por Defecto

**Semaforo:** 🟢 Verde  
**Objetivo:** Convertir el layout nuevo en la ruta oficial y default de Cortex.

#### Alcance

- Setup nuevo emite layout nuevo exclusivamente
- CLI comunica layout nuevo
- `WorkspaceLayout.discover()` prioriza layout nuevo
- Docs principales muestran layout nuevo
- Compatibilidad legacy sigue existiendo pero ya no es el path principal

#### Gate de salida

- [ ] El producto puede ser usado por un repo nuevo sin tocar ninguna ruta legacy
- [ ] Todos los comandos CLI funcionan en un repo nuevo
- [ ] Jira integration funciona en layout nuevo
- [ ] Enterprise retrieval funciona en layout nuevo
- [ ] WebGraph funciona en layout nuevo

#### Rollback

- Si aparece una regresión severa, mantener el layout nuevo como experimental y no retirar compatibilidad legacy

---

### Fase 8 — Retirar Compatibilidad Legacy

**Semaforo:** 🔴 Rojo  
**Objetivo:** Eliminar deuda de compatibilidad una vez estabilizado el sistema.

#### Condiciones mínimas para autorizarla

- Al menos 1-2 versiones de convivencia
- Zero blockers en IDE/MCP/WebGraph
- Guía de migración publicada y validada
- Evidencia de que el layout nuevo es el dominante

#### Alcance

- Remover discovery legacy de `WorkspaceLayout.discover()`
- Remover mensajes legacy
- Remover tests legacy
- Remover fallback de paths legacy
- Remover `DeprecationWarning` de `project_root`

#### Riesgos

- Bloquear repos inicializados antes del cambio
- Romper integraciones externas que aún dependan del layout anterior

#### Gate de salida

- [ ] Compatibilidad legacy puede eliminarse sin dejar casos de uso productivos fuera

#### Rollback

- No retirar legacy si alguna integración principal todavía depende de él

---

## 10. Cambios Exactos Esperados por Area

### 10.1 CLI

**Archivo:** `cortex/cli/main.py`

**Cambios esperados:**

- `_load_memory()` debe usar `WorkspaceLayout.discover()` para encontrar config
- Dejar de asumir `config.yaml` en `Path.cwd()`
- Dejar de asumir `.cortex/org.yaml` en `Path.cwd() / ".cortex"`
- Actualizar `-project-root` flags para resolver via `WorkspaceLayout`
- Los defaults de `install-skills` apuntan a `.cortex/skills/` (ya es así)
- Comandos `verify-docs`, `validate-docs`, `index-docs` deben usar layout para resolver `vault`
- Comandos enterprise (`promote-knowledge`, `review-knowledge`, `sync-enterprise-vault`, `memory-report`, `org-config`) deben usar `WorkspaceLayout`
- El argumento `--vault` de comandos debe aceptar tanto paths absolutos como relativos al `workspace_root`

### 10.2 Setup Orchestrator

**Archivos:**

```
cortex/setup/orchestrator.py
cortex/setup/templates.py
cortex/setup/cortex_workspace.py
cortex/setup/cold_start.py
cortex/setup/detector.py
```

**Cambios esperados:**

- `_create_directories()` debe crear dentro de `.cortex/`
- `_create_config()` debe escribir `.cortex/config.yaml`
- Los valores relativos de config deben apuntar a rutas relativas al workspace: `persist_dir: memory`, `vault_path: vault`
- `_create_vault_docs()` debe escribir dentro de `.cortex/vault/`
- `_create_enterprise_vault()` debe escribir dentro de `.cortex/vault-enterprise/`
- `_create_enterprise_org_config()` debe escribir dentro de `.cortex/org.yaml` (sin cambio de ubicación)
- `_create_enterprise_workspace()` debe incluir `layout_version: 2`
- `_create_workflows()` sigue escribiendo en `.github/workflows/` en raíz
- `_create_devsecdocops_script()` debe escribir en `.cortex/scripts/`
- `_create_agent_guidelines()` escribe en `.cortex/` (ya es así)
- `_install_skills()` instala en `.cortex/skills/` (ya es así)
- `_init_memory()` debe usar `WorkspaceLayout` para resolver vault y memory paths
- `cold_start.py` debe usar `repo_root` (no `workspace_root`) para `git log`

### 10.3 Runtime de Memoria

**Archivos:**

```
cortex/core.py
cortex/runtime_context.py
cortex/episodic/memory_store.py
cortex/semantic/vault_reader.py
```

**Cambios esperados:**

- `AgentMemory.__init__` recibe `workspace_root` de `WorkspaceLayout` en vez de derivarlo de `config_path.parent`
- La variable `self.project_root` pasa a `self.workspace_root` con DeprecationWarning
- `self.project_id` se deriva de `workspace_root.name` (que es `.cortex`) y se usa `repo_root.name` como fallback
- `resolve_episodic_persist_dir()` recibe `workspace_root` en vez de `project_root`
- `VaultReader` recibe `vault_path` resuelto desde `WorkspaceLayout.vault_path`
- `_INDEX_FILE` (`.cortex_index.json`) se ubica dentro de `.cortex/vault/`

### 10.4 Enterprise

**Archivos:**

```
cortex/enterprise/config.py
cortex/enterprise/models.py
cortex/enterprise/knowledge_promotion.py
cortex/enterprise/reporting.py
cortex/enterprise/retrieval_service.py
cortex/enterprise/sources.py
```

**Cambios esperados:**

- `DEFAULT_ENTERPRISE_CONFIG_PATH` cambia de `Path(".cortex") / "org.yaml"` a `WorkspaceLayout.org_config_path`
- `resolve_enterprise_vault_path()` usa `workspace_root / "vault-enterprise"` (y el valor relativo es `vault-enterprise`)
- `resolve_enterprise_memory_path()` usa `workspace_root / "enterprise-memory"` (y el valor relativo es `enterprise-memory`)
- `PromotionPaths.enterprise_vault` se resuelve contra `workspace_root`
- `PromotionPaths.records_path` se convierte en `enterprise_vault / "promotion" / "records.jsonl"` (sin `.cortex` intermedio)
- `EnterpriseReportingService._local_source()` usa `WorkspaceLayout.vault_path`
- `EnterpriseRetrievalService` recibe `workspace_root` en vez de `project_root`

### 10.5 IDE

**Archivos:**

```
cortex/ide/__init__.py
cortex/ide/base.py
cortex/ide/adapters/*.py (9 archivos)
cortex/ide/prompts.py
cortex/ide/registry.py
```

**Cambios esperados:**

- `_find_project_root()` delega en `WorkspaceLayout.discover()`
- Los adapters reciben `workspace_root` en vez de `project_root`
- Los prompts generados referencian `.cortex/skills/...` y `.cortex/subagents/...`
- MCP config apunta a `.cortex/config.yaml`

### 10.6 MCP

**Archivo:** `cortex/mcp/server.py`

**Cambios esperados:**

- Línea ~94: `config_path = project_root / "config.yaml"` → usar `WorkspaceLayout.config_path`
- Línea ~87: `log_dir = project_root / ".cortex" / "logs"` → usar `WorkspaceLayout.logs_dir`
- Línea ~300: `subagent_file = project_root / ".cortex" / "subagents" / ...` → usar `WorkspaceLayout.subagents_dir`
- El constructor recibe `repo_root` y deriva internamente via `WorkspaceLayout`

### 10.7 WebGraph

**Archivos:**

```
cortex/webgraph/config.py         → default_path via WorkspaceLayout
cortex/webgraph/service.py        → project_root → repo_root, workspace_root via WorkspaceLayout
cortex/webgraph/cli.py            → resolver con WorkspaceLayout
cortex/webgraph/federation.py    → resolver con WorkspaceLayout
cortex/webgraph/setup.py          → install via WorkspaceLayout
cortex/webgraph/cache.py          → cache_dir via WorkspaceLayout
cortex/webgraph/semantic_source.py → vault_path via WorkspaceLayout
cortex/webgraph/episodic_source.py → persist_dir via WorkspaceLayout
cortex/webgraph/server.py         → resolver con WorkspaceLayout
```

**Nota:** WebGraph **no cambia de ubicación** — ya está en `.cortex/webgraph/`. Lo que cambia es cómo se resuelven sus paths.

### 10.8 Diagnóstico y Política Git

**Archivos:**

```
cortex/doctor.py
cortex/tutor/hint.py
cortex/git_policy.py
.gitignore
```

**Cambios esperados:**

- `doctor` valida `.cortex/config.yaml`, `.cortex/vault/`, `.cortex/org.yaml`, `.cortex/memory/`
- `doctor` reporta layout detectado (nuevo vs legacy)
- `ProjectState.detect()` usa `WorkspaceLayout.discover()`
- `git_policy.py` actualiza `RECOMMENDED_GITIGNORE_PATTERNS` para el nuevo layout
- `.gitignore` incluye patrones para ambos layouts

### 10.9 Tests (Fixture Global)

**Archivo:** `tests/conftest.py`

**Cambios esperados:**

- Agregar fixture `workspace_layout` que crea un layout nuevo con `tmp_path`
- Agregar fixture `legacy_workspace` que crea un layout legacy con `tmp_path`
- Los tests existentes se migran gradualmente a usar estos fixtures

---

## 11. Validación del Acceso y Funcionalidad Post-Refactor

### 11.1 Vault Enterprise accesible y actualizable

**Confirmado:** ✅ El vault enterprise pasará de `vault-enterprise/` a `.cortex/vault-enterprise/`. Es un directorio de archivos Markdown sin permisos. Cualquier desarrollador puede:

- `cortex promote-knowledge --apply` → escribir en `.cortex/vault-enterprise/`
- `cortex review-knowledge` → aprobar/rechazar
- `cortex sync-enterprise-vault` → indexar
- `cortex search --scope enterprise` → buscar
- Edición directa de archivos `.md`

La cadena de acceso es `WorkspaceLayout.enterprise_vault_path` → `.cortex/vault-enterprise/`. Sin cambios funcionales, solo de ruta.

### 11.2 Conexión Jira funciona sin cambios

**Confirmado:** ✅ La integración Jira es ortogonal al layout:

- **Lectura:** `JiraProvider.get_item()` → API HTTP remota (no depende de paths locales)
- **Escritura:** `WorkItemService.import_item()` → `vault_path / "hu"` → `.cortex/vault/hu/`
- **Config:** Leída de `.cortex/config.yaml` vía `WorkspaceLayout.config_path`

El único cambio es la resolución del path donde se escriben las HUs.

### 11.3 Setup crea todo en `.cortex/` y un desarrollador puede leer todo

**Confirmado:** ✅ Con la salvedad de `.github/workflows/` que debe quedar en raíz:

| Comando | Todo dentro de `.cortex/` | Excepción |
|---|---|---|
| `cortex setup agent` | ✅ Sí | Ninguna |
| `cortex setup pipeline` | ✅ Sí | `.github/workflows/` (GitHub lo exige en raíz) |
| `cortex setup full` | ✅ Sí | `.github/workflows/` |
| `cortex setup enterprise` | ✅ Sí | Ninguna |
| `cortex setup webgraph` | ✅ Sí | Ninguna (ya está en `.cortex/webgraph/`) |

Dentro de `.cortex/` no hay archivos ocultos. Todo es accesible:

```
.cortex/
├── AGENT.md              ← legible
├── config.yaml           ← legible, editable
├── org.yaml              ← legible, editable
├── system-prompt.md      ← legible
├── workspace.yaml         ← legible, editable
├── vault/                ← navegable
├── vault-enterprise/     ← navegable
├── memory/               ← accesible (ChromaDB)
├── skills/               ← legible
├── subagents/            ← legible
├── webgraph/             ← navegable
├── scripts/              ← legible, ejecutable
└── logs/                 ← accesible
```

---

## 12. Matriz de Riesgos

| Riesgo | Severidad | Probabilidad | Mitigación |
|---|---|---:|---|
| Duplicación de prefijos `.cortex/.cortex/...` | Alta | Alta | Fijar `workspace_root` como base única de resolución; tests exhaustivos |
| Setup genera nuevo layout pero runtime sigue leyendo legacy | Alta | Alta | Fases 1-3 antes de writers exclusivos |
| IDE no descubre el proyecto | Alta | Media | Migrar `ide/__init__.py` con `WorkspaceLayout.discover()` temprano |
| MCP arranca pero no encuentra subagentes | Alta | Media | Smoke test real de delegación MCP |
| WebGraph sigue escribiendo en rutas legacy | Media | Alta | Incluir WebGraph en contrato de WorkspaceLayout |
| `doctor` y `hint` reportan falso | Media | Alta | Migrarlos antes de activar default nuevo |
| Promotion records quedan repartidos | Media | Media | `.cortex/vault-enterprise/promotion/` sin `.cortex/` intermedio |
| Tests legacy bloquean adopción | Media | Alta | Agregar fixture `workspace_layout` en Fase 1 |
| `git log` en cold start usa workspace_root en vez de repo_root | Media | Media | Pasar `repo_root` explícitamente a `run_cold_start()` |
| Vault index `.cortex_index.json` se pierde al mover vault | Baja | Media | Migrar como parte de `VaultReader` vía `WorkspaceLayout.vault_index_path` |
| `.cortex/` no se oculta en Windows | Baja | Baja | Documentar; no es un problema funcional, todo es accesible por diseño |

---

## 13. Matriz de Validación Mínima

Antes de considerar completa la migración, se deben validar como mínimo estos escenarios:

1. `cortex setup agent` en repo vacío crea layout nuevo completo dentro de `.cortex/`
2. `cortex setup enterprise` en repo nuevo crea layout nuevo completo
3. `cortex doctor` funciona en repo nuevo
4. `cortex doctor` funciona en repo legacy
5. `remember`, `save-session`, `create-spec`, `sync-vault` funcionan en repo nuevo
6. `search --scope local` funciona en repo nuevo
7. `search --scope enterprise` funciona en repo nuevo
8. `promote-knowledge` y `review-knowledge` funcionan en repo nuevo
9. `memory-report` funciona en repo nuevo
10. `cortex hu import PROJ-123` funciona (Jira)
11. `cortex install-ide --ide cursor` funciona en repo nuevo
12. `cortex install-ide --ide opencode` funciona en repo nuevo
13. MCP puede delegar subagentes en repo nuevo
14. `cortex webgraph doctor` funciona en repo nuevo
15. `cortex webgraph serve` funciona en repo nuevo
16. `cortex context --files ...` funciona en repo nuevo
17. Un repo legacy inicializado previamente sigue siendo legible
18. `cold_start` (git indexing) funciona en repo nuevo (usando repo_root)
19. Un desarrollador puede entrar a `.cortex/` y leer todos los archivos

---

## 14. Recomendación Final

La refactorización del workspace **es conveniente** y **debe ejecutarse como migración de arquitectura**, no como rename masivo de paths.

La regla clave para que salga bien es:

> **Primero compatibilidad y resolvedor central, después writers nuevos, después activación default, y recién mucho más tarde retiro legacy.**

El contenedor `.cortex/` es la mejor elección porque:
- Ya existe en el layout actual (los archivos ya dentro no se mueven)
- Es reconocible como marca del proyecto
- En Unix se oculta por convención (punto inicial); en Windows es accesible por diseño
- No produce anidación `.cortex/.cortex/`
- Un desarrollador que entre a `.cortex/` ve todo: config, vault, skills, scripts

**La única excepción es `.github/workflows/`**, que debe permanecer en raíz por requisito de GitHub Actions. Esto no es negociable y no afecta la experiencia del desarrollador.

---

## 15. Checklist de Cierre

- [ ] `WorkspaceLayout` implementado con discovery, resolución y compatibilidad legacy
- [ ] El contrato de layout está congelado y sin contradicciones
- [ ] Los lectores soportan layout nuevo y legacy
- [ ] El runtime crítico usa el resolvedor
- [ ] `AgentMemory.workspace_root` funciona correctamente
- [ ] Setup escribe layout nuevo
- [ ] IDE y MCP usan rutas nuevas
- [ ] WebGraph usa rutas nuevas
- [ ] `doctor`, `hint`, reporting y `.gitignore` están alineados
- [ ] La documentación explica el layout nuevo
- [ ] La suite cubre nuevo + legacy
- [ ] El layout nuevo puede activarse por defecto
- [ ] La compatibilidad legacy queda programada para retiro posterior, no inmediato
- [ ] Jira integration funciona en layout nuevo
- [ ] Vault enterprise es accesible y modificable dentro de `.cortex/`
- [ ] Cold start usa `repo_root` para `git log`
- [ ] `.github/workflows/` se crea en raíz, no dentro de `.cortex/`
- [ ] No hay archivos ocultos adicionales dentro de `.cortex/`
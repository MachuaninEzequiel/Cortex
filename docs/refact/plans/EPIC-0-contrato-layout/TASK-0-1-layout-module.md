# TASK 0-1 — Crear módulo workspace con API de WorkspaceLayout

**Epic:** EPIC 0  
**Dependencias:** Ninguna  
**Rama:** `refac/epic-0-task-1-layout-module`

## Objetivo

Crear el paquete `cortex/workspace/` con la clase `WorkspaceLayout` que define el contrato central de resolución de rutas.

## Archivos a crear

- `cortex/workspace/__init__.py` — Exportar `WorkspaceLayout`
- `cortex/workspace/layout.py` — Implementación completa

## Implementación

`WorkspaceLayout` debe exponer:

```python
class WorkspaceLayout:
    # Discovery
    @classmethod
    def discover(cls, start: Path) -> "WorkspaceLayout"
    @classmethod
    def from_repo_root(cls, repo_root: Path) -> "WorkspaceLayout"

    # Roots
    repo_root: Path
    workspace_root: Path       # = repo_root / ".cortex"
    is_legacy_layout: bool
    is_new_layout: bool

    # Config
    config_path: Path          # workspace_root / "config.yaml"
    org_config_path: Path      # workspace_root / "org.yaml"

    # Vault
    vault_path: Path           # workspace_root / "vault"
    enterprise_vault_path: Path  # workspace_root / "vault-enterprise"

    # Memory
    episodic_memory_path: Path   # workspace_root / "memory"
    enterprise_memory_path: Path # workspace_root / "enterprise-memory"

    # Assets
    skills_dir: Path            # workspace_root / "skills"
    subagents_dir: Path         # workspace_root / "subagents"
    agent_guidelines_path: Path # workspace_root / "AGENT.md"
    system_prompt_path: Path    # workspace_root / "system-prompt.md"
    workspace_yaml_path: Path   # workspace_root / "workspace.yaml"

    # WebGraph
    webgraph_dir: Path          # workspace_root / "webgraph"
    webgraph_config_path: Path
    webgraph_workspace_path: Path
    webgraph_cache_dir: Path

    # Runtime
    logs_dir: Path              # workspace_root / "logs"
    scripts_dir: Path           # workspace_root / "scripts"

    # CI/CD (fuera de .cortex)
    workflows_dir: Path         # repo_root / ".github" / "workflows"

    # Promotion
    promotion_records_path: Path # enterprise_vault_path / "promotion" / "records.jsonl"

    # Vault
    vault_index_path: Path      # vault_path / ".cortex_index.json"

    # Git
    gitignore_path: Path         # repo_root / ".gitignore"

    # Resolution
    def resolve_workspace_relative(self, value: str | Path) -> Path

    # Legacy compatibility
    def legacy_config_path(self) -> Path    # repo_root / "config.yaml"
    def legacy_vault_path(self) -> Path    # repo_root / "vault"
    def legacy_memory_path(self) -> Path   # repo_root / ".memory"
```

## Reglas

- `discover()` busca desde `start` hacia arriba en los parents
- Precedencia: workspace.yaml con layout_version≥2 → .cortex/config.yaml → config.yaml en raíz → bootstrap
- `from_repo_root()` construye directamente sin discovery
- Todos los paths son `Path` objects absolutos
- `is_legacy_layout` = True si se encontró layout viejo
- `is_new_layout` = True si se encontró layout nuevo

## Checklist

- [ ] `cortex/workspace/__init__.py` creado
- [ ] `cortex/workspace/layout.py` creado con clase `WorkspaceLayout`
- [ ] Todos las propiedades del contrato implementadas
- [ ] `discover()` implementa precedencia de 3 niveles
- [ ] `from_repo_root()` construye layout directamente
- [ ] `resolve_workspace_relative()` funciona
- [ ] `legacy_*` paths funcionan
- [ ] Tipo `dict` o `dataclass` en vez de clase con `@property` — lo que sea más idiomático
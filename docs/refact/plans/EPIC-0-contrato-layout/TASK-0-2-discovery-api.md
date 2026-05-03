# TASK 0-2 — Implementar discovery con precedencia

**Epic:** EPIC 0  
**Dependencias:** TASK 0-1  
**Rama:** `refac/epic-0-task-2-discovery-api`

## Objetivo

Implementar el método `WorkspaceLayout.discover()` con la precedencia de 3 niveles definida en el contrato.

## Lógica de Discovery

```
1. Si existe start/.cortex/workspace.yaml con layout_version >= 2 → nuevo layout
2. Si existe start/.cortex/config.yaml → nuevo layout (setup en progreso)
3. Si existen start/config.yaml o start/.cortex/ (sin config.yaml dentro) → legacy layout
4. Si no existe ninguno → bootstrap limpio
```

En los casos 1-2: `workspace_root = repo_root / ".cortex"`, paths relativos contra `workspace_root`
En caso 3: `workspace_root = repo_root`, paths relativos contra `repo_root` (comportamiento legacy)
En caso 4: igual que caso 1, pero `is_new_layout = True` y `is_legacy_layout = False`

## Implementación

```python
@classmethod
def discover(cls, start: Path) -> "WorkspaceLayout":
    current = start.resolve()
    for parent in [current] + list(current.parents):
        # Caso 1: layout_version >= 2
        ws_yaml = parent / ".cortex" / "workspace.yaml"
        if ws_yaml.exists():
            data = yaml.safe_load(ws_yaml.read_text()) or {}
            if data.get("layout_version", 1) >= 2:
                return cls.from_repo_root(parent)
        
        # Caso 2: config.yaml dentro de .cortex/
        cortex_config = parent / ".cortex" / "config.yaml"
        if cortex_config.exists():
            return cls.from_repo_root(parent)
        
        # Caso 3: layout legacy
        root_config = parent / "config.yaml"
        cortex_dir = parent / ".cortex"
        git_dir = parent / ".git"
        if root_config.exists() or (cortex_dir.exists() and git_dir.exists()):
            # Es un repo con layout legacy
            layout = cls.from_repo_root(parent)
            layout._is_legacy = True
            layout._is_new = False
            # Override: workspace_root = repo_root en legacy
            layout.workspace_root = parent
            return layout
    
    # Caso 4: bootstrap limpio - asumir directorio actual
    return cls.from_repo_root(start.resolve())
```

## Checklist

- [ ] `discover()` implementa los 4 niveles de precedencia
- [ ] Distinción correcta entre `is_legacy_layout` e `is_new_layout`
- [ ] En legacy layout, `workspace_root = repo_root` y los paths apuntan a raíz
- [ ] En nuevo layout, `workspace_root = repo_root / ".cortex"`
- [ ] Búsqueda hacia arriba en parents hasta encontrar proyecto o llegar a raíz del filesystem
- [ ] Manejo de caso donde `start` es un subdirectorio del proyecto
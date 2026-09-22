# Estructura — `cortex/mcp/tools`

## Para qué existe esta carpeta

(sin docstring de paquete; reexportes)

## Árbol interno (código, sin `__pycache__`)

```
tools/
├── __init__.py
├── documenter.py
├── search.py
├── sessions.py
└── workspace.py
```

## Archivos Python cubiertos aquí

| Archivo | Líneas | Síntesis observada |
|---|---:|---|
| `cortex/mcp/tools/__init__.py` | 1 | reexportes / marcador de paquete |
| `cortex/mcp/tools/documenter.py` | 415 | Handlers MCP del dominio spec/proposal/documenter (mixín de CortexMCPServer). |
| `cortex/mcp/tools/search.py` | 239 | Handlers MCP del dominio búsqueda/contexto (mixín de CortexMCPServer). |
| `cortex/mcp/tools/sessions.py` | 523 | Handlers MCP del dominio sesiones/checkpoints/tasks (mixín de CortexMCPServer). |
| `cortex/mcp/tools/workspace.py` | 204 | Handlers MCP del dominio workspace/docs/HU (mixín de CortexMCPServer). |

## Relaciones de la carpeta

### Recibe de (unión de imports `cortex.*` de los módulos de este nivel)

- `cortex.mcp.schemas`
- `cortex.mcp.vault_adapter`
- `cortex.models`
- `cortex.security.paths`

### Envía a (módulos `cortex.*` que importan a este nivel)

- `cortex.mcp.server`

---
Fuente: árbol de `cortex/` + AST de imports. No se usó documentación previa.

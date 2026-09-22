# Estructura — `cortex/mcp`

## Para qué existe esta carpeta

(sin docstring)

## Árbol interno (código, sin `__pycache__`)

```
mcp/
├── tools/
│   ├── __init__.py
│   ├── documenter.py
│   ├── search.py
│   ├── sessions.py
│   └── workspace.py
├── _subprocess.py
├── schemas.py
├── server.py
└── vault_adapter.py
```

## Archivos Python cubiertos aquí

| Archivo | Líneas | Síntesis observada |
|---|---:|---|
| `cortex/mcp/_subprocess.py` | 189 | Defensive subprocess helpers for the Cortex MCP server. |
| `cortex/mcp/schemas.py` | 1079 | Definiciones (schemas) de las tools MCP — fuente única. |
| `cortex/mcp/server.py` | 492 | CortexMCPServer |
| `cortex/mcp/tools/__init__.py` | 1 | reexportes / marcador de paquete |
| `cortex/mcp/tools/documenter.py` | 415 | Handlers MCP del dominio spec/proposal/documenter (mixín de CortexMCPServer). |
| `cortex/mcp/tools/search.py` | 239 | Handlers MCP del dominio búsqueda/contexto (mixín de CortexMCPServer). |
| `cortex/mcp/tools/sessions.py` | 523 | Handlers MCP del dominio sesiones/checkpoints/tasks (mixín de CortexMCPServer). |
| `cortex/mcp/tools/workspace.py` | 204 | Handlers MCP del dominio workspace/docs/HU (mixín de CortexMCPServer). |
| `cortex/mcp/vault_adapter.py` | 29 | Adaptador ``VaultLike`` mínimo sobre un path del workspace. |

## Relaciones de la carpeta

### Recibe de (unión de imports `cortex.*` de los módulos de este nivel)

- `cortex.autopilot.mcp_tools`
- `cortex.autopilot.service`
- `cortex.core`
- `cortex.mcp.schemas`
- `cortex.mcp.tools.documenter`
- `cortex.mcp.tools.search`
- `cortex.mcp.tools.sessions`
- `cortex.mcp.tools.workspace`
- `cortex.session.models`
- `cortex.workspace.layout`

### Envía a (módulos `cortex.*` que importan a este nivel)

- `cortex.mcp.server`
- `cortex.mcp.tools.sessions`
- `cortex.mcp.tools.workspace`

---
Fuente: árbol de `cortex/` + AST de imports. No se usó documentación previa.

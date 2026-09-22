# cortex/handoff.py

## Qué tiene adentro

- `ArtifactProduced`: path, action `created|modified|deleted|renamed`, líneas.
- `AgentHandoff`: contrato YAML legado entre agentes (`agent`, `status` `complete|partial|blocked`, claims, artifacts). Métodos `to_yaml` / `from_yaml` en el resto del archivo.

El propio docstring del módulo lo marca **deprecated** (Phase 02 Pluggable Middle). El estado canónico es `SessionRecord` + checkpoints. Se conserva para IDEs single-agent (p.ej. Codex) y para el documenter en modo YAML legado. Código nuevo no debe depender de este módulo.

## Para qué sirve

Serializar un pase de postas agente→agente cuando no hay sesión MCP.

## Relaciones

### Recibe de

- Solo pydantic + typing.

### Envía a

- `documenter.reconstruction` construye un `AgentHandoff` sintético (visto en docstring de `documenter/__init__.py`).
- Consumidores legacy del YAML.

### Notas de implementación observadas en el código

- Permisivo en listas opcionales; estricto en `agent` y `status`.

---
Fuente: lectura de `cortex/handoff.py`. No se usó documentación previa.

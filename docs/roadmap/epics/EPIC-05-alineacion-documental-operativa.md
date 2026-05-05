# EPIC-05 - Alineacion documental operativa

> Importante: marcar cada tarea completada en este archivo.
> Al cerrar la epica, completar [EPIC-05-alineacion-documental-operativa-REALIZACION.md](./EPIC-05-alineacion-documental-operativa-REALIZACION.md).

## Objetivo

Hacer que la documentacion operativa de mayor consumo describa el contrato real de setup, layout, config y vault sin introducir mas drift.

## Historia de usuario 1

**Como** usuario nuevo de Cortex  
**Quiero** que el README y getting-started describan el setup real  
**Para** no seguir instrucciones que contradigan el layout actual.

### Tarea 5.1 - Alinear README y getting-started con el setup real

**Archivos principales a cambiar**

- `README.md`
- `docs/guides/getting-started.md`

**Dependencias que deben revisarse o corregirse por arrastre**

- `cortex/setup/orchestrator.py` - archivos y directorios creados por setup
- `cortex/setup/cortex_workspace.py` - contenido inicial de `.cortex/`
- `cortex/workspace/layout.py` - contrato new vs legacy
- `config.yaml` - defaults operativos visibles
- `docs/vision/ARQUITECTURA-GLOBAL-CORTEX.md` - topologia explicada a nivel alto

**Checklist**

- [x] Corregir en `README.md` donde vive `config.yaml` segun layout nuevo y legacy.
- [x] Corregir en `README.md` donde viven `vault`, `memory` y `workspace.yaml`.
- [x] Reescribir `docs/guides/getting-started.md` para que no asuma solo layout legacy.
- [x] Verificar que los comandos de setup citados coincidan con el comportamiento actual del CLI.

## Historia de usuario 2

**Como** usuario que necesita configurar Cortex  
**Quiero** una referencia de config que refleje el schema real  
**Para** no usar campos inexistentes ni defaults viejos.

### Tarea 5.2 - Alinear referencia de configuracion y pipeline

**Archivos principales a cambiar**

- `docs/guides/configuration-reference.md`
- `docs/guides/pipeline-setup.md`

**Dependencias que deben revisarse o corregirse por arrastre**

- `cortex/core.py` - modelos `CortexConfig`, `EpisodicConfig`, `SemanticConfig`, `RetrievalConfig`, `LLMConfig`
- `config.yaml` - ejemplo vivo del repo
- `cortex/enterprise/config.py` - contracto real de `org.yaml`
- `cortex/setup/templates.py` - renderer del config generado por setup
- `docs/guides/enterprise-vault.md`

**Checklist**

- [x] Eliminar de `configuration-reference.md` campos que ya no existan en el schema real.
- [x] Agregar o corregir campos que si existen y hoy no estan documentados.
- [x] Corregir `pipeline-setup.md` para que la configuracion del pipeline coincida con el config actual.
- [x] Revisar que ejemplos YAML y nombres de claves no contradigan `config.yaml` ni `org.yaml`.

## Historia de usuario 3

**Como** usuario que consulta arquitectura y ejemplos  
**Quiero** que las guias de vault, enterprise y ejemplos de uso reflejen el contrato actual  
**Para** no propagar modelos mentales viejos en los documentos de apoyo.

### Tarea 5.3 - Alinear guias topologicas y ejemplos visibles

**Archivos principales a cambiar**

- `docs/guides/vault-structure.md`
- `docs/guides/enterprise-vault.md`
- `docs/vision/ARQUITECTURA-GLOBAL-CORTEX.md`
- `docs/enterprise/MANIFIESTO-CORTEX-ENTERPRISE.md`
- `examples/basic_usage.py`
- `examples/auth.py`
- `examples/langchain_integration.py`

**Dependencias que deben revisarse o corregirse por arrastre**

- `README.md`
- `docs/guides/getting-started.md`
- `docs/guides/configuration-reference.md`
- `cortex/workspace/layout.py`
- `cortex/setup/orchestrator.py`

**Checklist**

- [x] Corregir las rutas de `vault/`, `.memory/`, `memory/` y `.cortex/` en las guias topologicas.
- [x] Aclarar en las guias enterprise que documentos historicos no son necesariamente la fuente operativa actual.
- [x] Revisar los ejemplos de `examples/` para que no asuman una API o layout ya desalineados.
- [x] Mantener fuera de esta epica los documentos historicos de avance o review salvo que un desajuste critico los vuelva peligrosos.

## Validacion de la epica

- [x] Leer de corrido `README.md`, `docs/guides/getting-started.md` y `docs/guides/configuration-reference.md` y confirmar que no se contradicen.
- [x] Ejecutar `pytest -q tests/unit/cli/test_main.py` si hubo cambios que toquen comportamiento documentado del CLI.
- [x] Completar el archivo de realizacion de la epica.

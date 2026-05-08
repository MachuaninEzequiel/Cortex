# FASE 2 — "Consistencia del Ecosistema"

**Documento padre:** `docs/tests/PLAN-GLOBAL.md`  
**Fecha:** 2026-05-08  
**Estado:** Planificación detallada — listo para ejecución  
**Semáforo:** 🟡 Amarillo (importante, no bloqueante individualmente, pero sí en conjunto)

---

## 1. Resumen Ejecutivo

Un usuario beta no solo ejecuta comandos CLI; también usa `cortex-pi/`, lee los skills generados, y depende de los workflows de GitHub Actions. Si la CLI evoluciona pero los artefactos generados no se actualizan, el beta experimenta inconsistencias silenciosas: comandos mencionados en skills que ya no existen, workflows que referencian scripts que cambiaron de nombre, o configuraciones Pi que apuntan a archivos inexistentes.

Esta fase implementa **tests de integridad de artefactos** que no requieren levantar procesos ni crear proyectos. Son tests puros de pytest que validan la coherencia interna del repositorio Cortex como producto distribuible.

Los 4 ejes de validación son:
1. **Consistencia cortex-pi vs CLI** — Lo que Pi configura debe coincidir con lo que la CLI genera.
2. **Validez de YAMLs generados** — Los templates de workflow deben producir YAML parseable y estructuralmente correcto.
3. **Integridad de skills** — Cada skill Markdown debe tener frontmatter válido y no estar vacío.
4. **Alineación MCP ↔ CLI** — Las herramientas expuestas por el MCP server deben tener contraparte en la CLI.

---

## 2. Gate de Entrada

- [ ] FASE 1 cerrada (gate de salida completado).
- [ ] `tests/e2e/helpers.py` y `tests/e2e/conftest.py` funcionan (de FASE 1).

---

## 3. Gate de Salida (Definition of Done)

- [ ] El archivo `tests/e2e/test_artefact_integrity.py` existe y contiene tests para los 4 ejes.
- [ ] Todos los tests de artefactos pasan en local.
- [ ] Los tests están marcados con `@pytest.mark.artefact`.
- [ ] Se detecta al menos 1 inconsistencia real (si existe) o se confirma que no hay inconsistencias.
- [ ] Si se encuentran inconsistencias, se documentan en `docs/tests/FASE-2-DEFECTOS.md` (opcional) o se corrigen.

---

## 4. Estructura de Archivos

```
tests/
└── e2e/
    ├── test_artefact_integrity.py   ← NUEVO (unico archivo de test de esta fase)
    └── artefacts/                   ← NUEVO (datos auxiliares si se necesitan)
        └── __init__.py
```

---

## 5. Tasks Detalladas

---

### TASK 2-1 — Consistencia cortex-pi vs CLI

**Fase:** FASE 2  
**Dependencias:** FASE 1 cerrada  
**Rama:** `tests/fase-2-task-1-pi-consistency-tests`

#### Objetivo
Validar que los archivos en `cortex-pi/` sean internamente consistentes y que referencien elementos que existen en la CLI y en el workspace generado.

#### Archivo a crear/modificar
- `tests/e2e/test_artefact_integrity.py` — agregar clase `TestPiConsistency`

#### Implementación paso a paso

**TestPiConsistency** (clase con `@pytest.mark.artefact`):

Metodos:

1. `test_justfile_references_existing_extensions()`
   - Leer `cortex-pi/justfile`.
   - Extraer todos los paths que terminen en `.ts` (regex: `[\w\-/]+\.ts`).
   - Para cada path, verificar que exista relativo a `cortex-pi/`.
   - Ejemplo: `{{EXT}}/system-select.ts` → verificar `cortex-pi/.pi/extensions/system-select.ts`.

2. `test_justfile_references_existing_agents()`
   - Extraer referencias a archivos `.md` en `.pi/agents/`.
   - Verificar que existan.

3. `test_pi_agents_reference_valid_cli_commands()`
   - Leer todos los `.md` en `cortex-pi/.pi/agents/`.
   - Extraer menciones a comandos `cortex <subcommand>`.
   - Para cada comando, verificar que exista en la CLI (usar introspección de `typer` o parsear `cortex.cli.main.app.registered_commands`).
   - Lista de comandos a verificar (no exhaustiva, pero representativa):
     - `cortex init`, `cortex setup`, `cortex save-session`, `cortex create-spec`, `cortex sync-vault`, `cortex search`, `cortex doctor`, `cortex memory-report`, `cortex promote-knowledge`, `cortex review-knowledge`.

4. `test_pi_skills_reference_valid_tools()`
   - Leer `cortex-pi/.pi/skills/cortex-vault.md`.
   - Verificar que las herramientas mencionadas (`cortex_search`, `cortex_context`, etc.) correspondan a herramientas del MCP server o comandos CLI.

5. `test_pi_settings_json_is_valid_json()`
   - Leer `cortex-pi/.pi/settings.json`.
   - Verificar que sea JSON parseable.
   - Verificar que tenga las claves esperadas: `version`, `settings` (o lo que corresponda según la estructura real).

6. `test_pi_system_prompt_exists()`
   - Verificar que `cortex-pi/.pi/system.md` exista y no esté vacío.

#### Checklist de verificación
- [ ] `test_justfile_references_existing_extensions` pasa.
- [ ] `test_justfile_references_existing_agents` pasa.
- [ ] `test_pi_agents_reference_valid_cli_commands` pasa (o reporta comandos obsoletos).
- [ ] `test_pi_skills_reference_valid_tools` pasa.
- [ ] `test_pi_settings_json_is_valid_json` pasa.
- [ ] `test_pi_system_prompt_exists` pasa.

---

### TASK 2-2 — Validez de YAMLs Generados

**Fase:** FASE 2  
**Dependencias:** TASK 2-1 (puede ejecutarse en paralelo)  
**Rama:** `tests/fase-2-task-2-yaml-artefact-validation`

#### Objetivo
Validar que las funciones template del setup generen YAMLs parseables y con la estructura mínima esperada. No se testean los workflows en GitHub Actions; solo su validez sintáctica y semántica básica.

#### Archivo a crear/modificar
- `tests/e2e/test_artefact_integrity.py` — agregar clase `TestGeneratedYamlArtefacts`

#### Implementación paso a paso

**TestGeneratedYamlArtefacts** (clase con `@pytest.mark.artefact`):

> **NOTA IMPLEMENTACIÓN — P7:** Todas las funciones `render_*` en `cortex/setup/templates.py` requieren un `ProjectContext` como primer argumento. No tienen defaults. Antes de llamarlas, crear un contexto mínimo:
> ```python
> from cortex.setup.detector import Detector
> ctx = Detector(tmp_path).detect()  # o equivalente según la API real
> content = render_ci_pull_request(ctx)
> ```
> Verificar la firma exacta del `Detector` contra el código fuente en `cortex/setup/detector.py` antes de implementar.

Metodos:

1. `test_ci_pull_request_yaml_is_valid()`
   - Importar `render_ci_pull_request` desde `cortex.setup.templates`.
   - Llamarla con argumentos por defecto.
   - Parsear el resultado con `yaml.safe_load`.
   - Verificar que sea un `dict`.
   - Verificar que tenga `name`, `on`, `jobs`.

2. `test_ci_feature_yaml_is_valid()`
   - Similar para `render_ci_feature`.

3. `test_cd_deploy_yaml_is_valid()`
   - Similar para `render_cd_deploy`.

4. `test_ci_enterprise_governance_yaml_is_valid()`
   - Similar para `render_ci_enterprise_governance`.

5. `test_rendered_config_yaml_is_valid()`
   - Importar `render_config_yaml`.
   - Llamarla con valores por defecto.
   - Parsear con `yaml.safe_load`.
   - Validar contra `CortexConfig`.

6. `test_rendered_workspace_yaml_is_valid()`
   - Importar `render_workspace_yaml`.
   - Llamarla.
   - Parsear con `yaml.safe_load`.
   - Verificar que tenga `layout_version: 2`.

7. `test_all_workflows_have_on_trigger()`
   - Para cada template de workflow, verificar que el YAML parseado tenga la clave `on` (triggers).

8. `test_all_workflows_have_at_least_one_job()`
   - Verificar que `jobs` no esté vacío.

> **ATENCIÓN — `render_workspace_yaml`:** Si esta función no existe en `templates.py`, omitir el test 6 y documentar el hallazgo en el checklist.

#### Checklist de verificación
- [ ] Se verificó la firma de `Detector` o método equivalente para construir `ProjectContext` antes de implementar.
- [ ] Los 8 métodos pasan (o el test 6 se omite con documentación si `render_workspace_yaml` no existe).
- [ ] Ningún template genera YAML que `yaml.safe_load` rechace.
- [ ] `CortexConfig.model_validate` acepta el output de `render_config_yaml`.

---

### TASK 2-3 — Integridad de Skills

**Fase:** FASE 2  
**Dependencias:** TASK 2-1 (puede ejecutarse en paralelo)  
**Rama:** `tests/fase-2-task-3-skill-frontmatter-checks`

#### Objetivo
Validar que los skills distribuidos en `cortex/skills/` y generados en `.cortex/skills/` cumplan con un formato mínimo de calidad: frontmatter YAML válido, cuerpo no vacío, y estructura predecible.

#### Archivo a crear/modificar
- `tests/e2e/test_artefact_integrity.py` — agregar clase `TestSkillIntegrity`

#### Implementación paso a paso

**TestSkillIntegrity** (clase con `@pytest.mark.artefact`):

Metodos:

1. `test_all_cortex_skills_have_frontmatter()`
   - Recorrer `cortex/skills/` buscando archivos `.md`.
   - Para cada uno, verificar que empiece con `---` seguido de YAML válido.
   - Usar regex simple o split por `---\n`.

2. `test_all_cortex_skills_have_non_empty_body()`
   - Para cada `.md` en `cortex/skills/`, verificar que después del frontmatter haya contenido no vacío.

3. `test_all_obsidian_skills_have_skill_md()`
   - Recorrer `cortex/skills/` buscando directorios (cada skill puede ser un directorio).
   - Verificar que cada directorio de skill contenga al menos un archivo llamado `SKILL.md` o `README.md`.

4. `test_generated_agent_guidelines_exist()`
   - Verificar que `cortex/agent_guidelines.md` exista y no esté vacío.
   - Verificar que `cortex/agent_guidelines_work.md` exista y no esté vacío.

5. `test_generated_skills_have_expected_sections()`
   - Para `cortex/skills/cortex-sync.md` y `cortex/skills/cortex-SDDwork.md`, verificar que contengan las secciones:
     - `# ` (título H1)
     - `## ` (al menos una sección H2)

6. `test_subagents_have_non_empty_content()`
   - Verificar que cada `.md` en `cortex/subagents/` exista y tenga > 100 caracteres.

#### Checklist de verificación
- [ ] Todos los `.md` en `cortex/skills/` tienen frontmatter YAML parseable.
- [ ] Todos los skills tienen cuerpo no vacío.
- [ ] Los subagentes no están vacíos.
- [ ] `agent_guidelines.md` y `agent_guidelines_work.md` existen.

---

### TASK 2-4 — Alineación MCP ↔ CLI

**Fase:** FASE 2  
**Dependencias:** TASK 2-1 (puede ejecutarse en paralelo)  
**Rama:** `tests/fase-2-task-4-mcp-tools-cli-alignment`

#### Objetivo
Validar que las herramientas expuestas por el MCP server (`cortex/mcp/server.py`) tengan una contraparte lógica en la CLI o en el core de Cortex. Esto evita que el MCP server ofrezca herramientas que no pueden cumplirse.

#### Archivo a crear/modificar
- `tests/e2e/test_artefact_integrity.py` — agregar clase `TestMcpCliAlignment`

#### Implementación paso a paso

**TestMcpCliAlignment** (clase con `@pytest.mark.artefact`):

Metodos:

1. `test_mcp_tools_list_is_not_empty()`
   - Importar `CortexMCPServer`.
   - Instanciar o inspeccionar la lista de tools.
   - Verificar que haya al menos 3 tools registradas.

2. `test_mcp_tools_have_descriptions()`
   - Para cada tool del MCP server, verificar que tenga `description` no vacía.

3. `test_mcp_search_has_cli_counterpart()`
   - Verificar que el tool `cortex_search` (o similar) del MCP tenga un comando CLI equivalente (`cortex search`).
   - Estrategia: mantener un diccionario manual `MCP_TO_CLI` en el test que mapee nombres de tools a comandos CLI, y verificar que el comando exista en `cortex.cli.main.app`.

4. `test_mcp_remember_has_cli_counterpart()`
   - Similar para `cortex_remember` → `cortex remember`.

5. `test_mcp_sync_vault_has_cli_counterpart()`
   - Similar para `cortex_sync_vault` → `cortex sync-vault`.

6. `test_mcp_create_spec_has_governance_rule()`
   - Verificar que el tool `cortex_create_spec` del MCP tenga documentada la regla de gobernanza (requiere `cortex_sync_ticket` previo).
   - Esto puede validarse inspeccionando el docstring o la implementación del tool.

7. `test_mcp_server_initializes_without_api_keys()`
   - Crear una instancia de `CortexMCPServer` con config `llm.provider = "none"`.
   - Verificar que no lance excepción.

#### Diccionario de mapeo real (verificado contra `cortex/mcp/server.py`)

```python
# Tools registradas en el MCP server (cortex/mcp/server.py):
# cortex_search_vector, cortex_search, cortex_context, cortex_sync_ticket,
# cortex_create_spec, cortex_save_session, cortex_import_hu, cortex_get_hu, cortex_sync_vault
#
# NOTA: cortex_remember NO existe como tool MCP. El MCP no expone remember directamente.

MCP_TO_CLI = {
    "cortex_search_vector": "search",       # búsqueda semántica profunda (ONNX)
    "cortex_search": "search",              # búsqueda rápida por keywords
    "cortex_context": "context",            # contexto enriquecido del proyecto
    "cortex_sync_vault": "sync-vault",
    "cortex_create_spec": "create-spec",
    "cortex_save_session": "save-session",
    "cortex_import_hu": "hu import",        # CLI: cortex hu import <id>
    "cortex_get_hu": "hu show",             # CLI: cortex hu show <id>
    "cortex_sync_ticket": None,             # no tiene CLI directa, solo existe en MCP
}
```

#### Checklist de verificación
- [ ] `test_mcp_tools_list_is_not_empty` pasa.
- [ ] `test_mcp_tools_have_descriptions` pasa.
- [ ] Los mapeos `MCP_TO_CLI` están verificados.
- [ ] `test_mcp_server_initializes_without_api_keys` pasa.

---

## 6. Riesgos y Mitigaciones de la Fase

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|------------|
| Los tests son muy frágiles ante refactorings menores de texto | Media | Medio | Los tests no validan contenido exacto, solo existencia y parseabilidad. |
| `cortex-pi/` no está en el PYTHONPATH | Baja | Medio | Leer archivos con paths relativos al repo root (`Path(__file__).resolve().parents[2] / "cortex-pi"`). |
| Los templates cambian de firma | Baja | Medio | Si cambia la firma de `render_*`, el test fallará y se actualizará. |
| El MCP server tiene tools dinámicas | Baja | Medio | Usar introspección en runtime en vez de lista hardcodeada si es posible. |

---

## 7. Notas para el Agente Ejecutor

- Los tests de esta fase son puramente declarativos: no modifican el filesystem.
- Pueden ejecutarse en paralelo sin riesgo.
- Si se detecta una inconsistencia real (ej: un skill referencia un comando obsoleto), no corregir automáticamente a menos que sea trivial y esté dentro del scope. Documentar y reportar.
- Al finalizar la fase, ejecutar `pytest tests/e2e/test_artefact_integrity.py -m artefact -v`.

# SPEC-REFAC-WORKSPACE-STRUCT
**Fecha:** 2026-05-01  
**Estado:** Propuesta de implementacion por fases  
**Prioridad:** Alta  
**Complejidad estimada:** Alta  
**Riesgo global si se hace en hard cut:** Alto  
**Riesgo global si se hace con compatibilidad temporal y gates:** Medio  

## 0. Resumen Ejecutivo
Este documento redefine por completo el plan de refactorizacion del workspace de Cortex para mover la infraestructura del proyecto del usuario a un contenedor visible `cortex/`, con un subespacio interno `.system/` para el estado operativo y los artefactos que no forman parte del conocimiento visible del desarrollador.

El objetivo no es "mover carpetas", sino **cambiar el modelo de layout del producto** sin romper:

- runtime de memoria
- configuracion local y enterprise
- `doctor`, `hint` y reporting
- setup inicial y generadores
- MCP y delegacion de subagentes
- adaptadores IDE
- WebGraph
- tests
- documentacion operativa

La refactorizacion **no debe hacerse como cutover directo**. El enfoque correcto para este repo es:

1. Definir un contrato central de layout.
2. Introducir compatibilidad dual `nuevo + legacy`.
3. Migrar lectores y runtime al resolvedor central.
4. Migrar generadores y setup.
5. Migrar IDE, MCP y WebGraph.
6. Activar el layout nuevo como default.
7. Retirar compatibilidad legacy en una fase posterior, no en la misma release.

---

## 1. Problema Actual
Hoy Cortex asume un layout de proyecto distribuido en la raiz del repo del usuario. En esta base aparecen referencias legacy a:

- `config.yaml`
- `vault/`
- `vault-enterprise/`
- `.memory/`
- `.cortex/skills/`
- `.cortex/subagents/`
- `.cortex/AGENT.md`
- `.cortex/system-prompt.md`
- `.cortex/webgraph/config.yaml`
- `.cortex/webgraph/workspace.yaml`
- `.cortex/webgraph/cache/`
- `scripts/devsecdocops.sh`

Esto genera cuatro problemas estructurales:

1. **DX pobre en la raiz del proyecto**  
   Cortex ensucia la raiz con demasiados directorios y archivos operativos.

2. **Resolucion de rutas distribuida**  
   Varias partes del runtime resuelven paths de forma local y no centralizada.

3. **Acoplamiento fuerte entre setup y runtime**  
   No alcanza con cambiar los generadores. Tambien hay que actualizar los consumidores en tiempo de ejecucion.

4. **Alto riesgo de regresion silenciosa**  
   Un proyecto puede inicializar "bien" pero luego fallar en MCP, IDE, WebGraph o doctor porque alguno sigue mirando el layout viejo.

---

## 2. Hallazgos Quirurgicos del Repo Actual
El estado actual del repo muestra que el cambio afecta mas superficie de la que contemplaba el plan original.

### 2.1 Runtime y resolucion de config
- `cortex/core.py`
- `cortex/runtime_context.py`
- `cortex/cli/main.py`
- `cortex/doctor.py`

Hallazgo critico:

- `AgentMemory` hoy define `project_root` como `config_path.parent`.
- Si `config.yaml` se mueve a `cortex/config.yaml` y se conservan paths tipo `cortex/vault`, se duplica el prefijo y se rompe la resolucion.

Esto significa que **no es valido mover `config.yaml` a `cortex/config.yaml` sin cambiar primero el modelo de resolucion de rutas**.

### 2.2 Workspace release-2 y activos Cortex
- `cortex/setup/cortex_workspace.py`
- `cortex/setup/orchestrator.py`

Hallazgo:

- El plan original solo mencionaba `skills/` y `subagents/`, pero el workspace real tambien incluye:
  - `AGENT.md`
  - `system-prompt.md`
  - skills release-2
  - subagentes release-2

### 2.3 Enterprise
- `cortex/enterprise/config.py`
- `cortex/enterprise/models.py`
- `cortex/enterprise/knowledge_promotion.py`
- `cortex/enterprise/reporting.py`

Hallazgo:

- No solo hay que mover `org.yaml`.
- Tambien hay que decidir el destino de:
  - `enterprise_memory_path`
  - promotion records
  - discovery logic
  - reporting

### 2.4 IDE y descubrimiento de proyecto
- `cortex/ide/__init__.py`
- `cortex/ide/adapters/*.py`

Hallazgo:

- Hoy el descubrimiento del proyecto Cortex busca explicitamente `.cortex/`.
- Si esto no se migra, el nuevo workspace no se descubre.

### 2.5 MCP
- `cortex/mcp/server.py`

Hallazgo:

- El server busca `config.yaml` y subagentes en layout legacy.
- Esto impacta directamente la delegacion operativa.

### 2.6 WebGraph
- `cortex/webgraph/config.py`
- `cortex/webgraph/federation.py`
- `cortex/webgraph/setup.py`
- `cortex/webgraph/cache.py`
- `cortex/webgraph/cli.py`

Hallazgo:

- WebGraph sigue escribiendo infraestructura propia en `.cortex/webgraph/`.
- Si el objetivo es un contenedor unico `cortex/`, tambien debe migrar.

### 2.7 Diagnostico, hinting y politica Git
- `cortex/doctor.py`
- `cortex/tutor/hint.py`
- `cortex/git_policy.py`
- `.gitignore`

Hallazgo:

- Estos modulos usan paths legacy como parte de su comportamiento funcional, no solo cosmetico.

### 2.8 Tests
- `tests/integration/setup/*`
- `tests/integration/mcp/*`
- `tests/unit/cli/*`
- `tests/unit/enterprise/*`
- `tests/unit/webgraph/*`
- `tests/unit/test_runtime_context.py`

Hallazgo:

- La suite actual esta muy acoplada a `.memory`, `.cortex`, `config.yaml` en raiz, `vault/` y `vault-enterprise/`.

---

## 3. Objetivos del Refactor
La implementacion correcta debe cumplir simultaneamente con estos objetivos:

1. Reducir la contaminacion visual de la raiz del repo del usuario.
2. Mantener visibles los artefactos utiles para el desarrollador.
3. Ocultar el estado operativo y la infraestructura interna.
4. Permitir compatibilidad temporal con repos ya inicializados.
5. Centralizar la resolucion de rutas en un unico contrato.
6. Permitir que setup, runtime, IDE, MCP y WebGraph lean el mismo modelo.
7. Evitar que el cambio dependa de coincidencias accidentales de `cwd`.

---

## 4. No Objetivos
Este refactor **no** busca:

- cambiar la semantica de memoria hibrida
- cambiar el modelo de promotion enterprise
- rediseñar el formato logico de los documentos del vault
- rehacer la UX de WebGraph en esta misma especificacion
- eliminar soporte legacy en la misma release de la migracion

---

## 5. Principios de Diseño
La implementacion debe seguir estos principios:

1. **Resolver antes de escribir**  
   Primero se redefine como Cortex descubre y resuelve paths. Despues se cambian los generadores.

2. **Nuevo layout con compatibilidad temporal**  
   Los lectores deben entender ambos layouts antes de que los escritores emitan solo el nuevo.

3. **Un solo contrato de layout**  
   Ningun modulo critico debe hardcodear `config.yaml`, `.cortex`, `.memory` o `vault` sin pasar por un resolvedor central.

4. **Raiz del repo y raiz del workspace no son lo mismo**  
   El repo del usuario sigue teniendo raiz Git. Cortex vive dentro de un `workspace_root`.

5. **Los paths relativos deben tener una base declarada**  
   No se debe inferir por costumbre si algo es relativo al repo root, al `config.yaml` o al `cwd`.

6. **Soporte Windows y Unix**  
   `.system/` no debe depender solo del prefijo con punto para ser "oculto". En Unix sera convencional; en Windows debe asumirse que la carpeta puede seguir siendo visible salvo tratamiento adicional.

---

## 6. Contrato de Layout Objetivo
La propuesta correcta para este repo es:

```text
<repo-root>/
  cortex/
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
      .system/
        promotion/
          records.jsonl
    scripts/
      devsecdocops.sh
    .system/
      memory/
      enterprise-memory/
      org.yaml
      workspace.yaml
      AGENT.md
      system-prompt.md
      skills/
      subagents/
      webgraph/
        config.yaml
        workspace.yaml
        cache/
  .github/
    workflows/
```

### 6.1 Decision de diseno clave
**Todos los paths relativos declarados por Cortex deben resolverse contra `workspace_root = <repo-root>/cortex`, no contra el parent fisico del archivo de config ni contra el `cwd`.**

Esto evita la contradiccion detectada en el plan original.

### 6.2 Configuracion resultante esperada
En este modelo, `cortex/config.yaml` debe mantener rutas **relativas al workspace root**, por ejemplo:

```yaml
episodic:
  persist_dir: .system/memory

semantic:
  vault_path: vault
```

Y `cortex/.system/org.yaml` debe mantener:

```yaml
memory:
  enterprise_vault_path: vault-enterprise
  enterprise_memory_path: .system/enterprise-memory
```

### 6.3 Razon de esta decision
Si `config.yaml` vive dentro de `cortex/`, almacenar `cortex/vault` o `cortex/.system/memory` es conceptualmente incorrecto salvo que el resolvedor lo interprete contra `repo_root`. Eso introduce una regla mas fragil y menos intuitiva.

Por eso, el contrato nuevo sera:

- `repo_root`: raiz Git o raiz del proyecto del usuario
- `workspace_root`: `repo_root / "cortex"`
- todas las rutas internas de Cortex se resuelven contra `workspace_root`

---

## 7. Arquitectura Recomendada de Implementacion
Se recomienda introducir una capa central explicita, por ejemplo:

- `cortex/workspace/layout.py`

o equivalente funcional, con una API similar a:

- `WorkspaceLayout.discover(start: Path) -> WorkspaceLayout`
- `WorkspaceLayout.from_repo_root(repo_root: Path) -> WorkspaceLayout`
- `layout.repo_root`
- `layout.workspace_root`
- `layout.system_root`
- `layout.config_path`
- `layout.org_config_path`
- `layout.vault_path`
- `layout.enterprise_vault_path`
- `layout.episodic_memory_path`
- `layout.enterprise_memory_path`
- `layout.skills_dir`
- `layout.subagents_dir`
- `layout.agent_guidelines_path`
- `layout.system_prompt_path`
- `layout.webgraph_config_path`
- `layout.webgraph_workspace_path`
- `layout.webgraph_cache_dir`
- `layout.is_legacy_layout`
- `layout.resolve_workspace_relative(value: str | Path) -> Path`

### 7.1 Compatibilidad requerida
El resolvedor debe poder descubrir:

- layout nuevo
- layout legacy
- repos parcialmente migrados durante la transicion

### 7.2 Precedencia recomendada
Mientras exista compatibilidad dual, la precedencia debe ser:

1. layout nuevo si existe `repo_root/cortex/`
2. layout legacy si existen `config.yaml`, `.cortex/`, `vault/` o `.memory/` en raiz
3. si no existe ninguno, comportamiento de bootstrap limpio

---

## 8. Semaforo Global por Fases
El cambio no debe implementarse por tipo de archivo, sino por fases operativas.

### `Rojo`
Fases donde no se debe avanzar sin gate tecnico formal.

- Fase 0: contrato de layout
- Fase 1: compatibilidad dual
- Fase 2: centralizacion de resolucion de paths
- Fase 8: retiro de compatibilidad legacy

### `Amarillo`
Fases que requieren smoke tests y validacion cruzada.

- Fase 3: runtime critico
- Fase 4: setup y generadores
- Fase 5: IDE, MCP y WebGraph
- Fase 6: docs, doctor, hint, tests

### `Verde`
Fases de activacion una vez cerradas las anteriores.

- Fase 7: activar layout nuevo por defecto

---

## 9. Plan de Implementacion por Fases

## Fase 0 - Definir el Contrato de Layout
**Semaforo:** Rojo  
**Objetivo:** congelar una unica verdad semantica para el nuevo workspace antes de tocar los consumidores.

### Alcance
- Definir formalmente `repo_root`, `workspace_root` y `system_root`.
- Definir la base de resolucion de todos los paths relativos.
- Definir el arbol objetivo exacto.
- Decidir el destino de promotion metadata y WebGraph.

### Archivos / zonas que deben quedar alineados al terminar la fase
- `docs/refact/REFAC-WORKSPACE-STRUCT.md`
- `docs/refact/REFAC-WEBGRAPH.md`
- futura capa central de layout

### Decisiones obligatorias
1. `config.yaml` vive en `cortex/config.yaml`.
2. `org.yaml` vive en `cortex/.system/org.yaml`.
3. Los valores relativos de config se resuelven contra `workspace_root`.
4. WebGraph se migra a `cortex/.system/webgraph/`.
5. Promotion records viven en `cortex/vault-enterprise/.system/promotion/records.jsonl`.

### Riesgos
- Elegir una base de resolucion equivocada y propagar el error a todo el sistema.
- Dejar fuera del contrato piezas reales como `AGENT.md`, `system-prompt.md` o WebGraph.

### Gate de salida
- El layout final esta documentado sin contradicciones.
- Existe una regla unica y declarativa para resolver cualquier path interno.

### Rollback
- No aplica; esta fase es de definicion.

---

## Fase 1 - Introducir Compatibilidad Dual
**Semaforo:** Rojo  
**Objetivo:** permitir que Cortex lea tanto el layout nuevo como el layout legacy durante la transicion.

### Alcance
- Descubrimiento de proyecto
- carga de config local
- carga de config enterprise
- descubrimiento de skills, subagentes y guidelines
- lectura de paths de WebGraph

### Archivos impactados
- `cortex/cli/main.py`
- `cortex/core.py`
- `cortex/runtime_context.py`
- `cortex/doctor.py`
- `cortex/enterprise/config.py`
- `cortex/enterprise/knowledge_promotion.py`
- `cortex/enterprise/reporting.py`
- `cortex/ide/__init__.py`
- `cortex/mcp/server.py`
- `cortex/webgraph/cli.py`
- `cortex/webgraph/config.py`
- `cortex/webgraph/federation.py`
- `cortex/webgraph/setup.py`
- `cortex/webgraph/cache.py`
- `cortex/webgraph/semantic_source.py`
- `cortex/webgraph/episodic_source.py`

### Regla operativa
Mientras dure esta fase:

- los lectores entienden ambos layouts
- los escritores todavia pueden seguir emitiendo legacy o nuevo segun el estado de implementacion
- ningun comando critico debe asumir que solo existe uno de los dos

### Riesgos
- Ambiguedad al descubrir proyecto
- Seleccionar por error el layout equivocado en repos mixtos
- Compatibilidad parcial que haga andar CLI pero no MCP o IDE

### Gate de salida
- Un repo legacy inicializado antes del cambio sigue funcionando.
- Un repo nuevo con layout nuevo puede ser descubierto y leido.
- `doctor` reporta correctamente ambos layouts durante la transicion.

### Rollback
- Mantener prioridad legacy si el nuevo layout no se detecta con suficiente confiabilidad.

---

## Fase 2 - Centralizar la Resolucion de Paths
**Semaforo:** Rojo  
**Objetivo:** eliminar hardcodes estructurales en modulos criticos y reemplazarlos por el resolvedor central.

### Alcance funcional
- paths de config local
- paths de org enterprise
- paths de vault local
- paths de enterprise vault
- paths de memoria episodica local y enterprise
- paths de skills, subagentes, prompts y guidelines
- paths de WebGraph

### Archivos impactados de forma critica
- `cortex/core.py`
- `cortex/runtime_context.py`
- `cortex/doctor.py`
- `cortex/cli/main.py`
- `cortex/mcp/server.py`
- `cortex/enterprise/config.py`
- `cortex/enterprise/models.py`
- `cortex/webgraph/cli.py`
- `cortex/webgraph/semantic_source.py`
- `cortex/webgraph/episodic_source.py`
- `cortex/webgraph/config.py`
- `cortex/webgraph/federation.py`
- `cortex/webgraph/cache.py`

### Reglas de implementacion
1. Ningun modulo debe construir paths de layout con strings hardcodeados si ya existe un valor equivalente en el resolvedor.
2. Ningun modulo critico debe depender implicitamente de `Path.cwd()`.
3. Los defaults del runtime deben declararse en terminos del contrato nuevo, no del legacy.

### Riesgos
- Resolver correctamente config pero no WebGraph
- Resolver memoria local pero no enterprise
- Dejar paths "pequeños" legacy en mensajes, hints o validaciones

### Gate de salida
- Los modulos criticos de lectura usan el resolvedor central.
- Ya no hay dependencia estructural fuerte de `.cortex`, `.memory`, `config.yaml` en raiz o `vault` en raiz.

### Rollback
- Mantener wrappers de compatibilidad que sigan exponiendo rutas legacy derivadas si algun consumidor externo todavia las requiere.

---

## Fase 3 - Migrar Runtime Critico
**Semaforo:** Amarillo  
**Objetivo:** hacer que la operacion real de Cortex use el nuevo layout correctamente.

### Flujos que deben quedar funcionando
- `AgentMemory`
- `remember`
- `search`
- `sync-vault`
- `create-spec`
- `save-session`
- retrieval enterprise
- promotion
- reporting
- `doctor`

### Archivos impactados
- `cortex/core.py`
- `cortex/runtime_context.py`
- `cortex/services/spec_service.py`
- `cortex/services/session_service.py`
- `cortex/services/pr_service.py`
- `cortex/workitems/service.py`
- `cortex/enterprise/knowledge_promotion.py`
- `cortex/enterprise/retrieval_service.py`
- `cortex/enterprise/reporting.py`
- `cortex/doctor.py`

### Requisitos de esta fase
1. `AgentMemory` no debe derivar `project_root` solo del parent de `config.yaml`.
2. La memoria episodica local debe resolver a `cortex/.system/memory`.
3. La memoria enterprise debe resolver a `cortex/.system/enterprise-memory`.
4. El vault local debe resolver a `cortex/vault`.
5. El enterprise vault debe resolver a `cortex/vault-enterprise`.

### Riesgos
- Ruptura silenciosa de indexing
- Creacion de archivos en rutas duplicadas tipo `cortex/cortex/...`
- Promotion escribiendo records en ubicaciones inconsistentes

### Gate de salida
- Un proyecto nuevo puede:
  - guardar specs
  - guardar sesiones
  - sincronizar vault
  - recuperar contexto local
  - cargar configuracion enterprise
- Un proyecto legacy sigue siendo legible.

### Rollback
- Permitir fallback temporal a lectura legacy mientras el resolvedor central decide rutas.

---

## Fase 4 - Migrar Setup y Generadores
**Semaforo:** Amarillo  
**Objetivo:** hacer que el bootstrap escriba exclusivamente el layout nuevo.

### Alcance
- directorios base
- config local
- config enterprise
- enterprise workspace
- skills
- subagentes
- prompts y guidelines
- scripts
- workflows
- templates de docs

### Archivos impactados
- `cortex/setup/orchestrator.py`
- `cortex/setup/templates.py`
- `cortex/setup/cortex_workspace.py`
- `cortex/setup/cold_start.py`
- `cortex/setup/detector.py`
- `cortex/enterprise/config.py`
- `cortex/cli/main.py`

### Reglas de escritura
1. `setup agent` debe escribir:
   - `cortex/config.yaml`
   - `cortex/vault/...`
   - `cortex/.system/org.yaml`
   - `cortex/.system/skills/...`
   - `cortex/.system/subagents/...`
   - `cortex/.system/AGENT.md`
   - `cortex/.system/system-prompt.md`

2. `setup enterprise` debe escribir:
   - `cortex/vault-enterprise/...`
   - `cortex/vault-enterprise/.system/promotion/...`
   - `cortex/.system/workspace.yaml`

3. `setup webgraph` debe escribir:
   - `cortex/.system/webgraph/config.yaml`
   - `cortex/.system/webgraph/workspace.yaml`
   - `cortex/.system/webgraph/cache/`

### Templates y referencias que deben actualizarse
- rutas de `verify-docs`
- rutas de `validate-docs`
- rutas de `index-docs`
- ubicacion de `AGENT.md`
- ubicacion de `org.yaml`
- comandos y runbooks que mencionen `.memory/`, `.cortex/`, `vault/`, `vault-enterprise/`

### Riesgos
- Setup generando nuevo layout pero runtime leyendo viejo
- Workflows y scripts quedando con rutas duras legacy

### Gate de salida
- Un repo inicializado desde cero genera exclusivamente el layout nuevo, excepto `.github/workflows/`.

### Rollback
- Permitir que setup detecte repos legacy y ofrezca modo de inicializacion legacy solo durante la transicion, si fuera estrictamente necesario.

---

## Fase 5 - Migrar IDE, MCP y WebGraph
**Semaforo:** Amarillo  
**Objetivo:** alinear los consumidores externos y de integracion con el nuevo modelo de workspace.

### 5.1 IDE
#### Archivos impactados
- `cortex/ide/__init__.py`
- `cortex/ide/base.py`
- `cortex/ide/adapters/vscode.py`
- `cortex/ide/adapters/cursor.py`
- `cortex/ide/adapters/claude_code.py`
- `cortex/ide/adapters/claude_desktop.py`
- `cortex/ide/adapters/opencode.py`
- `cortex/ide/adapters/windsurf.py`
- `cortex/ide/adapters/zed.py`
- `cortex/ide/adapters/antigravity.py`
- `cortex/ide/adapters/pi.py`
- `cortex/ide/prompts.py`

#### Requisitos
- el descubrimiento del proyecto no debe depender de `.cortex/`
- las referencias fuente deben apuntar a `cortex/.system/skills/...`
- las referencias a subagentes deben apuntar a `cortex/.system/subagents/...`
- los prompts y mensajes deben dejar de instruir layout legacy

### 5.2 MCP
#### Archivos impactados
- `cortex/mcp/server.py`

#### Requisitos
- descubrir `cortex/config.yaml`
- descubrir subagentes desde `cortex/.system/subagents/`
- mantener delegacion funcional en modo legacy durante la transicion

### 5.3 WebGraph
#### Archivos impactados
- `cortex/webgraph/cli.py`
- `cortex/webgraph/config.py`
- `cortex/webgraph/federation.py`
- `cortex/webgraph/setup.py`
- `cortex/webgraph/cache.py`
- `cortex/webgraph/semantic_source.py`
- `cortex/webgraph/episodic_source.py`

#### Requisitos
- config en `cortex/.system/webgraph/config.yaml`
- workspace en `cortex/.system/webgraph/workspace.yaml`
- cache en `cortex/.system/webgraph/cache/`
- doctor y serve deben resolver el nuevo layout

### Riesgos
- La IDE no se rompe por el layout nuevo en si mismo; se rompe si Cortex no encuentra su workspace o emite prompts con rutas viejas.
- MCP puede seguir arrancando pero fallar recien al delegar.
- WebGraph puede servir la UI pero no encontrar snapshot, vault o memoria.

### Gate de salida
- Al menos un smoke test real por cada integracion principal:
  - VSCode
  - Cursor
  - OpenCode
  - MCP delegation
  - WebGraph serve/export/doctor

### Rollback
- Mantener compatibilidad de lectura a rutas legacy en integraciones hasta la release de retiro.

---

## Fase 6 - Migrar Diagnostico, Politica Git, Documentacion y Tests
**Semaforo:** Amarillo  
**Objetivo:** cerrar el refactor de forma verificable y coherente para usuarios nuevos y existentes.

### 6.1 Diagnostico y hinting
#### Archivos impactados
- `cortex/doctor.py`
- `cortex/tutor/hint.py`
- `cortex/enterprise/reporting.py`

#### Requisitos
- `doctor` debe validar el layout nuevo correctamente
- `hint` debe inspeccionar `cortex/config.yaml`, `cortex/vault/`, `cortex/.system/org.yaml`
- reporting debe dejar de hablar de rutas legacy como si fueran canonicas

### 6.2 Politica Git
#### Archivos impactados
- `cortex/git_policy.py`
- `.gitignore`
- docs generadas de politica Git/Vault

#### Requisitos
Actualizar patrones a:

- `cortex/.system/memory/`
- `cortex/.system/enterprise-memory/`
- `cortex/vault/sessions/` si la politica lo sigue recomendando
- `cortex/.system/webgraph/cache/`

### 6.3 Documentacion
#### Archivos impactados
- `docs/guides/*`
- `docs/ops/*`
- `docs/tutor/*`
- plantillas generadas por setup

#### Requisitos
- la documentacion nueva debe explicar el layout nuevo
- si se menciona el legacy, debe ser explicitamente como compatibilidad o migracion

### 6.4 Tests
#### Archivos impactados
- `tests/integration/setup/*`
- `tests/integration/mcp/*`
- `tests/integration/enterprise/*`
- `tests/unit/cli/*`
- `tests/unit/enterprise/*`
- `tests/unit/webgraph/*`
- `tests/unit/test_runtime_context.py`
- `tests/unit/test_doctor_enterprise_governance.py`
- `tests/unit/test_ide_adapters.py`
- `tests/unit/test_mcp_server.py`

#### Requisitos
La suite debe cubrir:

- descubrimiento layout nuevo
- compatibilidad legacy
- setup nuevo
- runtime nuevo
- IDE y MCP
- WebGraph
- enterprise promotion/reporting

### Riesgos
- Tener el runtime bien pero mensajes y docs falsos
- Tener docs actualizadas pero tests anclados al legacy

### Gate de salida
- suite verde en los frentes criticos
- docs y `doctor` consistentes con el layout nuevo

### Rollback
- Mantener notas de compatibilidad legacy en docs mientras dure la transicion

---

## Fase 7 - Activar el Layout Nuevo por Defecto
**Semaforo:** Verde  
**Objetivo:** convertir el layout nuevo en la ruta oficial y default de Cortex.

### Alcance
- setup nuevo emite layout nuevo
- CLI comunica layout nuevo
- docs principales muestran layout nuevo
- compatibilidad legacy sigue existiendo pero ya no es el path principal

### Gate de salida
- el producto puede ser usado por un repo nuevo sin tocar ninguna ruta legacy

### Rollback
- si aparece una regresion severa, mantener el layout nuevo como experimental y no retirar compatibilidad legacy

---

## Fase 8 - Retirar Compatibilidad Legacy
**Semaforo:** Rojo  
**Objetivo:** eliminar deuda de compatibilidad una vez estabilizado el sistema.

### Recomendacion
No ejecutar esta fase en la misma release del cambio estructural.

### Condiciones minimas para autorizarla
- al menos una o dos versiones de convivencia
- zero blockers en IDE/MCP/WebGraph
- guia de migracion publicada y validada
- evidencia de que el layout nuevo es el dominante

### Alcance
- remover discovery legacy
- remover mensajes legacy
- remover tests legacy
- remover fallback de paths legacy

### Riesgos
- bloquear repos inicializados antes del cambio
- romper integraciones externas que aun dependan del layout anterior

### Gate de salida
- compatibilidad legacy puede eliminarse sin dejar casos de uso productivos fuera

### Rollback
- no retirar legacy si alguna integracion principal todavia depende de el

---

## 10. Cambios Exactos Esperados por Area

## 10.1 CLI
### Archivos
- `cortex/cli/main.py`

### Cambios esperados
- dejar de asumir `config.yaml` en raiz
- dejar de asumir `.cortex/org.yaml`
- actualizar mensajes help, prompts y descripciones
- cambiar defaults de `install-skills`
- cambiar referencias de setup webgraph y enterprise

### Observaciones
La CLI hoy mezcla defaults, ayudas al usuario y acceso real a rutas. Esta area debe quedar muy alineada con el resolvedor central.

---

## 10.2 Setup Orchestrator
### Archivos
- `cortex/setup/orchestrator.py`
- `cortex/setup/templates.py`
- `cortex/setup/cortex_workspace.py`
- `cortex/setup/cold_start.py`

### Cambios esperados
- escribir todo dentro de `cortex/`
- mover skills, subagentes, prompts y guidelines a `.system/`
- mover WebGraph a `.system/webgraph/`
- actualizar rutas hardcodeadas de workflows, scripts y docs starter

---

## 10.3 Runtime de Memoria
### Archivos
- `cortex/core.py`
- `cortex/runtime_context.py`
- `cortex/episodic/memory_store.py`
- `cortex/semantic/vault_reader.py`

### Cambios esperados
- nueva nocion de `workspace_root`
- resolucion consistente para vault y memoria
- eliminar dependencia accidental del parent de `config.yaml`

---

## 10.4 Enterprise
### Archivos
- `cortex/enterprise/config.py`
- `cortex/enterprise/models.py`
- `cortex/enterprise/knowledge_promotion.py`
- `cortex/enterprise/reporting.py`
- `cortex/enterprise/retrieval_service.py`

### Cambios esperados
- mover `org.yaml` a `.system/`
- mover enterprise memory a `.system/enterprise-memory`
- decidir y aplicar el destino de promotion records
- alinear reporting y doctor

---

## 10.5 IDE
### Archivos
- `cortex/ide/__init__.py`
- `cortex/ide/adapters/*.py`
- `cortex/ide/prompts.py`

### Cambios esperados
- nuevo discovery de workspace
- nuevas fuentes de skills y subagentes
- nuevos mensajes de orientacion

---

## 10.6 MCP
### Archivos
- `cortex/mcp/server.py`

### Cambios esperados
- carga de config desde workspace
- carga de subagentes desde `.system/subagents`
- compatibilidad legacy temporal

---

## 10.7 WebGraph
### Archivos
- `cortex/webgraph/*.py`

### Cambios esperados
- todo lo estructural de WebGraph queda dentro de `cortex/.system/webgraph/`
- doctor, serve, export y federacion resuelven layout nuevo

---

## 10.8 Diagnostico y Politica Git
### Archivos
- `cortex/doctor.py`
- `cortex/tutor/hint.py`
- `cortex/git_policy.py`
- `.gitignore`

### Cambios esperados
- nuevas rutas oficiales
- nueva narrativa diagnostica
- politicas Git alineadas con `.system/`

---

## 11. Matriz de Riesgos

| Riesgo | Severidad | Probabilidad | Mitigacion |
|---|---|---:|---|
| Duplicacion de prefijos `cortex/cortex/...` | Alta | Alta | Fijar `workspace_root` como base unica de resolucion |
| Setup genera nuevo layout pero runtime sigue leyendo legacy | Alta | Alta | Fases 1-3 antes de writers exclusivos |
| IDE no descubre el proyecto | Alta | Media | Migrar `cortex/ide/__init__.py` temprano |
| MCP arranca pero no encuentra subagentes | Alta | Media | Smoke test real de delegacion |
| WebGraph sigue escribiendo en `.cortex/webgraph/` | Media | Alta | Incluir WebGraph explicitamente en el contrato |
| `doctor` y `hint` reportan falso | Media | Alta | Migrarlos antes de activar default nuevo |
| Promotion records quedan repartidos | Media | Media | decidir ubicacion final en Fase 0 |
| Tests legacy bloquean adopcion | Media | Alta | incluir fase de actualizacion de suite |

---

## 12. Matriz de Validacion Minima
Antes de considerar completa la migracion, se deben validar como minimo estos escenarios:

1. `setup agent` en repo vacio crea layout nuevo completo.
2. `setup enterprise` en repo nuevo crea layout nuevo completo.
3. `doctor` funciona en repo nuevo.
4. `doctor` funciona en repo legacy.
5. `remember`, `save-session`, `create-spec`, `sync-vault` funcionan en repo nuevo.
6. retrieval local funciona en repo nuevo.
7. retrieval enterprise funciona en repo nuevo.
8. promotion/reporting enterprise funcionan en repo nuevo.
9. `install-ide --ide cursor` funciona en repo nuevo.
10. `install-ide --ide opencode` funciona en repo nuevo.
11. MCP puede delegar subagentes en repo nuevo.
12. `cortex webgraph doctor` funciona en repo nuevo.
13. `cortex webgraph serve` funciona en repo nuevo.
14. un repo legacy inicializado previamente sigue siendo legible.

---

## 13. Recomendacion Final
La refactorizacion del workspace **si conviene**, pero **solo** si se ejecuta como migracion de arquitectura y no como rename masivo de paths.

La regla clave para que salga bien es:

**primero compatibilidad y resolvedor central, despues writers nuevos, despues activacion default, y recien mucho mas tarde retiro legacy.**

Si se sigue este documento, el riesgo pasa de "alto por hard cut" a "medio y controlable".

---

## 14. Checklist de Cierre
- [ ] El contrato de layout esta congelado y sin contradicciones.
- [ ] Existe un resolvedor central de workspace.
- [ ] Los lectores soportan layout nuevo y legacy.
- [ ] El runtime critico ya usa el resolvedor.
- [ ] Setup escribe layout nuevo.
- [ ] IDE y MCP usan rutas nuevas.
- [ ] WebGraph usa rutas nuevas.
- [ ] `doctor`, `hint`, reporting y `.gitignore` estan alineados.
- [ ] La documentacion explica el layout nuevo.
- [ ] La suite cubre nuevo + legacy.
- [ ] El layout nuevo puede activarse por defecto.
- [ ] La compatibilidad legacy queda programada para retiro posterior, no inmediato.

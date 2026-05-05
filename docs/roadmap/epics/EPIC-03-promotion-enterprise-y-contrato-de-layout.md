# EPIC-03 - Promotion enterprise y contrato de layout

> Importante: marcar cada tarea completada en este archivo.
> Al cerrar la epica, completar [EPIC-03-promotion-enterprise-y-contrato-de-layout-REALIZACION.md](./EPIC-03-promotion-enterprise-y-contrato-de-layout-REALIZACION.md).
> Esta es la epica de mayor complejidad del roadmap actual. No ejecutar tareas fuera del orden definido abajo.
> Para ejecucion autonoma sin supervision, usar tambien [EPIC-03-promotion-enterprise-y-contrato-de-layout-EJECUCION.md](./EPIC-03-promotion-enterprise-y-contrato-de-layout-EJECUCION.md).

## Motivo de complejidad

Esta epica es la mas riesgosa para un agente autonomo porque combina al mismo tiempo:

- reglas de negocio del pipeline de promotion;
- compatibilidad entre layout nuevo y layout legacy;
- persistencia de records idempotentes;
- validacion documental;
- comandos CLI que consumen el servicio;
- tests de integracion que dependen de todo lo anterior.

Un cambio incorrecto puede dejar el sistema en un estado donde:

- no se descubren candidatos;
- se descubren con paths incorrectos;
- se promueven al vault equivocado;
- la review deja de respetar fingerprints;
- los tests pasan parcialmente pero el contrato CLI queda roto.

## Objetivo

Hacer que el pipeline de promotion enterprise funcione igual de bien con layout nuevo y legacy, sin redescubrir paths con reglas inconsistentes y sin introducir cambios de contrato no intencionales.

## Falla observada al iniciar la epica

Baseline verificado sobre el repo actual:

- `pytest -q tests/integration/enterprise/test_promotion_e2e.py` falla en los tres escenarios.
- El sintoma comun actual es que `KnowledgePromotionService.discover_candidates()` devuelve `[]`.
- Antes de cambiar nada, asumir que el problema puede estar repartido entre:
  - autodeteccion de layout en repos temporales bootstrap;
  - reuse inconsistente de `WorkspaceLayout` dentro del servicio;
  - fixtures de prueba que mezclan convenciones legacy y new-layout.

## Protocolo de ejecucion para agente autonomo

### Reglas duras

- No editar documentacion funcional hasta que los tests de promotion esten verdes.
- No cambiar a la vez reglas de negocio y naming de modelos si no es estrictamente necesario.
- No tocar `PromotionRecord`, `PromotionCandidate` o `PromotionDecision` salvo que un test o el contrato lo exija.
- No mover `records.jsonl` a otra ubicacion sin actualizar antes `WorkspaceLayout` y los tests correspondientes.
- No asumir que `project_root` significa siempre lo mismo: en esta epica el concepto correcto a respetar es el ya resuelto por `WorkspaceLayout`.

### Secuencia obligatoria

1. Leer y entender el estado actual del servicio.
2. Reproducir la falla de integracion.
3. Corregir primero la fuente de verdad de layout dentro de `KnowledgePromotionService`.
4. Recien despues ajustar contratos auxiliares de layout/config.
5. Recien despues endurecer o ampliar tests.
6. Recien al final actualizar documentacion de realizacion.

### Comandos de control sugeridos

Ejecutar en este orden:

```powershell
pytest -q tests/integration/enterprise/test_promotion_e2e.py
pytest -q tests/unit/enterprise/test_promotion_records.py
pytest -q tests/unit/enterprise/test_promotion_rules.py
pytest -q tests/unit/workspace/test_layout.py
```

Luego, al final:

```powershell
pytest -q
```

---

## Historia de usuario 1

**Como** maintainer del promotion pipeline  
**Quiero** que `KnowledgePromotionService` reuse el layout ya resuelto  
**Para** evitar que discovery, review y promotion se ejecuten con paths divergentes.

### Tarea 3.1 - Diagnosticar y congelar el punto exacto de inconsistencia

**Archivos a leer antes de tocar nada**

- `cortex/enterprise/knowledge_promotion.py`
- `cortex/enterprise/config.py`
- `cortex/workspace/layout.py`
- `tests/integration/enterprise/test_promotion_e2e.py`

**Dependencias a tener presentes**

- `cortex/doc_validator.py`
- `cortex/enterprise/promotion_models.py`
- `tests/unit/enterprise/test_promotion_records.py`
- `tests/unit/enterprise/test_promotion_rules.py`

**Checklist**

- [x] Ejecutar `pytest -q tests/integration/enterprise/test_promotion_e2e.py` y confirmar la falla actual.
- [x] Ubicar la llamada exacta a `load_enterprise_config()` dentro de `discover_candidates()`.
- [x] Verificar que `from_project_root()` si usa `WorkspaceLayout` y que `discover_candidates()` no conserva ese mismo contexto.
- [x] Confirmar por lectura de codigo si `self.paths.local_vault` apunta al vault correcto mientras la carga de config no.
- [x] Registrar en el archivo de realizacion el diagnostico antes de hacer la correccion.

### Tarea 3.2 - Introducir una unica fuente de verdad de layout dentro del servicio

**Archivo principal a cambiar**

- `cortex/enterprise/knowledge_promotion.py`

**Dependencias que deben revisarse o corregirse por arrastre**

- `cortex/enterprise/config.py`
- `cortex/workspace/layout.py`
- `cortex/cli/main.py`

**Implementacion obligatoria**

- El servicio debe conservar el `WorkspaceLayout` resuelto al crearse.
- `discover_candidates()`, `review()`, `plan_promotion()` y `apply_promotion()` no deben redescubrir layout por caminos paralelos.
- La carga de enterprise config debe usar el layout ya resuelto, no recalcular desde `project_root` a ciegas.

**Checklist**

- [x] Ampliar el constructor de `KnowledgePromotionService` para almacenar `workspace_layout`.
- [x] Ajustar `from_project_root()` para pasar el layout al servicio.
- [x] Reemplazar en `discover_candidates()` la carga de config sin layout por una carga layout-aware.
- [x] Revisar cualquier otro punto del servicio que vuelva a inferir roots desde `self.paths.project_root`.
- [x] Verificar que `self.paths` siga siendo coherente y que no haga falta duplicar roots dentro del servicio.

### Tarea 3.3 - Confirmar que el contrato externo del servicio no cambie

**Archivos principales a revisar**

- `cortex/enterprise/knowledge_promotion.py`
- `cortex/cli/main.py`

**Dependencias que deben revisarse**

- `tests/integration/enterprise/test_promotion_e2e.py`
- `tests/unit/cli/test_main.py`

**Checklist**

- [x] Confirmar que `KnowledgePromotionService.from_project_root()` siga siendo el punto de entrada publico.
- [x] Confirmar que `service.paths.local_vault`, `service.paths.enterprise_vault` y `service.paths.records_path` sigan disponibles sin cambios de nombre.
- [x] Confirmar que `review()`, `plan_promotion()` y `apply_promotion()` mantengan sus firmas actuales.
- [x] Confirmar que comandos CLI existentes no requieran adaptaciones de argumento por este cambio.

---

## Historia de usuario 2

**Como** maintainer del layout de workspace  
**Quiero** que promotion tenga un contrato explicito para modo new y legacy  
**Para** que la semantica de `vault`, `vault-enterprise` y `records.jsonl` sea predecible.

### Tarea 3.4 - Verificar y consolidar el contrato de `promotion_records_path`

**Archivos principales a cambiar**

- `cortex/workspace/layout.py`

**Dependencias que deben revisarse o corregirse por arrastre**

- `cortex/enterprise/knowledge_promotion.py`
- `tests/unit/workspace/test_layout.py`
- `tests/unit/enterprise/test_promotion_records.py`

**Checklist**

- [x] Verificar que `promotion_records_path` refleje correctamente el contrato esperado en layout new.
- [x] Verificar que `promotion_records_path` refleje correctamente el contrato esperado en layout legacy.
- [x] Si hace falta ajustar la implementacion, hacerlo en `WorkspaceLayout` y nunca hardcodeando paths desde el servicio.
- [x] Revisar si `promotion_dir` sigue siendo derivado correcto una vez fijado `promotion_records_path`.
- [x] Mantener comentarios del modulo alineados con el comportamiento final.

### Tarea 3.5 - Revisar helpers de config enterprise que participan del flujo

**Archivos principales a cambiar**

- `cortex/enterprise/config.py`

**Dependencias que deben revisarse o corregirse por arrastre**

- `cortex/workspace/layout.py`
- `cortex/enterprise/knowledge_promotion.py`
- `tests/unit/enterprise/test_config.py`

**Checklist**

- [x] Confirmar que `load_enterprise_config()` se comporte igual con layout explicito y sin layout explicito.
- [x] Confirmar que `discover_enterprise_config_path()` no reintroduzca una convencion legacy en un flujo new-layout.
- [x] Confirmar que `write_enterprise_config()` siga escribiendo en la ruta correcta para ambos layouts.
- [x] Revisar `describe_enterprise_topology()` solo si el cambio de layout afecta su salida o paths resueltos.

---

## Historia de usuario 3

**Como** maintainer del flujo enterprise  
**Quiero** que los tests expresen el comportamiento correcto de candidate, review y promotion  
**Para** proteger el pipeline de futuras regresiones.

### Tarea 3.6 - Reparar primero los tests de integracion existentes

**Archivos principales a cambiar**

- `tests/integration/enterprise/test_promotion_e2e.py`

**Dependencias que deben revisarse o corregirse por arrastre**

- `cortex/enterprise/knowledge_promotion.py`
- `cortex/workspace/layout.py`
- `cortex/enterprise/config.py`

**Checklist**

- [x] Reejecutar `pytest -q tests/integration/enterprise/test_promotion_e2e.py` despues del fix base.
- [x] No modificar asserts hasta confirmar si el comportamiento esperado era correcto y la implementacion estaba mal.
- [x] Mantener los tres escenarios actuales:
  - idempotencia de promotion;
  - re-review al cambiar fingerprint;
  - rechazo de review ante errores de validacion.
- [x] Si un test necesita cambio, dejarlo limitado a reflejar el contrato correcto de layout y no a maquillar el bug.

### Tarea 3.7 - Agregar cobertura explicita de layout new y legacy

**Archivos principales a cambiar**

- `tests/integration/enterprise/test_promotion_e2e.py`
- `tests/unit/workspace/test_layout.py`

**Dependencias que deben revisarse o corregirse por arrastre**

- `cortex/enterprise/knowledge_promotion.py`
- `cortex/workspace/layout.py`

**Checklist**

- [x] Agregar un escenario de promotion sobre layout legacy.
- [x] Agregar un escenario de promotion sobre layout new con `.cortex/workspace.yaml`.
- [x] Confirmar en ambos escenarios el valor de `service.paths.local_vault`.
- [x] Confirmar en ambos escenarios el valor de `service.paths.enterprise_vault`.
- [x] Confirmar en ambos escenarios la ubicacion del `records.jsonl`.

### Tarea 3.8 - Proteger reglas de repositorio y records append-only

**Archivos principales a cambiar**

- `tests/unit/enterprise/test_promotion_records.py`
- `tests/unit/enterprise/test_promotion_rules.py`

**Dependencias que deben revisarse o corregirse por arrastre**

- `cortex/enterprise/knowledge_promotion.py`
- `cortex/enterprise/promotion_models.py`

**Checklist**

- [x] Confirmar que `PromotionRepository.load_latest_by_origin_id()` siga devolviendo el ultimo estado por `origin_id`.
- [x] Confirmar que `PromotionRulesEngine` siga excluyendo `sessions/` por default.
- [x] Confirmar que metadata interna `.cortex/` siga excluida de promotion.
- [x] Agregar tests solo si surge una nueva regla por la correccion de layout.

---

## Orden de ejecucion granular recomendado

Este orden no debe cambiarse:

### Fase A - Reproduccion y lectura

- [x] Leer `cortex/enterprise/knowledge_promotion.py` completo.
- [x] Leer `cortex/enterprise/config.py` completo.
- [x] Leer `cortex/workspace/layout.py` completo.
- [x] Ejecutar `pytest -q tests/integration/enterprise/test_promotion_e2e.py`.

### Fase B - Fix minimo en servicio

- [x] Hacer que el servicio conserve `WorkspaceLayout`.
- [x] Pasar ese layout desde `from_project_root()`.
- [x] Reusar ese layout en `discover_candidates()`.
- [x] Reejecutar `pytest -q tests/integration/enterprise/test_promotion_e2e.py`.

### Fase C - Contrato de layout

- [x] Revisar `promotion_records_path` en `WorkspaceLayout`.
- [x] Ajustar tests de layout si el contrato real queda explicitado mejor.
- [x] Ejecutar `pytest -q tests/unit/workspace/test_layout.py`.

### Fase D - Estabilizacion de tests de support

- [x] Ejecutar `pytest -q tests/unit/enterprise/test_promotion_records.py`.
- [x] Ejecutar `pytest -q tests/unit/enterprise/test_promotion_rules.py`.
- [x] Corregir solo si aparece una regresion real causada por el fix de layout.

### Fase E - Cobertura adicional

- [x] Agregar escenarios explicitos new/legacy.
- [x] Reejecutar `pytest -q tests/integration/enterprise/test_promotion_e2e.py`.

### Fase F - Cierre

- [x] Ejecutar `pytest -q`.
- [x] Completar el archivo `EPIC-03-...-REALIZACION.md`.
- [x] Marcar todos los checks de esta epica.

---

## Criterio de finalizacion estricta

La epica solo puede cerrarse cuando:

- [x] `tests/integration/enterprise/test_promotion_e2e.py` queda verde.
- [x] `tests/unit/enterprise/test_promotion_records.py` queda verde.
- [x] `tests/unit/enterprise/test_promotion_rules.py` queda verde.
- [x] `tests/unit/workspace/test_layout.py` queda verde.
- [x] `pytest -q` no presenta fallas atribuibles al flujo de promotion/layout.
- [x] El archivo de realizacion de la epica fue completado.

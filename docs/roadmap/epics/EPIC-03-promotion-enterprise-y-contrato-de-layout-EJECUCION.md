# EPIC-03 - Ejecucion autonoma detallada

> Importante: marcar cada tarea completada en este archivo a medida que se realiza.
> No cerrar la epica solo con cambios de codigo. Esta guia exige validar cada decision con tests y dejar evidencia minima en el archivo de realizacion de la epica.
> Esta guia complementa, no reemplaza, a [EPIC-03-promotion-enterprise-y-contrato-de-layout.md](./EPIC-03-promotion-enterprise-y-contrato-de-layout.md).

## Por que esta guia existe

Esta epica es la mas peligrosa para un agente autonomo porque hay mas de un punto donde se puede "hacer pasar verde" el flujo rompiendo el contrato real:

- se puede tocar `WorkspaceLayout.discover()` y alterar semantica global del repo;
- se puede tocar `KnowledgePromotionService` y ocultar una inconsistencia de layout;
- se pueden reescribir tests de integracion para que sigan la implementacion rota;
- se puede mezclar new-layout y legacy dentro del mismo fixture sin notar la contradiccion.

Por eso esta ejecucion tiene gates. Si un gate no esta resuelto, no avanzar al siguiente.

## Complejidad comparativa

EPIC-03 tiene mayor complejidad que las otras epicas activas porque:

- EPIC-01 es principalmente consistencia de metadata y narrativa;
- EPIC-02 tiene dos bugs acotados, con superficies bien delimitadas;
- EPIC-04 es amplia, pero modular y desacoplable por modulo;
- EPIC-05 es documental y de bajo riesgo funcional;
- EPIC-03 cruza layout, promotion, config, validacion y tests integrados en una sola cadena.

## Regla base de trabajo

No corregir codigo y tests al mismo tiempo sin haber escrito antes cual es el contrato que se quiere preservar.

Si un test y la implementacion se contradicen, primero decidir cual de estos representa el contrato correcto:

- `WorkspaceLayout.discover()`
- `KnowledgePromotionService.from_project_root()`
- `write_enterprise_config()`
- `tests/integration/enterprise/test_promotion_e2e.py`

La decision debe quedar resumida en el archivo `EPIC-03-promotion-enterprise-y-contrato-de-layout-REALIZACION.md`.

## Baseline que debe reproducirse primero

### Comando obligatorio

```powershell
pytest -q tests/integration/enterprise/test_promotion_e2e.py
```

### Resultado esperado al inicio

- 3 fallas.
- Sintoma principal:
  - `assert len(candidates) == 1`
  - valor real: `0`

## Mapa exacto del problema a inspeccionar

### Archivos primarios

- `cortex/enterprise/knowledge_promotion.py`
- `cortex/workspace/layout.py`
- `cortex/enterprise/config.py`
- `tests/integration/enterprise/test_promotion_e2e.py`
- `tests/unit/workspace/test_layout.py`

### Funciones y propiedades exactas a leer

- `KnowledgePromotionService.__init__`
- `KnowledgePromotionService.from_project_root`
- `KnowledgePromotionService.discover_candidates`
- `KnowledgePromotionService.review`
- `KnowledgePromotionService.plan_promotion`
- `KnowledgePromotionService.apply_promotion`
- `WorkspaceLayout.discover`
- `WorkspaceLayout.vault_path`
- `WorkspaceLayout.enterprise_vault_path`
- `WorkspaceLayout.promotion_records_path`
- `load_enterprise_config`
- `write_enterprise_config`

### Hecho tecnico ya verificado

Hoy existen dos focos concretos que el agente debe tratar como sospechosos reales:

1. `KnowledgePromotionService.discover_candidates()` vuelve a llamar `load_enterprise_config(self.paths.project_root, required=True)` sin reutilizar el `WorkspaceLayout` ya resuelto.
2. `WorkspaceLayout.discover()` cae a bootstrap new-layout cuando no encuentra `config.yaml` de raiz ni `.git`, aunque el fixture haya creado `vault/` en raiz y `org.yaml` via `write_enterprise_config()`.

## Gate 1 - Decidir el contrato de repos bootstrap

Antes de editar codigo, resolver esta pregunta:

Cuando existe un repo temporal con:

- `repo/.cortex/org.yaml`
- `repo/vault/...`
- `repo/vault-enterprise/...`
- sin `repo/config.yaml`
- sin `repo/.git`
- sin `repo/.cortex/workspace.yaml`

que layout deberia asumir el sistema?

### Archivos a inspeccionar para decidir

- `cortex/workspace/layout.py`
- `tests/unit/workspace/test_layout.py`
- `tests/integration/enterprise/test_promotion_e2e.py`
- `cortex/enterprise/config.py`

### Salidas validas de este gate

- Opcion A:
  El contrato correcto es "bootstrap repo sin senales explicitas cae a new-layout".

- Opcion B:
  El contrato correcto es "si hay `vault/` y `vault-enterprise/` en raiz, ese repo debe considerarse legacy o resolverse de forma compatible".

### Regla de seguridad

No avanzar hasta elegir una de las dos opciones y documentarla.

### Checklist del gate

- [x] Releer `WorkspaceLayout.discover()` completo.
- [x] Verificar como `write_enterprise_config()` arma el fixture fisico.
- [x] Confirmar donde escribe `KnowledgePromotionService.from_project_root()` el `local_vault`.
- [x] Registrar en el archivo de realizacion si el contrato elegido sera A o B.

## Gate 2 - Corregir la inconsistencia interna del servicio

Este gate se ejecuta siempre, independientemente de si el Gate 1 termina en A o en B.

### Archivo principal a cambiar

- `cortex/enterprise/knowledge_promotion.py`

### Dependencias a revisar por arrastre

- `cortex/enterprise/config.py`
- `cortex/workspace/layout.py`
- `tests/integration/enterprise/test_promotion_e2e.py`

### Objetivo exacto

Eliminar del servicio cualquier segundo camino de resolucion de layout que pueda divergir del layout ya descubierto al construir el servicio.

### Cambios esperados

- el servicio debe conservar el `WorkspaceLayout` resuelto;
- `from_project_root()` debe pasar ese layout al constructor;
- `discover_candidates()` no debe recalcular config por un camino ciego;
- si otra funcion vuelve a inferir layout desde `self.paths.project_root`, debe corregirse tambien.

### Checklist del gate

- [x] Modificar `KnowledgePromotionService.__init__` para aceptar y guardar `workspace_layout`.
- [x] Ajustar `KnowledgePromotionService.from_project_root()` para pasar `workspace_layout=layout`.
- [x] Cambiar `discover_candidates()` para cargar enterprise config con el layout ya guardado.
- [x] Revisar `review()`, `plan_promotion()` y `apply_promotion()` y confirmar que no reabren la misma inconsistencia por otra via.

## Gate 3 - Resolver la ambiguedad fixture vs layout

Este gate depende del resultado del Gate 1.

### Si el contrato elegido fue A

Entonces el repo bootstrap del test debe explicitar new-layout.

#### Archivos a cambiar

- `tests/integration/enterprise/test_promotion_e2e.py`

#### Dependencias a revisar

- `tests/unit/workspace/test_layout.py`
- `cortex/workspace/layout.py`
- `cortex/enterprise/config.py`

#### Cambios obligatorios

- crear `.cortex/workspace.yaml` con `layout_version >= 2`, o
- crear los documentos de prueba bajo `.cortex/vault/`, no bajo `vault/` en raiz, o
- adaptar el fixture de forma equivalente pero siempre consistente con new-layout.

#### Prohibiciones

- No meter hacks dentro de `KnowledgePromotionService` solo para buscar primero en `vault/` y despues en `.cortex/vault/`.
- No dejar un fixture parcialmente legacy y parcialmente new-layout.

### Si el contrato elegido fue B

Entonces la autodeteccion o la creacion del servicio deben respetar esa compatibilidad legacy.

#### Archivos a cambiar

- `cortex/workspace/layout.py`
- posiblemente `tests/unit/workspace/test_layout.py`

#### Dependencias a revisar

- `cortex/enterprise/knowledge_promotion.py`
- `tests/integration/enterprise/test_promotion_e2e.py`
- `tests/unit/workspace/test_layout.py`

#### Cambios obligatorios

- hacer explicito en `WorkspaceLayout.discover()` por que ese fixture debe leerse como legacy o compatible;
- agregar o ajustar test unitario que demuestre esa regla;
- confirmar que el cambio no rompe la deteccion ya cubierta para new-layout con `workspace.yaml`.

#### Prohibiciones

- No resolver el caso solo inyectando un layout manual en el test si el runtime real seguiria ambiguo.
- No cambiar `vault_path` o `enterprise_vault_path` para todos los layouts si el problema es solo de descubrimiento.

## Gate 4 - Validar records y promotion path

### Archivos a verificar

- `cortex/workspace/layout.py`
- `tests/unit/workspace/test_layout.py`
- `tests/unit/enterprise/test_promotion_records.py`

### Objetivo exacto

Confirmar que la ubicacion del archivo `records.jsonl` sigue siendo correcta y consistente con el layout final elegido.

### Checklist del gate

- [x] Verificar `WorkspaceLayout.promotion_records_path` para new-layout.
- [x] Verificar `WorkspaceLayout.promotion_records_path` para legacy.
- [x] Verificar que `PromotionRepository` siga operando con append-only.
- [x] Verificar que no se cambie la estructura del record ni el formato JSONL.

## Gate 5 - Rehabilitar tests existentes antes de ampliar cobertura

### Orden obligatorio

1. `pytest -q tests/integration/enterprise/test_promotion_e2e.py`
2. `pytest -q tests/unit/workspace/test_layout.py`
3. `pytest -q tests/unit/enterprise/test_promotion_records.py`
4. `pytest -q tests/unit/enterprise/test_promotion_rules.py`

### Regla

No agregar tests nuevos mientras alguno de esos cuatro bloques siga rojo por esta epica.

### Checklist del gate

- [x] Dejar verde `test_promotion_pipeline_review_then_promote_is_idempotent`.
- [x] Dejar verde `test_promotion_requires_re_review_when_content_changes`.
- [x] Dejar verde `test_review_rejects_documents_with_validation_errors`.
- [x] Verificar que los tests unitarios de layout no hayan quedado en contradiccion con el contrato final.

## Gate 6 - Recien ahora ampliar cobertura

### Archivos principales a cambiar

- `tests/integration/enterprise/test_promotion_e2e.py`
- `tests/unit/workspace/test_layout.py`

### Cobertura adicional recomendada

- caso legacy explicito y completo;
- caso new-layout explicito con `.cortex/workspace.yaml`;
- asercion explicita de `service.paths.local_vault`;
- asercion explicita de `service.paths.enterprise_vault`;
- asercion explicita de `service.paths.records_path`.

### Checklist del gate

- [x] Agregar un escenario de promotion legacy completamente consistente.
- [x] Agregar un escenario de promotion new-layout completamente consistente.
- [x] Asegurar que cada escenario tenga sus rutas fisicas alineadas con su layout.

## Secuencia de ejecucion exacta

### Paso 1 - Reproduccion

- [x] Ejecutar `pytest -q tests/integration/enterprise/test_promotion_e2e.py`.
- [x] Copiar el sintoma principal al archivo de realizacion.

### Paso 2 - Lectura dirigida

- [x] Leer `KnowledgePromotionService.from_project_root`.
- [x] Leer `KnowledgePromotionService.discover_candidates`.
- [x] Leer `WorkspaceLayout.discover`.
- [x] Leer `write_enterprise_config`.
- [x] Leer el fixture implicito de `test_promotion_e2e.py`.

### Paso 3 - Decision contractual

- [x] Resolver Gate 1.
- [x] Escribir en el archivo de realizacion si el contrato final sera A o B.

### Paso 4 - Fix de servicio

- [x] Resolver Gate 2.
- [x] Reejecutar `pytest -q tests/integration/enterprise/test_promotion_e2e.py`.

### Paso 5 - Fix de layout o fixture

- [x] Resolver Gate 3 segun A o B.
- [x] Reejecutar `pytest -q tests/integration/enterprise/test_promotion_e2e.py`.

### Paso 6 - Verificacion de records

- [x] Resolver Gate 4.
- [x] Ejecutar `pytest -q tests/unit/workspace/test_layout.py`.
- [x] Ejecutar `pytest -q tests/unit/enterprise/test_promotion_records.py`.

### Paso 7 - Reglas de promotion

- [x] Ejecutar `pytest -q tests/unit/enterprise/test_promotion_rules.py`.
- [x] Corregir solo si aparece una regresion real causada por los cambios anteriores.

### Paso 8 - Cobertura adicional

- [x] Resolver Gate 6.
- [x] Reejecutar `pytest -q tests/integration/enterprise/test_promotion_e2e.py`.

### Paso 9 - Cierre de epica

- [x] Ejecutar `pytest -q`.
- [x] Completar `EPIC-03-promotion-enterprise-y-contrato-de-layout-REALIZACION.md`.
- [x] Marcar checks en la epica principal y en esta guia.

## Condiciones de stop

Detener la ejecucion y reevaluar si ocurre cualquiera de estas situaciones:

- un cambio en `WorkspaceLayout.discover()` rompe tests no relacionados con promotion;
- para dejar verde la integracion hace falta cambiar a la vez `WorkspaceLayout`, `KnowledgePromotionService` y los asserts del test sin poder justificar cada cambio por separado;
- el agente necesita introducir fallback dual `vault/` y `.cortex/vault/` dentro del servicio;
- hay que tocar `PromotionRecord`, `PromotionCandidate` o `PromotionDecision` sin que exista una falla que lo exija.

## Criterio de cierre para agente autonomo

No considerar terminada la epica hasta que se cumpla todo:

- [x] existe una sola explicacion contractual de por que el fixture corre en legacy o en new-layout;
- [x] `KnowledgePromotionService` ya no recalcula config ignorando el layout resuelto;
- [x] `tests/integration/enterprise/test_promotion_e2e.py` queda verde;
- [x] `tests/unit/workspace/test_layout.py` queda verde;
- [x] `tests/unit/enterprise/test_promotion_records.py` queda verde;
- [x] `tests/unit/enterprise/test_promotion_rules.py` queda verde;
- [x] el archivo de realizacion documenta la decision tomada y los archivos modificados.

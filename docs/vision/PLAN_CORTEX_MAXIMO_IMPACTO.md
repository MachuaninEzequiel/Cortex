# Plan de Accion Validado - Cortex

> Documento reescrito a partir de una validacion contra el codigo real del repositorio, la documentacion local y la ejecucion de `pytest -q` el 2026-05-05.
> Este archivo reemplaza el plan anterior generado externamente y corrige supuestos que ya no representan el estado actual del proyecto.
> Carpeta propuesta para el desglose futuro en epicas, historias y tareas: `docs/roadmap/`.

---

## 1. Contexto y objetivo

El plan anterior estaba bien orientado en varios frentes, pero mezclaba problemas reales con supuestos desactualizados. El objetivo de esta version es dejar un roadmap que:

- priorice los problemas comprobados hoy en el repositorio;
- descarte iniciativas que ya estan parcialmente implementadas;
- agregue puntos debiles que el plan anterior no contemplaba;
- indique rutas exactas donde deben hacerse los cambios.

La validacion se realizo contrastando:

- empaquetado y metadata (`pyproject.toml`, `cortex/__init__.py`, `README.md`);
- arquitectura principal (`cortex/core.py`, `cortex/mcp/server.py`, `cortex/enterprise/*`);
- documentacion operativa (`docs/guides/*`, `docs/vision/*`);
- workflows de CI (`.github/workflows/*`);
- estado de pruebas (`pytest -q`).

---

## 2. Veredicto sobre el plan anterior

| Tema del plan anterior | Veredicto | Ajuste necesario |
| --- | --- | --- |
| I1 - versionado y madurez | Correcto, pero incompleto | El problema es mas grave: hoy hay inconsistencia entre `pyproject.toml`, `README.md` y `cortex.__version__`. |
| I2 - activar CI publico con badges | Fuera del plan actual | El repo ya tiene workflows y perfiles. No hace falta tocar esta linea en la ejecucion inmediata. |
| I3 - refactor de `AgentMemory` a DI real | Valido, pero no prioritario | Es una mejora estructural util, aunque costosa para el beneficio inmediato. Conviene dejarla como observacion futura. |
| I4 - threat model MCP y validacion de paths | Correcto | Sigue siendo una deuda real y todavia no aparece implementada de forma transversal. |
| I5 - sincronizar README y docs de API | Parcialmente correcto | Ya existe un arbol de `docs/`, pero hay drift fuerte entre README, guias y layout/configuracion reales. El problema no es "falta total de docs", sino inconsistencia documental. |

### Lo que el plan anterior no cubria y hoy debe ser prioridad

1. La suite actual no esta en verde: `pytest -q` falla en 5 tests.
2. El pipeline de promotion enterprise no esta descubriendo candidatos en escenarios cubiertos por tests.
3. El helper de delegacion MCP no es robusto fuera del constructor completo.
4. La documentacion de configuracion y getting-started no refleja bien el contrato actual de `.cortex/` vs layout legacy.

---

## 3. Debilidades confirmadas y solucion propuesta

### D1. Version, madurez y narrativa publica inconsistentes

**Problema comprobado**

- `pyproject.toml` declara `version = "3.0.0"` y `Development Status :: 5 - Production/Stable`.
- `cortex/__init__.py` expone `__version__ = "0.1.0"`.
- `README.md` publica badges estaticos de `3.0.0`, `>85%` y `CI/CD`, pero eso no coincide con el estado verificable del repo.

**Rutas exactas a cambiar**

- `pyproject.toml`
- `cortex/__init__.py`
- `README.md`
- `CHANGELOG.md`
- `CONTRIBUTING.md`

**Solucion**

1. Definir una unica fuente de verdad para la version publica.
   Comentario: hoy hay dos verdades tecnicas (`3.0.0` y `0.1.0`) y una tercera verdad narrativa en el README.
2. Hacer que `cortex.__version__` derive de la version publicada o quede sincronizada explicitamente con `pyproject.toml`.
3. Reemplazar badges estaticos por badges reales o, si todavia no existe una fuente publica estable, simplificar el encabezado y quitar claims no auditables.
4. Bajar el `Development Status` a un nivel acorde al estado real hasta tener suite verde y documentacion consistente.
5. Registrar en `CHANGELOG.md` la normalizacion de versionado y madurez.

**Criterios de aceptacion**

- `pyproject.toml`, `cortex.__version__` y el README muestran la misma version.
- Desaparecen claims no verificables de cobertura/CI del encabezado.
- `CHANGELOG.md` deja trazada la decision de version y madurez.

---

### D2. La suite de pruebas no esta estable y el plan anterior no lo prioriza

**Problema comprobado**

`pytest -q` falla hoy en:

- `tests/integration/enterprise/test_promotion_e2e.py`
- `tests/integration/mcp/test_server.py`
- `tests/unit/enterprise/test_retrieval_performance.py`

**Rutas exactas a cambiar**

- `cortex/enterprise/knowledge_promotion.py`
- `cortex/mcp/server.py`
- `cortex/enterprise/retrieval_service.py`
- `cortex/enterprise/sources.py`
- `tests/integration/enterprise/test_promotion_e2e.py`
- `tests/integration/mcp/test_server.py`
- `tests/unit/enterprise/test_retrieval_performance.py`

**Solucion**

1. Agregar una iniciativa explicita de estabilizacion antes de refactors grandes.
2. Corregir primero los fallos funcionales y de contrato, no los tests.
3. Usar la suite actual como lista de regresion minima antes de tocar refactors estructurales.

**Criterios de aceptacion**

- `pytest -q` pasa en local.
- Los tests fallidos quedan cubiertos por la misma suite sin marcarse como skip.

---

### D3. El promotion pipeline enterprise necesita correccion funcional

**Problema comprobado**

El codigo de promotion no esta resolviendo bien el descubrimiento de candidatos en los escenarios cubiertos por la suite de integracion. Hoy esa debilidad es mas urgente que agregar mas documentacion enterprise.

**Rutas exactas a cambiar**

- `cortex/enterprise/knowledge_promotion.py`
- `cortex/workspace/layout.py`
- `cortex/enterprise/config.py`
- `tests/integration/enterprise/test_promotion_e2e.py`
- `tests/unit/enterprise/test_promotion_records.py`
- `tests/unit/enterprise/test_promotion_rules.py`

**Solucion**

1. Unificar la resolucion de paths en `discover_candidates()` con el mismo `WorkspaceLayout` utilizado por `from_project_root()`.
   Comentario: el servicio no deberia redescubrir configuracion con reglas distintas una vez que ya resolvio layout y paths.
2. Revisar si el contrato soportado es layout nuevo, layout legacy o ambos, y documentarlo sin ambiguedad.
3. Asegurar que la promocion use consistentemente `local_vault`, `enterprise_vault` y `records_path` ya resueltos.
4. Añadir tests de regresion para:
   - proyecto legacy;
   - proyecto nuevo con `.cortex/`;
   - cambio de contenido que fuerce re-review;
   - documento invalido que no pueda aprobarse.

**Criterios de aceptacion**

- `discover_candidates()` encuentra documentos promocionables en los escenarios de prueba existentes.
- El flujo `candidate -> reviewed -> promoted` vuelve a ser idempotente.

---

### D4. Seguridad de escritura y paths sigue siendo una deuda transversal real

**Problema comprobado**

El plan anterior acierta en esta area: las superficies MCP, documentacion y vault siguen necesitando validacion defensiva de paths y un threat model publicado.

**Rutas exactas a cambiar**

- `cortex/mcp/server.py`
- `cortex/semantic/vault_reader.py`
- `cortex/documentation.py`
- `cortex/workitems/service.py`
- `cortex/runtime_context.py`
- `cortex/services/session_service.py`
- `cortex/services/spec_service.py`
- `SECURITY.md`
- `docs/security/threat-model.md`
- `tests/unit/test_security_paths.py` o `tests/unit/security/test_paths.py`

**Solucion**

1. Crear una utilidad comun de resolucion segura de paths bajo `workspace_root` o `vault_path`.
2. Usarla en cualquier operacion que construya rutas a partir de strings externos o semi-externos.
3. Bloquear traversal y rutas absolutas fuera del workspace.
4. Publicar `SECURITY.md` y el threat model con alcance realista.
5. Agregar tests parametrizados con intentos de escape de ruta.

**Criterios de aceptacion**

- Ninguna escritura o lectura sensible aceptada desde CLI/MCP puede escapar del root permitido.
- Existe `SECURITY.md` con politicas y threat model.

---

### D5. La documentacion existe, pero no representa de forma consistente el contrato actual

**Problema comprobado**

No falta documentacion en bruto: ya hay `docs/guides/`, `docs/ops/`, `docs/enterprise/`, `docs/review/` y `docs/vision/`. El problema real es drift entre:

- `README.md`
- `docs/guides/getting-started.md`
- `docs/guides/configuration-reference.md`
- `WorkspaceLayout`
- `CortexConfig`

**Rutas exactas a cambiar**

- `README.md`
- `docs/guides/getting-started.md`
- `docs/guides/configuration-reference.md`
- `docs/guides/enterprise-vault.md`
- `docs/guides/pipeline-setup.md`
- `cortex/core.py`
- `cortex/workspace/layout.py`
- `examples/`

**Solucion**

1. Definir el contrato documental base: donde vive `config.yaml`, donde vive el vault y cual es el layout por defecto.
2. Reescribir `getting-started` y `configuration-reference` para reflejar el schema real actual, no uno historico.
3. Limitar esta iniciativa a consistencia documental operativa.
   Comentario: hoy el riesgo mayor no es "no tener sitio", sino enseñar un setup distinto al que usa el codigo.

**Criterios de aceptacion**

- README y guias no se contradicen entre si.
- Los ejemplos de configuracion coinciden con los modelos reales usados por el codigo.
- El layout nuevo/legacy queda explicado sin ambiguedad.

---

## 4. Roadmap recomendado y orden de ejecucion

### Fase 0 - Recuperar verdad operativa

1. D1 - Unificar version, madurez y narrativa publica.
2. D2 - Recuperar la suite a verde.

### Fase 1 - Corregir contratos rotos del producto

1. D3 - Arreglar promotion pipeline enterprise.
2. D5 - Alinear documentacion con layout y configuracion reales.

### Fase 2 - Reducir riesgo funcional

1. D4 - Seguridad de paths y threat model.

---

## 5. Carpeta recomendada para el plan y su desglose

La carpeta recomendada es:

`docs/roadmap/`

Motivo:

- `docs/vision/` deberia conservarse para documentos estrategicos y de direccion.
- `docs/roadmap/` comunica ejecucion, priorizacion y seguimiento.
- evita mezclar roadmap operativo con manifiestos, arquitectura conceptual o analisis retrospectivo.

### Estructura sugerida

```text
docs/
└── roadmap/
    ├── README.md
    ├── epics/
    ├── user-stories/
    └── tasks/
```

### Convencion sugerida

- `docs/roadmap/README.md`: roadmap maestro y secuencia de fases.
- `docs/roadmap/epics/EPIC-01-versionado-y-estabilidad.md`
- `docs/roadmap/user-stories/US-01-unificar-version-publica.md`
- `docs/roadmap/tasks/TASK-01-alinear-pyproject-y-init.md`

---

## 6. Archivo y rutas concretas que el plan reescrito deja priorizadas

### Prioridad alta inmediata

- `pyproject.toml`
- `cortex/__init__.py`
- `README.md`
- `cortex/enterprise/knowledge_promotion.py`
- `cortex/mcp/server.py`
- `docs/guides/getting-started.md`
- `docs/guides/configuration-reference.md`

### Prioridad media

- `cortex/semantic/vault_reader.py`
- `cortex/documentation.py`
- `cortex/workitems/service.py`
- `cortex/runtime_context.py`
- `cortex/workspace/layout.py`
- `SECURITY.md`
- `docs/security/threat-model.md`

### Pruebas a reforzar

- `tests/integration/enterprise/test_promotion_e2e.py`
- `tests/integration/mcp/test_server.py`
- `tests/unit/enterprise/test_retrieval_performance.py`
- `tests/unit/enterprise/test_core_retrieve_scope.py`
- `tests/unit/test_mcp_server.py`
- `tests/unit/cli/test_main.py`

---

## 7. Criterio de cierre del roadmap

El plan puede considerarse bien encaminado cuando se cumpla todo lo siguiente:

- `pytest -q` pasa en local.
- version publica, version del paquete y narrativa del README coinciden;
- promotion enterprise funciona en layout nuevo y legacy soportado;
- la documentacion ya no enseña un contrato distinto al implementado;
- las rutas de escritura sensibles quedan protegidas por validacion defensiva.

---

## 8. Observaciones futuras fuera del plan actual

Estas lineas quedan mencionadas para mas adelante, pero no forman parte del plan de ejecucion inmediato:

### O1. Endurecimiento de CI y permisos

- Mantener por ahora el modelo actual de perfiles `observability` / `advisory` / `enforced`.
- Si en otra etapa se quiere endurecer la CI, el punto de entrada sigue siendo:
  - `.github/workflows/ci-pull-request.yml`
  - `.github/workflows/ci-enterprise-governance.yml`
  - `.github/workflows/ci-security.yml`
  - `.github/workflows/ci-release.yml`

### O2. Refactor progresivo de `AgentMemory`

- Valoracion breve: es util, pero no urgente.
- Aporta principalmente testabilidad, menor acoplamiento y menor costo de evolucion.
- No bloquea estabilizar el proyecto hoy.
- Dado su costo y su impacto transversal, conviene dejarlo fuera del plan actual y retomarlo solo si vuelve a frenar cambios o pruebas.
- Rutas candidatas si se retomara:
  - `cortex/core.py`
  - `cortex/runtime_context.py`
  - `cortex/cli/main.py`
  - `cortex/mcp/server.py`

### O3. Sitio de documentacion y API reference automatica

- Se descarta por ahora crear un sitio de documentacion.
- Se descarta por ahora agregar API reference automatica.
- Ambas cosas sumarian mantenimiento en una etapa donde primero hace falta pulir contrato, pruebas y comportamiento real.
- Si algun dia se retoma, deberia ser solo despues de que la documentacion operativa ya este totalmente alineada al codigo.

---

## 9. Conclusion

El plan anterior no estaba mal orientado, pero estaba desfasado respecto del repositorio real. Sus principales aciertos eran:

- detectar la deuda de versionado y narrativa publica;
- detectar la falta de hardening de seguridad.

Sus principales errores eran:

- asumir una agenda de CI que hoy no hace falta tocar;
- asumir ausencia de documentacion cuando el problema real es la inconsistencia;
- no priorizar fallas actuales de tests, promotion enterprise y contrato de layout.

La version correcta del roadmap para Cortex no debe empezar por "agregar mas superficie", sino por recuperar coherencia entre codigo, pruebas, versionado, seguridad de paths y documentacion base.

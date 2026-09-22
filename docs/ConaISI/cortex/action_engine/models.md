# cortex/action_engine/models.py

## Qué tiene adentro

- **Ruta de código:** `cortex/action_engine/models.py` (129 líneas).
- **Módulo Python:** `cortex.action_engine.models`.
- **Docstring del módulo:** Modelos del ActionEngine (Obra 05 Fase B, §3.2 del plan).
- **Clases definidas:**
  - `Check`
    - Precondición pura: predicado sin efectos + razón legible si falla.
    - Métodos públicos/especiales: `cumple`
  - `ActionResult`
    - Resultado de ejecutar una acción.
    - Métodos públicos/especiales: `dry`, `fail`
  - `Action`
    - Métodos internos: `__post_init__`
  - `ProposedAction`
    - Una acción que el scheduler ofrece tras evaluar precondiciones.
  - `Decision`
    - Decisión del usuario/aprendizaje sobre una acción propuesta.
- **Funciones de módulo:**
  - `_ahora()`
  - `ahora_iso()`
- **Constantes / símbolos de módulo:** `IMPACTO_BASE`, `COSTO_PENALIZACION`

## Para qué sirve

Modelos del ActionEngine (Obra 05 Fase B, §3.2 del plan).

Contrato duro:
1. Toda acción delega en su servicio — nunca reimplementa lógica.
2. Las precondiciones se evalúan ANTES de ofrecer la acción.
3. ``reversible=False`` ⇒ requiere aprobación SIEMPRE (sin modo auto).
4. Toda ejecución se registra en ``.cortex/action_log.jsonl``.
5. Dry-run nativo: ``run(dry_run=True)`` devuelve el efecto sin escribir.

## Relaciones

### Recibe de

- Dependencias externas/stdlib: `__future__`, `collections.abc`, `dataclasses`, `datetime`, `typing`

### Envía a

- `cortex.action_engine`
- `cortex.action_engine.actions.catalog`
- `cortex.action_engine.registry`
- `cortex.action_engine.runner`
- `cortex.action_engine.scheduler`
- `cortex.tui.core`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 129.

---
Fuente: código de `cortex/action_engine/models.py` (AST + grafo de imports internos). No se usó documentación previa.

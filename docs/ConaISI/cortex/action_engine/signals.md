# cortex/action_engine/signals.py

## Qué tiene adentro

- **Ruta de código:** `cortex/action_engine/signals.py` (85 líneas).
- **Módulo Python:** `cortex.action_engine.signals`.
- **Docstring del módulo:** Señales de feedback real para el score del scheduler (Obra 05 Fase E).
- **Clases definidas:**
  - `MemorySignals`
    - Métodos públicos/especiales: `dominio`
- **Funciones de módulo:**
  - `leer_senales(dot_cortex)` — Lee feedback.jsonl (+rotado) filtrando a la ventana temporal.
  - `multiplicador_categoria(categoria, senales)` — Multiplicador suave (tope ±25%) según dominio del feedback.
  - `_parse_ts(value)`
- **Constantes / símbolos de módulo:** `VENTANA_DIAS_DEFAULT`

## Para qué sirve

Señales de feedback real para el score del scheduler (Obra 05 Fase E).

La marca [y]=útil de la búsqueda TUI (y cualquier feedback explícito
persistido) alimenta la prioridad: dominio negativo ⇒ suben calidad/
mantenimiento (retrieval malo = problemas de índice/docs); dominio
positivo ⇒ suben aprendizaje/conocimiento (usuario comprometido).
Ventana por defecto: 14 días.

## Relaciones

### Recibe de

- Dependencias externas/stdlib: `json`, `__future__`, `dataclasses`, `datetime`, `pathlib`

### Envía a

- `cortex.action_engine.scheduler`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 85.
Docstrings de símbolos públicos:
- `leer_senales`: Lee feedback.jsonl (+rotado) filtrando a la ventana temporal.
- `multiplicador_categoria`: Multiplicador suave (tope ±25%) según dominio del feedback.

---
Fuente: código de `cortex/action_engine/signals.py` (AST + grafo de imports internos). No se usó documentación previa.

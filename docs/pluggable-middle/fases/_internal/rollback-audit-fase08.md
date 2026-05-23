# Rollback transaccional — audit Fase 08 / T8.1

> **Tipo:** scratchpad histórico. Documenta lo que se encontró y restauró
> al ejecutar T8.1 de Fase 08.
> **Fecha:** 2026-05-17
> **Owner del cambio:** `cortex/services/note_service.py::NoteService.create`

---

## 1. Pregunta

¿La pipeline de persistencia del documenter preserva la invariante
**"file en disco ⇒ file indexado en memoria semántica + episódica"**
después de la fusion de Fase 03?

## 2. Hallazgo

**Ausente.** Post-Fase 03, el `NoteService.create` (nuevo owner del flow
persistir + indexar) escribía el `.md` al vault y luego invocaba
`self._semantic.index_file(...)` y `self._store_episodic(...)` **sin
rollback transaccional**. Si cualquiera de los dos pasos fallaba con
excepción, el archivo `.md` quedaba huérfano en disco — invisible para
`cortex search` pero ocupando espacio y confundiendo a futuros lectores
del vault.

El contrato lo enforzaba el eliminado
`cortex/autopilot/session_writer.py::IndexingSessionWriter`, que se quitó
en Fase 03 (audit T3.1, §4) sin portar la lógica al nuevo dueño. El
mismo audit ya lo flagueaba como pendiente: *"verificar al hacer T3.3 si
el DocumenterPersister lo preserva"*. Esa verificación nunca quedó
documentada y la lógica nunca se portó.

## 3. Acción tomada

Portada la lógica al `NoteService.create`. El bloque post-write ahora
está envuelto en `try/except` con `path.unlink(missing_ok=True)` y
re-raise de la excepción original. Si el `unlink` también falla (caso
defensivo), se loguea a `WARNING` y la excepción original sigue
propagando — el caller nunca recibe un éxito silencioso.

**Líneas modificadas:** `cortex/services/note_service.py:158-191`.

## 4. Tests añadidos

`tests/unit/services/test_note_service.py` — 5 casos:

| Test | Verifica |
|---|---|
| `test_indexing_success_preserves_file` | Happy path: el `.md` queda escrito + indexado. |
| `test_indexing_failure_unlinks_persisted_file` | Falla del semantic store ⇒ no quedan `.md` huérfanos. |
| `test_indexing_failure_propagates_exception` | El caller observa la excepción (no éxito silencioso). |
| `test_episodic_failure_also_rolls_back` | Falla del episodic store (post-semantic OK) ⇒ rollback igual. |
| `test_remember_false_skips_episodic_path` | Con `remember=False`, el episodic no se invoca y el `.md` queda escrito. |

## 5. Verificación

```
pytest tests/unit/services/test_note_service.py \
       tests/unit/services/test_note_service_alias.py \
       tests/unit/documenter/test_persistence.py --no-cov -v
# 18 passed, 0 failed

mypy --strict --follow-imports=silent cortex/services/note_service.py
# Success: no issues found

ruff check cortex/services/note_service.py
# All checks passed
```

## 6. Notas para futuras fases

- **Performance:** el `try/except` no agrega overhead en happy path (Python
  catches son free hasta que se lanza la excepción). Sólo el unlink en
  falla, que es I/O barato.
- **Atomicidad:** la atomicidad real es a nivel "persistencia + indexing".
  La indexación interna del `_PathOnlyVault` (en `_write_note` de
  `cortex/documentation/writers.py:345-368`) ya estaba silenciada por
  diseño — esa capa NO interfiere con el rollback nuevo, que sólo cubre
  los pasos explícitos del `NoteService`.
- **Episodic side-effects:** si la `episodic.add` falla pero ya escribió
  parcialmente en su store interno (caso teórico), el rollback del file
  del vault no des-deshace el episodic. Es deuda residual aceptable: la
  invariante crítica es del vault, no del episodic store (que es
  reconstruible).

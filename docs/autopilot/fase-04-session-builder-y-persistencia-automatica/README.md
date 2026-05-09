# Fase 4 - Session Builder y Persistencia Automatica

**Fuente:** `docs/autopilot/README.md`
**Estado:** Pendiente de ejecucion

## Introduccion de la fase

En esta fase se lleva a cabo lo definido en el plan global para `Fase 4 - Session Builder y Persistencia Automatica`. El cuerpo operativo de la fase se copia directamente desde `docs/autopilot/README.md` para mantener la especificacion sin reinterpretaciones.

Al terminar la realizacion de esta fase, es obligatorio documentar lo desarrollado dentro de esta misma carpeta en un archivo `REALIZACION.md`. Esa realizacion debe incluir decisiones tomadas, archivos modificados, tests ejecutados, desviaciones respecto del plan, riesgos residuales y pendientes.

## Nota obligatoria para agentes implementadores

Esta nota baja a esta fase las reglas del item 18 del plan global. Es obligatoria antes de implementar.

### Reglas generales heredadas del item 18

- **No improvises.** Segui el alcance exacto de esta fase y no agregues campos, servicios ni adapters fuera de lo definido.
- **No saltees tests.** La fase no esta completa hasta cumplir su gate de salida.
- **Usa `WorkspaceLayout`.** No hardcodees `.cortex/`, `config.yaml`, `vault/` ni rutas legacy.
- **Cada archivo nuevo debe tener test unitario correspondiente** cuando la fase cree codigo runtime.
- **Si algo no esta claro, pregunta antes de asumir.** La racionalizacion es el enemigo del Autopilot.

### Aplicacion especifica en esta fase

- No inventes informacion de trabajo: renderiza solamente datos observados en estado/eventos.
- Si faltan datos, el resultado debe degradar a `auto-draft` y dejar warnings.
- No dupliques session notes si el estado ya tiene `session_note_path`.
- No hagas full `sync-vault` como cierre default.

## Plan operativo original

## Fase 4 - Session Builder y Persistencia Automatica

### Objetivo

Construir session notes confiables desde estado observado.

### Archivos a crear

```text
cortex/autopilot/session_builder.py
cortex/autopilot/renderers/base.py
cortex/autopilot/renderers/minimal.py
cortex/autopilot/renderers/implementation.py
cortex/autopilot/renderers/docs_only.py
cortex/autopilot/renderers/fallback_draft.py
tests/unit/autopilot/test_session_builder.py
tests/unit/autopilot/test_renderers.py
```

### Contrato de SessionDraft (referencia obligatoria del plan global §7.3)

Los renderers producen un `SessionDraft`, no escriben archivos directamente. El modelo esta definido en `cortex/autopilot/models.py` (creado en Fase 1):

```python
class SessionDraft(BaseModel):
    title: str
    body: str  # markdown formateado
    confidence: Literal["high", "medium", "auto-draft"]
    warnings: list[str] = []  # problemas detectados durante render
    source_events: int  # cuantos eventos se usaron para generar
```

### Renderers (referencia obligatoria del plan global §7.3)

- `MinimalSessionRenderer` — titulo, resumen, archivos. Para tareas simples.
- `ImplementationSessionRenderer` — cambios, decisiones, archivos, spec ref. Para fast-code y deep-code.
- `DocsOnlySessionRenderer` — documentos creados/modificados. Para docs-only.
- `FallbackDraftRenderer` — genera draft seguro con status `auto-draft` cuando faltan datos.

### Self-review automatizado del draft (referencia obligatoria del plan global §7.3.1)

Antes de que `finish()` persista la session note, el `SessionBuilder` debe ejecutar un self-review del draft generado:

1. **Placeholder scan:** Buscar "TBD", "TODO", secciones vacias, o textos genericos.
2. **Consistencia interna:** El titulo coincide con el contenido? Los archivos listados son los mismos que los eventos registraron?
3. **Completitud:** Si hubo eventos de tipo `checkpoint`, estan reflejados en la nota?
4. **Evidencia:** Si hay afirmaciones de "tests pasan" o "build exitoso", hay un evento de verificacion que lo respalde?

Si el self-review encuentra problemas:
- En modo `autopilot`: corregir automaticamente lo que se pueda, marcar el resto como `auto-draft`.
- En modo `assist`: listar los problemas al agente y pedir correccion.
- En modo `observe`: registrar los problemas como warnings sin bloquear.

### Integracion

Usar `AgentMemory.save_session_note()` o `SessionService` por la fachada.

### Reglas de seguridad epistemica

1. Si no se observo un cambio, no se declara como realizado.
2. Si no se ejecutaron tests, se escribe "No registrado".
3. Si no hay spec, se escribe "No se detecto spec asociada".
4. Si el cierre es automatico y falta contexto, status `auto-draft`.

### Checklist

- [ ] Render minimo con titulo, resumen, archivos y eventos.
- [ ] Render implementacion con cambios y decisiones.
- [ ] Render docs-only para tareas de documentacion.
- [ ] `FallbackDraftRenderer` genera draft seguro con confidence `auto-draft`.
- [ ] `finish()` ejecuta self-review antes de persistir.
- [ ] `finish()` marca estado `documented`.
- [ ] `finish()` no duplica session notes si ya existe `session_note_path`.
- [ ] Tests unitarios para cada renderer y para self-review.

### Gate de salida

- Session note util con cero invencion.
- Self-review detecta placeholders y afirmaciones sin evidencia.
- Indexacion selectiva sigue siendo el mecanismo default.

---


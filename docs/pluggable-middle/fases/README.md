# Plan de fases — Implementación de Pluggable Middle

Este directorio contiene el **plan de implementación ejecutable** de la arquitectura Pluggable Middle.

Cada documento de fase está pensado para que un agente de IA pueda ejecutarlo **de forma autónoma**, durante días, sin desviarse del diseño.

---

## 1. Cómo leer este README

**Antes de tocar una sola línea de código, este README debe leerse íntegramente.**

Contiene tres secciones que aplican a TODAS las fases:

1. **Quality Charter** — los estándares no-negociables.
2. **Context Loading Protocol** — qué leer al empezar, siempre.
3. **Cómo ejecutar una fase** — flujo operativo (resume, progress, verificación).

Después de leer este README, abrí la fase correspondiente al estado actual (ver tabla en `../README.md`).

---

## 2. Quality Charter (NO NEGOCIABLE)

Esta sección aplica a TODA fase, TODA tarea, TODA línea de código que escribas.

### 2.1 Principios

1. **Cero deuda técnica.** No "TODO: fix later". No "good enough for now". No "voy a refactorizar después". Si algo no está bien hecho, no está hecho.
2. **Diseño antes que velocidad.** Si una decisión de diseño está poco clara, pará y consultá el documento de arquitectura. Si sigue poco clara, leé código existente. Si sigue poco clara, leé docs externas vía WebFetch. **Nunca improvises.**
3. **Test-driven, sin excepciones.** Toda función pública tiene tests. Tests cubren happy path + edge cases + error cases. Coverage objetivo: **>85%** del módulo nuevo.
4. **Type-safe.** Todo type-hinted. `mypy --strict` debe pasar sobre el código nuevo (no relajado).
5. **Lint clean.** `ruff check` debe pasar limpio. `ruff format` aplicado.
6. **Sin abstracciones especulativas.** No crees una clase base abstracta para "futuras implementaciones". No crees un factory para un solo concrete. Tres usos repetidos justifican una abstracción; menos, no.
7. **Sin código comentado.** Si querés sacar código, sacalo. Git lo recuerda.
8. **Sin print/console.log de debug.** Usá el logger del proyecto.
9. **Frameworks y patrones del proyecto.** Pydantic para schemas, Typer para CLI, pytest para tests, ruff para lint, mypy para types, ChromaDB para vectores. NO introducir dependencias nuevas sin justificación documentada.
10. **Documentación inline solo cuando el "por qué" no es obvio.** Funciones bien nombradas no necesitan docstring que repita el nombre. Pero algoritmos no triviales, invariantes, y workarounds SÍ deben tener explicación.

### 2.2 Lo que NO es aceptable

- ❌ Implementación parcial marcada como "completa".
- ❌ Tests que solo cubren happy path.
- ❌ Funciones de 100+ líneas sin separar.
- ❌ Try/except que silencia errores sin loguearlos.
- ❌ Magic numbers o strings sin constantes nombradas.
- ❌ Duplicación de lógica entre módulos.
- ❌ Acoplamiento que se podría haber evitado con inyección de dependencias.
- ❌ Estado global mutable.
- ❌ Funciones con efectos secundarios no documentados.
- ❌ APIs públicas inconsistentes con el resto del repo.

### 2.3 Cuándo ESTÁ permitido investigar antes de codear

**Siempre.** El agente tiene autorización explícita para:

- **Leer cualquier archivo del repo** con `Read`, `Glob`, `Grep`.
- **Leer documentación externa** vía `WebFetch` (Pydantic docs, Typer docs, pytest docs, FastMCP docs, etc.) cuando haya duda real sobre comportamiento de una librería.
- **Buscar issues/discusiones** en GitHub si una decisión depende del comportamiento histórico de una herramienta.
- **Consultar el git log/blame** si una decisión de diseño previa necesita entenderse antes de cambiar algo.

**Investigar NO es perder tiempo. Inventar SÍ lo es.**

### 2.4 Definition of Done para cualquier tarea

Una tarea está completa solo si:

- [ ] El código escrito está cubierto por tests (happy + edge + error).
- [ ] `pytest <ruta-del-modulo>` pasa al 100%.
- [ ] `mypy --strict <ruta-del-modulo>` no reporta errores.
- [ ] `ruff check <ruta-del-modulo>` no reporta issues.
- [ ] `ruff format <ruta-del-modulo>` aplicado.
- [ ] Cobertura del módulo nuevo > 85% (medido con `pytest --cov`).
- [ ] El código es invocable end-to-end (no fragmento huérfano).
- [ ] Si la tarea expone API pública (MCP tool, CLI command, función), está documentada en el README correspondiente.
- [ ] No quedan TODOs ni FIXMEs.

### 2.5 Definition of Done para una FASE

Una fase está completa solo si:

- [ ] Todas las tareas de la fase cumplen su Definition of Done.
- [ ] Existe al menos un test E2E que valida el escenario completo de la fase.
- [ ] Los **Completion Verification Commands** (al final de cada doc de fase) pasan todos.
- [ ] El changelog del proyecto está actualizado.
- [ ] La tabla de progreso en `../README.md` está actualizada con ✅.
- [ ] Existe un commit (o serie de commits coherentes) que materializa la fase.

---

## 3. Context Loading Protocol

**Al EMPEZAR (o RESUMIR) cualquier fase, leé en este orden:**

### 3.1 Contexto base (siempre, sin excepción)

1. `C:\Cortex\README.md` — para entender qué es Cortex.
2. `C:\Cortex\docs\pluggable-middle\ARQUITECTURA-PLUGGABLE-MIDDLE.md` — el diseño completo. **Esta es la fuente de verdad sobre qué se está construyendo.**
3. `C:\Cortex\docs\pluggable-middle\fases\README.md` — este archivo (Quality Charter + protocolo).
4. `C:\Cortex\docs\pluggable-middle\README.md` — para saber qué fase está activa.

### 3.2 Contexto específico de la fase

Antes de tocar la fase X, leé:

- `C:\Cortex\docs\pluggable-middle\fases\0X-<NOMBRE>.md` — el plan detallado de la fase actual.
- Si X > 0: leé también el README de la fase X−1 al final del documento ("Handoff to next phase") para entender qué se asume que ya existe.

### 3.3 Contexto del repo (leer según necesidad de la tarea)

Cada documento de fase lista en su sección **"Required Reading"** los archivos del repo que necesitás conocer.

Reglas:
- **No asumas la estructura del código.** Si la fase dice "modificar `cortex/services/spec_service.py`", leé ese archivo ANTES de tocarlo.
- **Si una librería externa va a usarse de forma no trivial,** leé su doc oficial vía `WebFetch`. Ejemplos:
  - Pydantic v2 features: https://docs.pydantic.dev/latest/
  - Typer commands: https://typer.tiangolo.com/
  - FastMCP server: la fuente actual en `cortex/mcp/`
- **Si una decisión arquitectónica necesita rastreo:** `git log --oneline -- <archivo>` y `git blame`.

### 3.4 Contexto que se preserva entre fases

Cada fase deja como **output** un set de artefactos que la siguiente puede asumir como dados. Esos outputs están listados al final de cada doc de fase, en la sección **"Handoff to next phase"**.

**Nunca duplique código. Nunca reinvente abstracciones que la fase anterior ya creó. Si dudás, leé los archivos que la fase anterior produjo.**

---

## 4. Cómo ejecutar una fase (operativa)

### 4.1 Identificar la fase actual

Antes de empezar, ejecutar:

```bash
# 1. Verificar tabla de progreso
cat C:\Cortex\docs\pluggable-middle\README.md   # buscar primera fase con ⏸ Pendiente o 🟡 En progreso

# 2. Verificar estado del repo
cd C:\Cortex
git status
git log --oneline -10
```

La fase a ejecutar es la **primera** en la tabla con estado distinto de ✅ Completa.

### 4.2 Resume protocol (si la fase ya empezó)

Si la fase está marcada 🟡 En progreso:

1. Abrí el documento de la fase (ej. `00-FOUNDATIONS.md`).
2. Buscá la sección **"Progress Log"** al final del documento.
3. Identificá la última tarea marcada como completa.
4. Continúa desde la siguiente.

**Si la sección "Progress Log" está vacía o desactualizada:**
- Ejecutá los **Completion Verification Commands** de las tareas anteriores para inferir el estado.
- Actualizá el Progress Log con lo que encontraste antes de continuar.

### 4.3 Durante la ejecución

1. **Una tarea a la vez.** No empezar tarea N+1 sin completar N.
2. **Tests con el código, no después.** Escribir test → escribir implementación → verificar test pasa. Iterar.
3. **Actualizar Progress Log al terminar cada tarea.** Esto permite resume.
4. **Hacer commits granulares.** Un commit por tarea (o por sub-feature coherente). Mensaje claro: `feat(session): add SessionRecord pydantic model with tests`.
5. **Si la fase se interrumpe,** asegurate de dejar el repo en un estado verde (`pytest` pasa, `ruff check` pasa). Nunca dejar mid-task con tests rojos.

### 4.4 Al cerrar una fase

1. Correr los **Completion Verification Commands** del documento de fase. TODOS deben pasar.
2. Actualizar `../README.md`:
   - Marcar la fase como ✅ Completa.
   - Anotar la fecha de cierre (`closed_at: YYYY-MM-DD`).
   - Si la fase produjo artefactos visibles (comandos CLI nuevos, módulos), enumerarlos en "Output".
3. Hacer commit final: `chore(pluggable-middle): close Phase 0X`.
4. Pasar a la siguiente fase.

### 4.5 Manejo de bloqueos

Si durante una fase descubrís que el diseño no funciona como está documentado:

- **NO improvises ni cambies el plan unilateralmente.**
- Documentá el problema en el Progress Log de la fase: qué encontraste, qué intentaste, por qué bloquea.
- Marcá la fase como ⚠️ Bloqueada en `../README.md`.
- Pará. El siguiente paso es revisión arquitectónica humana.

---

## 5. Secuencia de fases y dependencias

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   00-FOUNDATIONS                                                │
│   (Session primitive, MCP tools, CLI base)                      │
│                          │                                      │
│                          │ produce: cortex.session module       │
│                          │          .cortex/sessions/ dir       │
│                          │          MCP session_* tools         │
│                          │          CLI cortex session ...      │
│                          ▼                                      │
│   01-DOCUMENTER-RECONSTRUCTION                                  │
│   (BYO mode funcional)                                          │
│                          │                                      │
│                          │ produce: documenter.reconstruction   │
│                          │          verification hooks runner   │
│                          │          finish-session CLI          │
│                          │          spec verification_hooks req │
│                          ▼                                      │
│   02-SDDWORK-MIGRATION                                          │
│   (Managed mode unified con BYO backbone)                       │
│                          │                                      │
│                          │ produce: SDDwork emite checkpoints   │
│                          │          subagents emiten checkpts   │
│                          │          handoff YAML deprecated     │
│                          ▼                                      │
│   03-AUTOPILOT-FUSION                                           │
│   (Observed mode + Autopilot rebuilt sobre Sessions)            │
│                          │                                      │
│                          │ produce: Autopilot wraps Sessions    │
│                          │          IDE hooks adapters          │
│                          │          session hooks install CLI   │
│                          ▼                                      │
│   04-INTERACTIVE-MODE-POLISH                                    │
│   (Documenter interactive + docs finales)                       │
│                          │                                      │
│                          │ produce: --interactive flag          │
│                          │          README/Manifiesto update    │
│                          │          doctor completo             │
│                          │          E2E tests interactive       │
│                          ▼                                      │
│                       ✅ FIN                                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Reglas de dependencia

- Cada fase **requiere** que la anterior esté ✅ Completa antes de empezar.
- Saltar una fase está **prohibido**. Cada fase asume artefactos concretos de la anterior.
- Las fases son **secuenciales por dependencia técnica**, no por preferencia. La 01 no puede operar sin la primitiva de Sesión de la 00. La 02 reescribe SDDwork sobre la infraestructura que la 01 dejó. Etc.

---

## 6. Tabla maestra de fases

| Fase | Nombre | Valor que entrega | Bloqueante para | Esfuerzo |
|---|---|---|---|---|
| 00 | Foundations | Primitiva Session usable, CLI visible, MCP tools | 01, 02, 03 | ~1 semana |
| 01 | Documenter Reconstruction | **BYO mode funciona**. Cierra el 70% del valor de la arquitectura nueva. | 02, 03, 04 | ~2 semanas |
| 02 | SDDwork Migration | Managed mode comparte backbone con BYO. Elimina deuda de YAML inline. | 03 | ~1 semana |
| 03 | Autopilot Fusion + Observed | Observed mode + hooks IDE. Fusión interna. | 04 | ~2 semanas |
| 04 | Interactive + Polish | UX interactiva del documenter, docs finales, validación full | — | ~1 semana |

---

## 7. Checklist global pre-implementación

Antes de empezar la Fase 00, este checklist debe cumplirse:

- [ ] El repo está en una rama dedicada (sugerido: `feature/pluggable-middle`).
- [ ] `pytest` actual pasa al 100% en `master`.
- [ ] `ruff check` y `mypy` actuales pasan en `master`.
- [ ] La rama de trabajo está rebaseada sobre `master`.
- [ ] Tenés acceso de lectura a cualquier archivo del repo.
- [ ] Tenés acceso de WebFetch para docs externas.
- [ ] Existe un mecanismo de commit/push autorizado.

---

## 8. Glosario rápido

| Término | Significado |
|---|---|
| **Fase** | Bloque de trabajo coherente con un Output definido. |
| **Tarea** | Unidad atómica de implementación dentro de una fase (T0.1, T0.2, etc.). |
| **DoD** | Definition of Done. Ver §2.4 y §2.5. |
| **Required Reading** | Sección de cada doc de fase con archivos a leer antes de empezar. |
| **Progress Log** | Sección al final de cada doc de fase donde se marca el progreso. |
| **Completion Verification** | Comandos que demuestran que la fase está completa. |
| **Handoff to next phase** | Sección que documenta qué artefactos quedan disponibles para la siguiente fase. |

---

## 9. Empezá acá

Si estás listo para empezar:

1. Confirmá que leíste este README completo.
2. Confirmá que entendés el Quality Charter (§2).
3. Identificá la fase actual en `../README.md`.
4. Abrí el documento de esa fase.
5. Seguí su Required Reading.
6. Empezá.

**Si la fase actual es la 00, abrí ahora `00-FOUNDATIONS.md`.**

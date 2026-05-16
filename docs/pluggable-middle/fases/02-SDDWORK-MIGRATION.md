# Fase 02 — SDDwork Migration (Managed Mode unificado)

> **Estado:** ⏸ Pendiente · **Bloqueada por:** Fase 01 · **Bloquea:** Fase 03 · **Esfuerzo estimado:** ~1 semana

---

## 0. Metadatos

| Campo | Valor |
|---|---|
| Fase número | 02 |
| Nombre | SDDwork Migration (Managed Mode unificado) |
| Versión del plan | 1.0 |
| Dependencias | Fase 01 cerrada (modo BYO + reconstruction operativos) |
| Output principal | Modo Managed reescrito sobre la infraestructura de Sessions. SDDwork ya no emite YAML inline al documenter. |
| Breaking changes | Sí, controlados: SDDwork ya no usa `cortex_validate_handoff` para coordinarse con el documenter; los subagents `cortex-code-explorer` y `cortex-code-implementer` emiten checkpoints. El YAML schema `AgentHandoff` sigue existiendo internamente pero deja de ser el contrato inter-agente. |

---

## 1. Required Reading

### 1.1 Contexto del plan

- [`fases/README.md`](README.md) — Quality Charter.
- [`../ARQUITECTURA-PLUGGABLE-MIDDLE.md`](../ARQUITECTURA-PLUGGABLE-MIDDLE.md):
  - §4 (los 3 modos),
  - §7 (Documenter reborn — modo enriquecido),
  - §10.3 (SDDwork degradado a managed mode adapter),
  - §10.4 (Documenter cambios).
- [`00-FOUNDATIONS.md`](00-FOUNDATIONS.md) §7.
- [`01-DOCUMENTER-RECONSTRUCTION.md`](01-DOCUMENTER-RECONSTRUCTION.md) §7.

### 1.2 Código existente que vas a tocar

Leé enteros:

- `C:\Cortex\.cortex\skills\cortex-SDDwork.md` — el skill actual.
- `C:\Cortex\.cortex\subagents\cortex-code-explorer.md` — subagent actual.
- `C:\Cortex\.cortex\subagents\cortex-code-implementer.md` — subagent actual.
- `C:\Cortex\.cortex\subagents\cortex-documenter.md` — para verificar el cambio que hace Fase 01 y agregar lo de modo enriquecido.
- `C:\Cortex\cortex\handoff.py` — entender qué se hace deprecated.
- `C:\Cortex\cortex\agent_guidelines.md` y `agent_guidelines_work.md` — guidelines tope-level que mencionan el flujo.
- `C:\Cortex\cortex\session\service.py` (de Fase 00) — para entender cómo se llama `checkpoint`.
- `C:\Cortex\cortex\documenter\reconstruction.py` (de Fase 01) — para entender qué consume el documenter en modo reconstruction.
- `C:\Cortex\cortex\mcp\server.py` — tools que SDDwork llama actualmente.

Leé bajo demanda:

- Tests E2E del flujo tripartito legacy (`tests/e2e/`) — vas a tener que actualizarlos.

### 1.3 Documentación externa

Solo si hay dudas concretas sobre comportamiento de FastMCP u otra librería ya usada. No deberías necesitar consultar nada nuevo.

---

## 2. Goal

Al finalizar esta fase:

1. **El skill `cortex-SDDwork`** está rescrito: emite **checkpoints en la Session** en lugar de YAML handoffs entre subagents.
2. **Los subagents `cortex-code-explorer` y `cortex-code-implementer`** emiten checkpoints también.
3. **El documenter en modo reconstruction** ya recibe checkpoints ricos cuando se viene del flujo Managed → el output del documenter en Managed es **tan rico como antes** (con checkpoints como input enrichment), pero sin requerir validación YAML inline.
4. **El handoff YAML `AgentHandoff`** sigue siendo schema válido (no se elimina), pero **deja de ser el contrato obligatorio** entre agentes Cortex internos. Se mantiene para el modo legacy del documenter (que va a ser eliminado en Fase 04).
5. **El validador `cortex_validate_handoff`** se marca deprecated pero sigue funcionando. Será removido en Fase 04.
6. **Tests E2E del modo Managed** validan que el output final es equivalente al modo BYO + checkpoints adicionales.
7. **Tests E2E del modo BYO siguen pasando** (Fase 01 no se rompe).

**Lo que NO se hace en esta fase:**

- ❌ NO se elimina el schema `AgentHandoff` (Fase 04).
- ❌ NO se elimina el modo Legacy YAML del documenter (Fase 04).
- ❌ NO se toca Autopilot (Fase 03).
- ❌ NO se implementa modo interactive (Fase 04).

---

## 3. Decisiones de diseño clave

### 3.1 Granularidad de los checkpoints emitidos

¿Cuándo SDDwork (y los subagents) emiten checkpoints?

**Decisión:** **Un checkpoint por unidad de trabajo significativa** (no por cada acción atómica).

Ejemplos por agente:

| Agente | Cuándo emite checkpoint |
|---|---|
| `cortex-SDDwork` | Al terminar Fast Track o al terminar de delegar (Deep Track) |
| `cortex-code-explorer` | Al completar exploración del repo, antes de devolver hallazgos |
| `cortex-code-implementer` | Al completar la implementación (no por cada archivo modificado) |
| `cortex-documenter` (futuro Fase 04) | No emite, él **cierra** la session |

**No queremos:** 50 checkpoints granulares por sesión. **Queremos:** 1-3 checkpoints ricos.

### 3.2 ¿Qué contiene un checkpoint del subagent?

Estructura ya definida en Fase 00 (`Checkpoint` model). En el contexto de Managed:

- `verified_claims`: lo que el subagent verificó (lectura de archivos, tests corridos).
- `unverified_claims`: lo que el subagent supone pero no verificó.
- `artifacts_touched`: lista de archivos.
- `note`: texto libre breve con context_for_next (qué debe saber el próximo paso).

### 3.3 Compatibilidad con el modo Legacy YAML

El documenter en modo Legacy YAML sigue funcionando si se le pasa un bloque YAML inline. Esto preserva backward compat con cualquier tooling/skill externo que aún emita YAML.

**Cuándo se usa Legacy YAML después de esta fase:**

- Si un IDE externo (Codex, opencode-modo-single-agent) ejecuta el flujo en una sola sesión sin Sessions tracking → emite YAML al final, modo legacy.
- Si un usuario tiene un skill custom que emite YAML → sigue funcionando.

**Por qué no se elimina ahora:** porque Codex y similares NO soportan checkpoint emission inline. Eliminar el modo Legacy YAML los rompería. Fase 04 evalúa si se elimina o se mantiene permanentemente.

### 3.4 ¿Qué pasa con `cortex_validate_handoff`?

Se mantiene la tool MCP (para los tests del schema y compat), pero el skill `cortex-SDDwork` ya no la llama (porque no recibe YAML de los subagents, recibe checkpoints).

Se le agrega un deprecation log warning cuando se invoca:

```python
log.warning(
    "cortex_validate_handoff is deprecated. Use cortex_session_checkpoint for inter-agent state."
)
```

### 3.5 Reglas de fallback

¿Qué pasa si SDDwork está corriendo pero la session está perdida (active pointer roto)?

**Decisión:** SDDwork detecta y aborta con error explícito:

```
✗ No active session found. SDDwork requires an open session.
  Did sync run successfully? Try: cortex session list
```

NO recuperar silenciosamente abriendo una session nueva. NO continuar sin tracking.

---

## 4. Task Breakdown

### T2.1 — Rescribir skill `cortex-SDDwork.md`

**Objetivo:** SDDwork emite checkpoints, no YAML inline.

**Archivos a modificar:**
- `C:\Cortex\.cortex\skills\cortex-SDDwork.md`

**Cambios concretos:**

1. **Reemplazar la sección "Contrato de Salida (Output Obligatorio)"** que hoy emite YAML, por:

```markdown
## Contrato de Salida (Checkpoints + Mensaje final)

### Durante la ejecución

Al final de **cada paso significativo**, invocá `cortex_session_checkpoint`:

```
cortex_session_checkpoint(
  source="cortex-SDDwork",
  verified_claims=[lista concreta de claims verificados],
  unverified_claims=[claims aún no probados],
  artifacts_touched=[paths absolutos o relativos al workspace],
  note="resumen breve del estado actual"
)
```

Reglas:
- En Fast Track: emitir UN checkpoint al final.
- En Deep Track: emitir un checkpoint al terminar de delegar a cada subagent (el subagent ya emitió el suyo).
- No emitir checkpoints granulares por cada archivo o cada acción.

### Después de implementar

NO emitas YAML AgentHandoff. NO llames a `cortex-documenter` directamente.
Instead, decile al usuario:

> 🚀 **Implementación completada.**
> Cuando estés listo para persistir la documentación:
>   `cortex finish-session`
```

2. **Eliminar las referencias a "Validación de handoffs"** y `cortex_validate_handoff` excepto una nota de "deprecated, no usar".

3. **Mantener** la sección "Vías de Ejecución" (Fast/Deep Track) y "Mecanismos de delegación por IDE".

4. **Actualizar "Reglas críticas":**

```markdown
- ⛔ NO USAS `cortex_save_session` DIRECTAMENTE. Solo el documenter (vía `cortex finish-session`).
- ⛔ NO INVOQUES `cortex-documenter` DIRECTAMENTE. El usuario lo dispara con `cortex finish-session`.
- ⛔ NO EMITAS YAML AgentHandoff. Usá checkpoints.
- ⛔ NO USAS SKILLS EXTERNOS.
```

**Definition of Done T2.1:**
- Skill file actualizado.
- Renderiza correctamente (validación: si hay parser de skill MD, correrlo).
- Self-check manual: leer el skill como si fuera la primera vez y verificar que el flujo es claro.

---

### T2.2 — Rescribir subagent `cortex-code-explorer.md`

**Objetivo:** explorer emite checkpoint en lugar de YAML.

**Archivos a modificar:**
- `C:\Cortex\.cortex\subagents\cortex-code-explorer.md`

**Cambios:**

1. **Reemplazar el contrato de salida YAML** por:

```markdown
## Output Contract

Al terminar la exploración, **emití UN checkpoint** vía MCP:

```
cortex_session_checkpoint(
  source="cortex-code-explorer",
  verified_claims=[
    "Mapeado de dependencias de auth.py",
    "Identificados 3 puntos de extensión",
    "Confirmado: no hay middleware previo de JWT"
  ],
  unverified_claims=[],
  artifacts_touched=[
    # solo archivos LEÍDOS o ANALIZADOS, NO modificados
    "src/auth.py",
    "src/middleware/__init__.py",
    "tests/auth_test.py"
  ],
  note="Recommend: implementar en src/auth/jwt_validator.py para aislamiento. Ver issue #142 para constraints históricas."
)
```

NO emitas YAML. NO modifiques código (explorer es READ-ONLY).

Después del checkpoint, devolvele el control al orquestador (SDDwork) con un mensaje breve:

> ✅ Exploración terminada. Checkpoint emitido.
```

2. **Mantener** todas las reglas de read-only, las herramientas permitidas, las anti-rationalization signals.

---

### T2.3 — Rescribir subagent `cortex-code-implementer.md`

**Objetivo:** implementer emite checkpoint en lugar de YAML.

**Archivos a modificar:**
- `C:\Cortex\.cortex\subagents\cortex-code-implementer.md`

**Cambios:**

Análogo a T2.2:

```markdown
## Output Contract

Al terminar la implementación, emití UN checkpoint:

```
cortex_session_checkpoint(
  source="cortex-code-implementer",
  verified_claims=[
    "src/auth.py: JWT validation function added (tests pasan)",
    "src/middleware.py: rotation middleware integrado",
    "tests/auth_test.py: 5 nuevos casos cubiertos"
  ],
  unverified_claims=[
    "Performance impact bajo carga (no benchmarked)"
  ],
  artifacts_touched=[
    "src/auth.py",
    "src/middleware.py",
    "tests/auth_test.py"
  ],
  note="TTL hardcodeado a 7 días — pendiente decidir si se mueve a config (TODO en línea 47)."
)
```
```

---

### T2.4 — Actualizar subagent `cortex-documenter.md` (modo enriquecido)

**Objetivo:** que el documenter en modo reconstruction sepa **leer los checkpoints** del flujo Managed y usarlos como enrichment.

**Archivos a modificar:**
- `C:\Cortex\.cortex\subagents\cortex-documenter.md`

**Cambios:**

1. **Modificar la sección "Modos de operación"** (creada en Fase 01):

```markdown
### Modo Reconstruction (default)

Input: `session_id`

El módulo de reconstrucción (`cortex_finish_session`) automáticamente:
- Carga los checkpoints de la sesión.
- Ejecuta los verification hooks.
- Computa el diff.
- Detecta contradicciones.

Vos solo:
1. Invocás `cortex_finish_session(session_id=<id>)`.
2. Recibís el resultado.
3. Comunicás al usuario.

Si la sesión tiene checkpoints (Managed o Observed), el output del documenter
es automáticamente más rico: incluye las decisiones in-flight, scope drift,
contradicciones, todos los datos que los checkpoints aportaron.

Si la sesión NO tiene checkpoints (BYO), el output se reconstruye 100% desde
diff + tests. Sigue siendo válido, solo con menos contexto de "intención".

### Modo Legacy YAML (compat)

(Sin cambios respecto a Fase 01 — sigue como está, para skills externos / Codex.)
```

2. **Sin tocar:** verification gate, ADR criteria, CONTEXT.md maintenance, anti-rationalization signals. Todo sigue aplicando.

---

### T2.5 — Actualizar `agent_guidelines.md`

**Objetivo:** las guidelines top-level reflejan el nuevo flujo.

**Archivos a modificar:**
- `C:\Cortex\cortex\agent_guidelines.md` (que se distribuye via `cortex agent-guidelines`)
- `C:\Cortex\cortex\agent_guidelines_work.md`

**Cambios en `agent_guidelines.md`:**

```markdown
# Cortex Agent - Governance Rules

## Mandatory Pre-flight

Use `cortex-sync` first.

1. Run `git fetch` silently.
2. If remote has commits not in the local branch, stop and ask:
   > "Encontré actualizaciones en el repo de las memorias, hago pull?"
3. Use Cortex tools only to gather context:
   - `cortex_sync_ticket`
   - `cortex_search`
   - `cortex_context`
   - `cortex_create_spec` (con verification_hooks obligatorios)
4. Sync abre la Session automáticamente.

## Ecosystem Isolation

(Sin cambios.)

## Execution Model (Phase 02+)

- `cortex-sync` prepara contexto y la spec. Abre Session.
- **Middle (cualquiera de estos):**
  - `cortex-SDDwork` (Managed, recomendado para empezar)
  - Agente del usuario / skills propios (Observed o BYO)
- `cortex-documenter` cierra la session vía `cortex finish-session`.

## Definition of Done

A task is not complete until:
1. `cortex finish-session` se ejecutó.
2. El session note está persistido en el Vault.
3. La Session está en status CLOSED (o HANDOFF si el trabajo es parcial).
```

**`agent_guidelines_work.md`:** revisar el contenido actual (Fase 00 lo dejó como deprecated stub). Actualizar para reflejar el flujo nuevo o eliminarlo y dejar una nota redirigiendo al guidelines principal.

---

### T2.6 — Tests E2E del modo Managed

**Objetivo:** validar el flujo Managed completo bajo la nueva arquitectura.

**Archivos a crear:**
- `tests/e2e/test_managed_flow.py`

**Escenarios:**

```python
def test_managed_fast_track_simple_change(tmp_repo_with_cortex):
    """
    Setup: repo + cortex inicializado.
    Acción simulada:
      1. cortex_create_spec → session abierta
      2. (SDDwork conceptualmente) modifica archivo
      3. cortex_session_checkpoint(source=cortex-SDDwork, ...)
      4. cortex_finish_session
    Assert:
      - Session cerrada
      - Mode inferido = MANAGED (checkpoint source es Cortex agent)
      - Session note incluye la nota del checkpoint
    """

def test_managed_deep_track_multiple_subagents(tmp_repo_with_cortex):
    """
    Acción simulada:
      1. cortex_create_spec → session abierta
      2. checkpoint(cortex-code-explorer)
      3. modificar archivos
      4. checkpoint(cortex-code-implementer)
      5. checkpoint(cortex-SDDwork)
      6. cortex_finish_session
    Assert:
      - Mode = MANAGED
      - Session note menciona 3 checkpoints
      - context_for_next del handoff sintético combina notas de los 3
    """

def test_managed_flow_handoff_status(tmp_repo_with_cortex):
    """
    Mismo flujo pero con verification hook fallando → status=HANDOFF.
    Assert: blockers, next-needs en session note.
    """

def test_managed_flow_no_active_session_errors(tmp_repo_with_cortex):
    """
    Acción: invocar checkpoint sin sesión activa → error claro.
    """
```

---

### T2.7 — Tests de no-regresión BYO

**Objetivo:** confirmar que la migración no rompió Fase 01.

**Archivos a tocar:**
- `tests/e2e/test_byo_flow.py` — no modificar, debe seguir pasando.
- Si algún test falla por cambios colaterales, **arreglar el código nuevo**, no el test.

---

### T2.8 — Cleanup: `cortex_validate_handoff` deprecated

**Objetivo:** marcar la tool MCP como deprecated sin romperla.

**Archivos a modificar:**
- `cortex/mcp/server.py` — agregar warning log.
- `cortex/handoff.py` — agregar docstring header explicando que sigue siendo schema válido para legacy mode pero no es el contrato principal.

**Cambios:**

```python
# En la tool cortex_validate_handoff:
log.warning(
    "cortex_validate_handoff is deprecated since Phase 02. "
    "Use cortex_session_checkpoint for inter-agent state. "
    "This tool remains available for legacy YAML mode only."
)
```

No eliminar. No cambiar la signature. Solo log.

---

### T2.9 — Documentación

**Archivos a modificar:**
- `C:\Cortex\README.md` — actualizar §"El Modelo de Ejecución Tripartito" para reflejar Pluggable Middle.
- `C:\Cortex\docs\architecture\session-primitive.md` — agregar sección "Managed mode: checkpoints flow".
- `C:\Cortex\docs\pluggable-middle\README.md` — marcar Fase 02 como ✅ Completa.

**Contenido del cambio en README principal:**

Reemplazar la sección "El Modelo de Ejecución Tripartito" actual por algo en línea con el modelo Pluggable Middle. Mantener el manifiesto general (memoria + gobernanza) pero clarificar que el "middle" es pluggable.

Borrador del texto (refinar al implementar):

```markdown
## Modelo de Ejecución: Pluggable Middle

Cortex envuelve tu workflow en tres puntos: **sync** (antes), **middle** (durante) y **documenter** (después).

### 1. `cortex-sync` — El Analista
Recupera contexto histórico del Vault y de la memoria episódica. Produce una spec con verification hooks. Abre una Session.

### 2. Middle (Pluggable)
- **Managed (`cortex-SDDwork`):** flujo guiado con Intelligent Routing. Recomendado si no tenés tooling propio.
- **Observed:** usá tus skills/agentes preferidos. Cortex observa los checkpoints.
- **BYO:** desarrollá manualmente o con cualquier herramienta. Cortex reconstruye desde el diff.

### 3. `cortex-documenter` — El Guardián
Paso final via `cortex finish-session`. Reconstruye el contexto, ejecuta verification hooks, valida claims contra el diff, persiste session note + ADRs.
```

---

## 5. Cross-cutting concerns

### 5.1 Backward compatibility

- Modo Legacy YAML del documenter: **se mantiene** intacto.
- Skill externo de usuario que use `cortex_validate_handoff`: sigue funcionando con deprecation warning.
- Tests E2E previos de Fase 01: **deben seguir pasando**.

### 5.2 Eliminar duplicación

Antes había una "contrato YAML inline" entre subagents. Ahora la session es el contrato compartido. Verificar que no quede:

- Código en cualquier lado que construya YAMLs y los pase entre subagents.
- Subagents que esperan recibir YAML de upstream (los explorer/implementer no lo necesitan; lo emitían ellos).

Usar `Grep` exhaustivo para confirmar limpieza.

### 5.3 Sin "fallback automático"

Si una checkpoint falla (ej. session inexistente), NO intentar recuperarse silenciosamente. Lanzar error con instrucciones.

---

## 6. Completion Verification Commands

```bash
cd C:\Cortex

# 1. Tests
pytest tests/e2e/test_managed_flow.py -v
pytest tests/e2e/test_byo_flow.py -v          # debe seguir verde (no regresión)
pytest tests/unit/session/ -v                  # idem
pytest tests/integration/ -v                   # idem
# expected: all green

# 2. Type checking
mypy --strict cortex/session/ cortex/documenter/
# expected: clean

# 3. Lint
ruff check cortex/ tests/
ruff format --check cortex/ tests/
# expected: clean

# 4. Smoke test del modo Managed
# (simular en repo de prueba)
cortex create-spec --title "managed test" \
  --goal "validate managed flow" \
  --files-in-scope "managed.txt" \
  --acceptance-criteria "managed.txt exists" \
  --verification-hook 'name=existence;command=test -f managed.txt'
# Session abierta automáticamente

# Simular implementación + checkpoint vía MCP/CLI:
echo "managed content" > managed.txt
git add managed.txt && git commit -m "managed"
cortex session checkpoint --source cortex-SDDwork \
  --verified-claim "managed.txt created" \
  --artifact "managed.txt" \
  --note "Fast Track simple"

cortex finish-session
# expected:
#   - status=CLOSED
#   - mode=MANAGED (porque checkpoint source es agente Cortex)
#   - session note contiene la nota del checkpoint

# 5. Verificar deprecation warning de validate_handoff
# (cuando se invoca, debe haber log warning)
```

---

## 7. Handoff to next phase

Al cerrar Fase 02:

### Artefactos producidos

| Artefacto | Path |
|---|---|
| Skill SDDwork actualizado | `.cortex/skills/cortex-SDDwork.md` |
| Subagents explorer/implementer actualizados | `.cortex/subagents/cortex-code-*.md` |
| Documenter en modo enriquecido | `.cortex/subagents/cortex-documenter.md` |
| Guidelines top-level actualizadas | `cortex/agent_guidelines.md` |
| Tests E2E Managed | `tests/e2e/test_managed_flow.py` |
| `cortex_validate_handoff` con deprecation warning | `cortex/mcp/server.py` |
| README principal actualizado | `README.md` |

### Lo que la Fase 03 puede asumir como dado

1. SDDwork emite checkpoints; los subagents también.
2. El documenter en modo reconstruction maneja sesiones con o sin checkpoints (BYO/Observed/Managed) uniformemente.
3. El modo Legacy YAML solo se usa para Codex u otros IDE sin subagent support.
4. La "Session" es el contrato universal entre todas las partes del framework Cortex.

### Lo que NO se entrega

- Hooks IDE para Observed mode (Fase 03).
- Autopilot fusion (Fase 03).
- Modo interactive del documenter (Fase 04).
- Eliminación del schema `AgentHandoff` o del modo Legacy YAML (Fase 04, opcional).

---

## 8. Progress Log

- [ ] T2.1 — Rescribir skill `cortex-SDDwork.md`
- [ ] T2.2 — Rescribir subagent `cortex-code-explorer.md`
- [ ] T2.3 — Rescribir subagent `cortex-code-implementer.md`
- [ ] T2.4 — Actualizar subagent `cortex-documenter.md` (modo enriquecido)
- [ ] T2.5 — Actualizar `agent_guidelines.md`
- [ ] T2.6 — Tests E2E del modo Managed
- [ ] T2.7 — Tests de no-regresión BYO siguen pasando
- [ ] T2.8 — `cortex_validate_handoff` deprecated
- [ ] T2.9 — Documentación pública
- [ ] Completion Verification Commands pasan
- [ ] Tabla en `../README.md` actualizada con ✅
- [ ] Commit final

---

## 9. Notas para el agente ejecutor

- **Esta fase es menor en código pero alto en disciplina de prompts.** Los archivos `.md` de skills/subagents son el contrato real con los LLMs. Calidad del wording importa.
- **Después de modificar un skill,** corré un test E2E del flujo correspondiente. No alcanza con "compiló": tiene que **funcionar cuando un agente lee el skill**.
- **No elimines el schema `AgentHandoff`.** Sigue vivo para legacy. Cambia el contrato de uso, no la pieza.
- **Lo más fácil de romper acá:** dejar referencias huérfanas a `cortex_validate_handoff` en skills/subagents. Buscá exhaustivamente con `Grep`.

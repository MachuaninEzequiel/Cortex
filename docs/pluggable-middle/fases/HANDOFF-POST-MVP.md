# Handoff post-MVP — orden de ejecución de las 5 fases pendientes

> **Para el agente que abra una sesión nueva y vaya a ejecutar Fases 05 a 09.**
> Este documento ordena las fases por prioridad recomendada, documenta las
> coordinaciones críticas entre ellas, y deja una pre-flight checklist para
> arrancar sin perder tiempo. Es el equivalente de
> [`HANDOFF-TO-NEXT-SESSION.md`](HANDOFF-TO-NEXT-SESSION.md) pero para la
> etapa post-MVP.
>
> Leelo de arriba abajo antes de tocar una sola línea de código. Te ahorra
> 1-2 horas de re-descubrir contexto.

---

## 0. Snapshot al inicio (estado del repo)

**Fecha del handoff:** 2026-05-17 (post-cierre Fase 04 + adición de planes 05-09)
**Rama de trabajo:** `feature/nuevo-modo-autonomo` (o sucesora — verificar `git status`)
**Repo:** `C:\Cortex` (Windows; PowerShell + Git Bash)

### Tabla de progreso global

| Fase | Nombre | Estado | Próxima acción |
|---|---|---|---|
| 00 | Foundations (Session primitive) | ✅ Completa | — |
| 01 | Documenter Reconstruction (BYO) | ✅ Completa | — |
| 02 | SDDwork Migration (Managed) | ✅ Completa | — |
| 03 | Autopilot Fusion + Observed | ✅ Completa | — |
| 04 | Interactive Mode + Final Polish | ✅ Completa | — |
| **05** | Opencode hook adapter | ⏸ Pendiente | Ver §1 para prioridad |
| **06** | Sessions TUI con `rich` | ⏸ Pendiente | Ver §1 para prioridad |
| **07** | CI Plugin (3 niveles) | ⏸ Pendiente | Ver §1 para prioridad |
| **08** | Managed Quality Gates restaurados | ⏸ Pendiente | Ver §1 para prioridad |
| **09** | SDD Refinement (proposal + design + tasks) | ⏸ Pendiente | Ver §1 para prioridad |

### Estado de la suite

- **1743 passed, 15 skipped, 0 failed** al cierre de Fase 04.
- `mypy --strict --follow-imports=silent` clean en `cortex/{session,documenter}/` + core de `cortex/autopilot/`.
- `ruff check` clean sobre módulos Pluggable Middle.

### Commits pendientes

**NADA HA SIDO COMMITEADO** del trabajo Fase 00-04. Todo el progreso está en working tree
esperando autorización del usuario.
- Los progress logs de fases dicen "Commit final hecho [ ]" — los planes nuevos (05-09)
  siguen el mismo patrón.
- **NO HAGAS COMMIT** salvo que el usuario te lo pida explícitamente.

---

## 1. Orden recomendado de ejecución

> **Conclusión de una línea:** ejecutar **08 → 06 → 09 → 05 → 07**. Razones en §2.

| # | Fase | Esfuerzo | Por qué en esta posición |
|---|---|---|---|
| 1 | **Fase 08** — Managed Quality Gates | ~1.5 sem | **Deuda silenciosa potencial.** Hay riesgo de bug latente en rollback transaccional del documenter; descubrirlo tarde es deuda creciente. Bajo costo, alto valor inmediato. Sin dependencias. |
| 2 | **Fase 06** — Sessions TUI | ~2 sem | **Producto deliverable visible.** Mejora UX inmediata; sin dependencias en otras fases pendientes. Si Fase 08 ya ejecutada, la TUI puede mostrar quality gate status en checkpoints (mejora natural). |
| 3 | **Fase 09** — SDD Refinement | ~3-4 sem | **Mejora estructural más grande.** Requiere que quality gates (Fase 08) estén operativos antes — si no, agregás features sobre base débil. 3 sub-fases incrementales (09.A: 3 días; 09.B: 1 sem; 09.C: 1.5 sem). |
| 4 | **Fase 05** — Opencode adapter | ~1 sem | **Trivial, baja prioridad de adopción.** El user-base de opencode es chico. Útil para cerrar la matriz de IDEs soportados, pero no urgente. Puede hacerse cuando alguien lo pida. |
| 5 | **Fase 07** — CI Plugin (Niveles 1-3) | ~3-4 sem | **Big-ticket, requiere ecosistema maduro.** Alto valor pero los Niveles 2 (PR comments) y 3 (review sessions) se benefician de quality gates (Fase 08) y tasks granulares (Fase 09) ya operativos. Si se ejecuta antes, el Nivel 3 tendría que re-trabajarse parcialmente para integrar tasks. |

**Esfuerzo total estimado:** ~11-13 semanas si se ejecutan en serie. Algunas pueden paralelizarse (ver §3).

---

## 2. Justificación detallada del orden

### ¿Por qué Fase 08 primero?

Tres razones objetivas:

1. **Hay un bug potencial silencioso.** El audit doc T3.1 documentó que `IndexingSessionWriter` tenía rollback transaccional ("file en disco ⇒ file indexado") y dijo "verificar al hacer T3.3 si el DocumenterPersister lo preserva". Esa verificación **nunca se hizo**. Si el rollback no se portó, hay sessions notes en producción que pueden quedar persistidos pero no indexados — invisibles a `cortex search`. Es deuda silenciosa que crece con cada uso.

2. **Costo bajo.** ~1.5 semanas. La mayor parte es portar lógica existente del Autopilot eliminado (delegation.py, self_review, IndexingSessionWriter rollback) a los nuevos owners (documenter, SDDwork). No es código nuevo conceptualmente.

3. **Sin dependencias.** No requiere ninguna otra fase pendiente. Y **otras fases la asumen útil**: Fase 09 modifica el SDDwork prompt; mejor con quality gates ya integrados al review pipeline.

### ¿Por qué Fase 06 segundo?

1. **UX visible sin dependencias.** Independiente de las otras fases pendientes. Puede arrancar en cualquier momento.

2. **Si Fase 08 ya está, gana automáticamente.** La TUI muestra checkpoints. Si los checkpoints tienen quality gate status post-Fase 08, la TUI lo refleja sin cambios (el campo es informativo en el `note` del checkpoint).

3. **Calidad de producto.** El usuario percibe la TUI antes que las mejoras internas de SDDwork. Para showcasing y demos vale más.

### ¿Por qué Fase 09 tercero?

1. **Es la más grande estructural** (3-4 semanas, 3 sub-fases). Conviene tenerla DESPUÉS de las quality gates para no agregar features sobre base débil.

2. **Toca paths que Fase 08 también modifica** (SDDwork prompt + documenter persistence). Si Fase 08 va primero, Fase 09 absorbe sus cambios sin merge manual.

3. **Cada sub-fase puede mergearse independiente.** Si capacidad se agota: 09.A (3 días) ya da valor (proposal step); 09.B (1 sem) cierra design step; 09.C (1.5 sem) cierra tasks granulares.

### ¿Por qué Fase 05 cuarto?

1. **Trivial técnicamente** (~1 semana siguiendo patrón de adapters existentes).

2. **Pero baja prioridad de adopción real.** Opencode tiene user-base chico vs Claude Code/Cursor. El ROI por hora invertida es bajo si nadie lo pide.

3. **Sin dependencias en ninguna otra fase.** Puede hacerse en cualquier momento, ideal para "filler" entre fases grandes.

### ¿Por qué Fase 07 último?

1. **Es la más big-ticket** (3-4 semanas para Niveles 1+2+3).

2. **Nivel 3 idealmente requiere Fase 09 cerrada.** El "review session first-class" de Nivel 3 introduce `CheckpointSource.CI_BOT` y `SessionMode.CI_REVIEW`. Si Fase 09.C (tasks granular) ya está, el CI puede reportar progress por task (mucho mejor UX). Sin Fase 09, el CI reporta "checkpoint emitido" sin granularidad.

3. **Niveles 1 y 2 PUEDEN hacerse antes** sin perder valor — si el equipo necesita validación CI urgente, ejecutar 07.A + 07.B vale la pena (~10 días, sin Nivel 3). El Nivel 3 queda para después de Fase 09.

---

## 3. Paralelización posible

Si hay capacidad para 2+ ejecutores trabajando en paralelo:

| Track A (serial obligado) | Track B (paralelizable) |
|---|---|
| 08 → 09 (porque 09 absorbe cambios de 08) | 06 (sin dependencias) |
| | 05 (sin dependencias) |
| | 07 Niveles 1+2 (sin dependencias en 08/09; Nivel 3 espera) |

**Configuración óptima con 2 agentes:**
- Agente 1: 08 → 09.A → 09.B → 09.C → 07 Nivel 3
- Agente 2: 06 → 05 → 07 Nivel 1 → 07 Nivel 2

Tiempo total con paralelización: ~6-7 semanas (vs 11-13 en serie).

**Configuración óptima con 1 agente:**
- 08 → 06 → 09 (todas las sub-fases) → 05 → 07 (los 3 niveles).

---

## 4. Coordinaciones críticas entre fases

Estos puntos se documentan en cada plan individual; acá se centralizan para
que el ejecutor los tenga a la vista antes de empezar:

### 4.1 Modelo de datos (`SessionRecord`, enums)

| Cambio | Fase | Tipo |
|---|---|---|
| `CheckpointSource.CI_BOT` | 07 Nivel 3 | Aditivo a enum |
| `SessionMode.CI_REVIEW` | 07 Nivel 3 | Aditivo a enum |
| `SessionRecord.tasks: list[Task]` | 09 sub-fase 09.C | Aditivo a Pydantic model |
| `Task` modelo nuevo | 09 sub-fase 09.C | Aditivo |
| `TaskStatus` enum nuevo | 09 sub-fase 09.C | Aditivo |

**Todos compatibles.** Sessions YAML viejas siguen cargando. Cualquier orden de ejecución funciona.

### 4.2 Prompts de skills/subagents

| Archivo | Fases que lo tocan | Orden obligado |
|---|---|---|
| `.cortex/skills/cortex-sync.md` | 09 sub-fase 09.A | — |
| `.cortex/skills/cortex-SDDwork.md` | 08 (review checkpoint), 09 sub-fases 09.B (designer step) + 09.C (tasks descomposición) | **08 antes que 09** para evitar merge manual |
| `.cortex/subagents/cortex-code-designer.md` (nuevo) | 09 sub-fase 09.B | — |

**Regla de oro:** cualquier cambio a un archivo `.md` de skill/subagent **requiere** actualizar el renderer en `cortex/setup/cortex_workspace.py` y correr `pytest tests/unit/ide/test_adapters_phase4.py` para confirmar hash match.

### 4.3 Pipeline del documenter (`cortex/documenter/persistence.py`)

| Cambio | Fase |
|---|---|
| Self-review del draft + rollback transaccional verificado/restaurado | 08 |
| Renderer condicional por `task_type` en template Jinja2 | 08 |
| Reporte de `% task completion` en summary | 09 sub-fase 09.C |

**Fase 08 primero** evita conflictos. Fase 09 absorbe.

### 4.4 MCP tools nuevas

| Tool | Fase |
|---|---|
| `cortex_review_checkpoint` | 08 |
| `cortex_session_task_list` | 09 sub-fase 09.C |
| `cortex_session_task_update` | 09 sub-fase 09.C |
| `write_design_note_canonical` | 09 sub-fase 09.B |
| `cortex_ci_validate_pr` (implícito vía CLI) | 07 Nivel 1 |

Todas aditivas. Registrarlas en `cortex/ide/canonical_tools.py` (Literal + dict `_TOOL_NAME_BY_IDE`) cada vez para evitar el típico break del test del adapter por IDE.

### 4.5 TUI (Fase 06) y nuevas features

La TUI v1 muestra el `mode` como string genérico — cualquier valor nuevo del enum
(`ci-review`, etc.) aparece sin cambios al código. **Sin necesidad de coordinación.**

Lo que NO incluye Fase 06 v1 intencionalmente:
- Tasks display (Fase 09.C entrega tasks; mostrarlos en TUI es iteración 06.1 post-MVP).
- Quality gate status display (Fase 08 entrega gates; mostrarlos visualmente es iteración 06.1).
- Design doc preview (Fase 09.B entrega designer; preview en TUI es iteración 06.1).

Si querés que la TUI v1 incluya alguno de estos: **redefinir scope de Fase 06 antes de empezar**, no agregarlo a mitad.

---

## 5. Pre-flight checklist (antes de empezar CUALQUIER fase)

```
[ ] Leí este archivo HANDOFF-POST-MVP.md entero.
[ ] Identifiqué qué fase voy a ejecutar (revisar §1 si dudás del orden).
[ ] Leí el archivo de plan de esa fase completo (e.g. 08-MANAGED-QUALITY-GATES.md).
[ ] Leí el README de fases (Quality Charter).
[ ] git status: working tree limpio o con cambios reconocibles del estado previo.
[ ] Baseline tests pasan:
    python -m pytest tests/unit/ tests/integration/ tests/e2e/test_byo_flow.py \
        tests/e2e/test_managed_flow.py tests/e2e/test_observed_flow.py \
        tests/e2e/test_interactive_flow.py --no-cov --tb=no 2>&1 | tail -3
    Expected: 1743 passed, 15 skipped, 0 failed (o el baseline actualizado si fases previas a la mía ya cerraron).
[ ] TaskCreate listo para trackear las tasks de la fase actual.
[ ] (Si Fase 08 o 09) Verifiqué la sección §4.2-§4.4 de este handoff para coordinación.
[ ] (Si Fase 07 Nivel 3) Verifiqué si Fase 09 está ejecutada; si sí, mi código integra `tasks`.
```

---

## 6. Recipe para retomar — orden de comandos

Si abrís la sesión y querés empezar inmediato:

```bash
cd C:\Cortex

# 1. Verificar estado del repo
git status
git log --oneline -10

# 2. Verificar baseline
python -m pytest tests/unit/ tests/integration/ tests/e2e/test_byo_flow.py \
    tests/e2e/test_managed_flow.py tests/e2e/test_observed_flow.py \
    tests/e2e/test_interactive_flow.py --no-cov --tb=no 2>&1 | tail -3
# Expected: 1743+ passed, 0 failed

# 3. Leer el plan de la fase a ejecutar (orden recomendado: 08 primero)
# (Abrir docs/pluggable-middle/fases/08-MANAGED-QUALITY-GATES.md)

# 4. Crear las tasks de esa fase con TaskCreate
# (cada plan tiene su §8 Progress Log con la lista exacta)

# 5. Empezar por la primera task del plan (típicamente T<X>.1)
```

---

## 7. Decisiones que el ejecutor debe respetar (no improvisar)

Estas decisiones están en los planes individuales pero se repiten acá por
visibilidad:

### Fase 08

- Two-stage review vive en `cortex/session/quality_gates.py` (función pura), invocada por MCP tool `cortex_review_checkpoint`. **NO reintroducir `cortex/autopilot/delegation.py`** en su path original.
- Self-review del documenter es **informativo, NO bloqueante**. Bloquear generaría loops infinitos.
- Budget profiles son data, no lógica compleja — función pura de 20 líneas.

### Fase 09

- **Proposal step es opcional por default** (`--proposal-mode optional`). Hacer required de entrada agregaría fricción.
- **Designer step es obligatorio en Deep Track** (excepción: `task_type=docs-only`).
- **Tasks granulares son OPT-IN** vía flag `--with-tasks`. Fast Track jamás emite tasks.
- **Naming de tasks** sigue regex `T\d+(\.\d+)*` (ej. `T1`, `T1.2`, `T1.2.3`). No `task-1`, no `t-1`.

### Fase 07 Nivel 3

- Recomendación es **Opción B** (nuevo `CheckpointSource.CI_BOT` + Session "review" como cualquier otra). Si te tienta Opción A (nuevo SessionStatus) o C (nueva primitiva): **pará y consultá** — modelo es irreversible.

### Fase 06

- **No keyboard interactivo en v1.** Sólo Ctrl+C para salir. Si te tienta agregar `q`/`r`/`c`: anotalo en post-MVP roadmap.
- **Cross-platform mandatorio.** Probar en Windows Terminal + cmd.exe + tmux antes de cerrar.

### Fase 05

- **Investigá primero (T5.1).** Sin saber el formato real de hooks de opencode (puede haber cambiado), el resto es adivinanza.

---

## 8. Lo que NO está en este handoff (intencionalmente)

- **Decisiones de feature scope.** Cada plan tiene su §2 Goal con lo que entrega; respetarlo.
- **Asignación de personas/agentes.** Esto es operativo del equipo, no del plan.
- **Cronograma calendarizado.** Los esfuerzos en semanas son estimados; el equipo decide cuándo arrancar cada fase.
- **Plan de release.** Cuándo cortar versión es decisión del usuario, no del agente IA.

---

## 9. Lecturas obligatorias antes de empezar Fase 05/06/07/08/09

| Fase a ejecutar | Mínimo a leer |
|---|---|
| **Cualquiera** | Este `HANDOFF-POST-MVP.md` + `fases/README.md` + `ARQUITECTURA-PLUGGABLE-MIDDLE.md` §4 + §10.5 |
| **05** | `05-OPENCODE-HOOK-ADAPTER.md` + `03-AUTOPILOT-FUSION.md` §T3.6-T3.10 |
| **06** | `06-SESSIONS-TUI.md` + `cortex/cli/session.py` actual |
| **07** | `07-CI-PLUGIN.md` + `01-DOCUMENTER-RECONSTRUCTION.md` §7.2 |
| **08** | `08-MANAGED-QUALITY-GATES.md` + `_internal/autopilot-audit.md` + git history de `cortex/autopilot/delegation.py` antes de Fase 03 |
| **09** | `09-SDD-REFINEMENT.md` + `02-SDDWORK-MIGRATION.md` §3.1 + `08-MANAGED-QUALITY-GATES.md` §5.2 |

---

## 10. Suerte

Las 5 fases planeadas extienden Cortex sin tocar la arquitectura core
(`SessionRecord`, los 3 modos, el documenter pipeline). Si una fase rompe
algo del baseline (1743 passed), **revertí y consultá** — probablemente
violaste una coordinación de §4. No improvises arreglos hacia adelante.

Cualquiera de los planes tiene Progress Log explícito y Completion
Verification Commands testeables. Si te perdés, abrí el archivo del plan
y seguí la siguiente task del Progress Log no marcada.

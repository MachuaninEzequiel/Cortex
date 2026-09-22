# Direct y JevDD — el medio, sin tracks

Spec de producto. **No implementar hasta que el handoff lo pida en orden.**

Fast Track y Deep Track **desaparecen de la UX**. No se renombran a metodologías ajenas.

| Nombre | Cuándo | Qué es |
|---|---|---|
| **Direct** | Community: `judgement` off / sin key | El medio de siempre: un agente implementa. Cero HTTP a TypeSafe. |
| **JevDD** | `judgement.enabled` + key + purposes del portero/plugins on | Direct **más** portero Jev (sesión, memoria, cierre, enchufes). |

JevDD no es un riel distinto. Es Direct con clasificador. Sin Jev, el sandwich y el default “hacer” siguen existiendo.

---

## Marco que no se toca

```
sync (oficio, obligatorio si hay trabajo) → EL MEDIO → documenter (oficio, obligatorio al cerrar)
```

El medio es plug-and-play: el dev codea como quiera. Cortex no le impone un menú Fast/Deep.

Lo que **sí** se toca: quién *dispara* sync y documenter (el humano deja de elegir slash; el runtime + Jev lo hacen). Eso está en [09-portero.md](09-portero.md).

---

## Default del medio

**Hacer.** Un agente, sin subagentes, sin “estás en Deep”.

Especialistas (explorer, security, tests, partir trabajo) son **enchufes**, no un track:

- JevDD: un HTTP con noul por enchufe (`needs_explore`, `needs_security`, `needs_split`). Un noul alto enciende *ese* plugin, no un paquete de tres agentes.
- Direct: lexicon / default actual (Autopilot regex). Nunca auto-Deep por conteo de archivos.
- Subagentes / SDD formal **solo** si el usuario lo pide o acepta un `propose`.
- Confianza Jev &lt; 0.5 → una pregunta al humano, no “por las dudas Deep”.
- Jev **no obliga** subagentes. Guardrail fail-closed **no** va en el medio.

Nombres prohibidos en UI, skills y specs de producto: Fast Track, Deep Track, y cualquier marca de metodología de terceros.

Internamente el código puede mapear `direct` vs `delegate(plugin)` hasta borrar los strings viejos. La UX no los muestra.

---

## Autopilot

Hoy: detectores regex → `fast_code` / `deep_code` → budget del enricher.

Mañana (JevDD): los mismos detectores pueden *proponer* señales; Jev las convierte en noul de enchufe + `pack_depth`. El budget `question-only` / light / full se mantiene como **datos**, no como nombre de track.

Direct: Autopilot como hoy, pero el skill SDDwork **deja de gritar Deep Track**. Default implementar.

---

## SDDwork

Sigue siendo el orquestador del **sandwich** (no saltarse sync ni documenter) y del default directo.

Deja de ser el que clasifica “esto es Deep” por complejidad. Esa clasificación, en JevDD, es el portero + noul de enchufes.

---

## Qué no se hace

- Renombrar Fast→otro branding y Deep→SDD.
- Un SDK o middleware de terceros para “el harness”.
- Que el medio deje de existir sin TypeSafe.
- MCP tools “solo las usa Jev” (Jev no tiene manos; ver 09).

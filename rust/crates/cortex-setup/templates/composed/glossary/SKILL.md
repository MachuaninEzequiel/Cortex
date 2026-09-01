---
name: glossary
description: Lenguaje compartido del proyecto — mantener CONTEXT.md con terminos canonicos y sinonimos prohibidos, y capturar decisiones de nombre que merecen ADR.
when-to-use: Aparece un termino nuevo o ambiguo en el diseno, el codigo o la spec; o cuando la conversacion usa dos palabras para la misma cosa.
disable-model-invocation: true
---

# Glossary — el lenguaje compartido ES el diseno (fase: solo si toca la spec)

El lenguaje vago produce codigo vago y verbosidad infinita. Cuando un termino queda bien definido, humanos y modelos dejan de pelearse con sinonimos.

## Flujo

1. **Detectar drift**: dos palabras para la misma cosa, o una palabra para tres cosas — se hace visible cuando la spec, el ticket o el diff lo usan inconsistente.
2. **Actualizar `CONTEXT.md`** (raiz del workspace/repo): por termino — nombre canonico, definicion de 1-2 lineas, **sinonimos prohibidos**, un ejemplo de uso correcto. Terminos viejos que mueren se eliminan, no se "deprecian" con nota.
3. **Decidir, no describir**: si el termino implica una alternativa de diseño descartada, proponer ADR en `vault/decisions/` (minimo: contexto, decision, consecuencias). Sin decision real no hay ADR.
4. **Revisar vocabulario de la spec**: cuando la spec se escribe o cambia, verificar que use los terminos canonicos. Soft: la observacion se documenta, no se bloquea.
5. **Propagar, no solo documentar**: reemplazar los sinonimos prohibidos en los artefactos vivos de la sesion (spec, tickets) — un glossario que nadie propaga es decoracion.

## Checkpoint (solo si toca la spec activa)

Mero mantenimiento de `CONTEXT.md` ⇒ **NO emite checkpoint**. Si los terminos afectaron la spec activa, emitir con `phase: spec` — el gate de spec pide evidencia **>10 chars** en `verified_claims`. El inputSchema congelado del server MCP no lista `phase`: pasarlo igual como argumento extra.

```json
cortex_session_checkpoint({
  "session_id": "<activa — ver cortex_session_status>",
  "source": "user-skill",
  "phase": "spec",
  "verified_claims": ["<terminos canonicos actualizados en CONTEXT.md; spec ajustada a ellos (diff de ambos archivos como evidencia)>"],
  "unverified_claims": ["<terminos propuestos que el humano todavia no confirmo>"],
  "artifacts_touched": ["CONTEXT.md", "<path de la spec ajustada>"],
  "note": "<handoff: termino que el resto del flujo debe usar, <=1 linea>"
})
```

Reglas: `note` <= 1 linea. Un termino por checkpoint colectivo — no uno por palabra agregada.
Si `CONTEXT.md` no existe, se crea solo con terminos que ya mostraron drift — no con un catalogo vacio.
Si un termino cambia de significado a mitad de sesion, el checkpoint anterior queda obsoleto: mejor corregirlo en `unverified_claims` que acumular definiciones rivales.
El drift se detecta leyendo lo escrito, no ‘intuyendo la intencion’: dos artefactos que dicen lo mismo con dos palabras, una de las dos sobra.
Si el termino nuevo choca con un ADR existente, el ADR gana hasta que una decision nueva lo reemplace; no "actualizar" silenciosamente.
El glossario se mide por uso: si nadie usa el termino canónico en dos sesiones, la definicion esta mal (o el termino, muerto).

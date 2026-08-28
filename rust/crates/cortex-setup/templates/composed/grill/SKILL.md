---
name: grill
description: Aclarar requisitos con preguntas de experto hasta que el objetivo sea medible y el alcance tenga bordes.
when-to-use: El humano pide algo ambiguo ("mejorar", "arreglar", "hacer como X") y hay que afilar el requisito antes de especificar o implementar.
disable-model-invocation: true
---

# Grill — aclarar requisitos (fase: grill)

Preguntar hasta que el "terminado" sea observable y el alcance tenga bordes. Todavia no se especifica: `to-spec` materializa lo aclarado.

## Flujo

1. Leer el material disponible: pedido del humano, ticket/HU si existe, `CONTEXT.md` (si hay, usar los terminos canonicos desde ya).
2. Afilar con preguntas de experto — **una por vez**, no una lista:
   - Que problema dispara esto (usuario, trigger, contexto real)?
   - Como se ve el "terminado" medible (observable, no adjetivo)?
   - Que NO entra en este cambio (anti-objetivos explicitos)?
   - Que restricciones cuentan (rendimiento, compatibilidad, plataformas)?
   - 5 whys sobre el objetivo declarado: si un "por que" cambia el alcance, volver a preguntar.
3. Confirmar antes de registrar: parafrasear objetivo + bordes + restricciones y esperar el acuerdo del humano. Sin acuerdo, no hay checkpoint.

## Anti-Rationalization Signals

Las excusas tipicas para saltearse la aclaracion, y como responder cada una:

| Racionalizacion | Respuesta |
|---|---|
| "Es obvio, no hace falta grillar" | Lo obvio sin bordes produce scope drift. Tres preguntas cuestan dos minutos; rehacer la spec, horas. |
| "Ya se que quiere" | Si no podes parafrasear el "terminado" medible, no lo sabes. Preguntar: una pregunta por vez. |
| "Es un cambio chico" | Los cambios chicos con requisito ambiguo se arreglan dos veces. |
| "Despues lo afilo en la spec" | La spec hereda la ambiguedad; el gate de spec mide evidencia, no comprension. |

## Checkpoint obligatorio

Al cerrar la aclaracion, emitir el checkpoint. El inputSchema congelado del server MCP no lista `phase`: pasarlo igual como argumento extra (el servicio lo valida; fase invalida ⇒ rechazo explicito).

```json
cortex_session_checkpoint({
  "session_id": "<activa — ver cortex_session_status>",
  "source": "user-skill",
  "phase": "grill",
  "verified_claims": ["<objetivo medible + bordes que el humano parafraseo y confirmo>"],
  "unverified_claims": ["<supuestos que quedaron abiertos>"],
  "artifacts_touched": [],
  "note": "<handoff a to-spec: una linea>"
})
```

Reglas: `note` <= 1 linea (es el handoff). `grill` es la unica fase sin gate de evidencia: escribi igual el objetivo completo. Si no hay sesion activa, avisar y continuar sin checkpoint — la aclaracion le sirve a `/to-spec`.

---
name: diagnose
description: Diagnostico de bugs con feedback loop — reproducir en rojo estable antes de teorizar. Usar cuando algo falla y no hay reproduccion confirmada, cuando el bug es intermitente, o cuando el humano reporta "roto" sin datos.
when-to-use: Hay un bug sin loop de reproduccion verificado; esta prohibido teorizar fixes antes del rojo.
---

# Diagnose — primero el rojo, despues la teoria (fase: implement)

Regla: **no se teoriza sobre un bug que no sabes reproducir**. Un feedback loop que va en rojo te dice que fix funciona; sin el, adivinas y lo llamas "arreglo".

## Flujo

1. **Feedback loop**: construir el comando/accion que muestra el fallo y se puede correr muchas veces — un test que falla, un script, un request contra el server local. Si no existe todavia, construirlo ES la tarea 1. Sin loop estable, no se continua: reportar y pedir los datos que faltan.
2. **Reproduccion**: correr el loop y capturar la salida real del fallo. Fijo o intermitente? (Intermitente ⇒ minimizar una variable a la vez: input, orden, entorno, reloj.) El comando del loop se guarda tal cual: es el candidato natural a test de regresion.
3. **Aislar**: reducir a lo minimo que reproduce — input mas chico, instrumentacion en el camino (logs, asserts temporales), `git bisect` si se conoce el cuando.
4. **Fixear**: con el rojo aislado, "Call the Skill tool with `tdd`" — la reproduccion se convierte en el test rojo del fix.
5. **Verificar**: loop verde + una corrida extra del contexto real que rompio. Los asserts temporales del aislamiento se borran.
6. **Prevenir**: preguntar si la clase de bug era detectable por un gate, un test de invariantes o un nombre mejor — el candidato va en `note` para que review lo considere.

## Checkpoint obligatorio

El gate de fases exige `artifacts_touched` no vacio + `verified_claims` con evidencia **>10 chars** para `phase: implement` (sin evidencia ⇒ redelegate). La evidencia: comando del loop, estado rojo observado, estado verde post-fix. El inputSchema congelado del server MCP no lista `phase`: pasarlo igual como argumento extra.

```json
cortex_session_checkpoint({
  "session_id": "<activa — ver cortex_session_status>",
  "source": "user-skill",
  "phase": "implement",
  "verified_claims": ["<bug reproducido con <loop>: <salida del rojo>; aislado a <causa>; fix verificado: loop verde + contexto real verde>"],
  "unverified_claims": ["<variantas del bug no reproducidas>"],
  "artifacts_touched": ["<test de reproduccion agregado>", "<archivos del fix>"],
  "note": "<handoff a review, <=1 linea>"
})
```

Si el diagnostico revela que el alcance real excede la spec: registrar el drift en `unverified_claims` y avisar — no expandir la sesion en silencio.

Reglas: `note` <= 1 linea. El test de reproduccion queda en el repo (es parte del fix, no un desechable): sin el, el bug vuelve.
Si la causa raiz es un patron estructural (no un typo), anotarla para el cierre: puede merecer ADR o ticket de limpieza.
Sin loop estable no hay checkpoint de fix: un "arreglado" sin reproduccion es una hypothesis.

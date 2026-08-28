# Craft de implementacion (on-demand)

Referencia de `implement/SKILL.md`. Cargar solo cuando el slice no es trivial.

## Revisar el diff propio antes de decir "listo"

- Cada linea del diff sirve al ticket? La que no, se saca.
- Hay cambios cosmeticos no relacionados (format, renames)? Separarlos o revertirlos — ensucian la revision ajena.
- Manejaste los errores? Un `unwrap`/`expect` nuevo sobre camino falible, o un `Err` tragado, es hallazgo antes de que lo vea `review`.
- Dejaste dead code (flags o funciones que ya nadie llama)?
- El test del slice verifica comportamiento observable, no el implemento?

## Tamano de cambio

- Un commit = un cambio logico. Un gate por commit.
- Diff de produccion >200 lineas sin tests proporcionales = slice demasiado grande: partirlo o explicar en `unverified_claims` por que no se parte.
- "Mientras estoy" es el enemigo: cada impulso de "ya que estoy..." es un hallazgo de review futuro.

## Evidencia honesta para claims

- `verified_claim` = comando + resultado. `"cargo test -p cortex-app → 121 passed"` prueba; `"los tests pasan"` no.
- Lo que asumis sin correr va a `unverified_claims`, con la razon.
- En UI: paso reproducible o screenshot. En API: request/response real. En CLI: salida verbatim (o el nombre del golden si toco un snapshot).

## Cuando delegar y cuando no

- Un slice, un contexto: si le estas explicando el estado a un subagente mas de lo que tardarias escribirlo vos, no delegar.
- Delegar (subagente nativo del IDE) rinde para: exploracion que contamina contexto, tareas mecanicas grandes, segunda opinion (review).
- En COMPOSED, cada delegacion significativa emite SU checkpoint `implement` (source `user-skill` + `phase: implement`) — no acumular "para informar todo al final".

## Drift de scope

Si hace falta tocar archivos fuera de `files_in_scope`: PARAR. Dos salidas legitimas: (1) el humano aprueba y la spec se actualiza PRIMERO (no codear y justificar despues); (2) cerrar el slice y abrir ticket nuevo. La tercera (expandir en silencio) invalida el gate de spec compliance y el documenter la va a registrar como drift.

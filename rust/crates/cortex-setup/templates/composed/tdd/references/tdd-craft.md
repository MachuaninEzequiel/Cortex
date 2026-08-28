# Craft de TDD (on-demand)

Referencia de `tdd/SKILL.md`. Anti-patrones y salidas.

## Anti-patrones del ciclo

- **Test que pasa primero**: no probaste nada. Si el test pasa sin codigo nuevo, o no cubre el comportamiento que decis, o ese comportamiento ya estaba — escribir el test igual no cuenta como rojo.
- **Mock de lo que queres probar**: mock del sistema bajo prueba = test de tu mock. Mockuear solo la colindacion cara o no deterministica (red, reloj, otro servicio).
- **Test al implemento**: si renombrar un helper privado rompe un test sin cambiar el comportamiento, el test estaba atado al como. Asestar sobre lo observable.
- **Verde dudoso**: "deberia pasar" no es resultado. Correrlo, leer la salida.
- **Flaky tolerado**: un test intermitente es un hallazgo Critical, no un ruido del CI. Determinizar: seed fija, clock inyectable, esperar estados (no sleeps).
- **Coverage como objetivo**: un assert debil sube el numero y no asegura nada.

## Como disenar el rojo

- Nombre = comportamiento, no metodo: `rejects_expired_token`, no `test_validate_line_3`.
- Un solo "que" por test. Si el nombre necesita "and", partir el test.
- El rojo tiene que fallar por la razon esperada: leer la salida del assert forma parte del ciclo.
- Preferir asserts sobre valores observables a comparar salidas completas; golden/self-golden solo donde el contrato es byte-paridad (no para cada test).

## Orden de slices

- Vertical: el primer test cruza la superficie real de punta a punta (aunque el interior sea feo), no un modelo perfecto en el vacio.
- Cada slice cierra con la suite del crate verde y clippy limpio — el rojo/verde del test nuevo no exonera al resto.

## Gramatica de evidencia para el checkpoint (umbral >10 chars del gate implement)

- `"login::expired_token RED: cargo test login → FAILED (assert 'debe rechazar'); GREEN: check exp + 2 tests → 3 passed; crate → 121 passed"`
- Rojo y verde pueden ir en un claim unico con ambos estados citados, o en dos claims. Lo que no va: `"hice TDD"` a secas.

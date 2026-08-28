---
name: cortex-SDDwork-implement-craft
description: Pericia de implementacion para cortex-SDDwork — TDD, tamaño de cambio, revision del diff, cuando delegar y evidencia en claims. Se carga on-demand durante la fase de implementacion.
---

# Craft de implementacion para cortex-SDDwork

Referencia de pericia (no es un contrato): las reglas de gobernanza estan en
`cortex-SDDwork.md`. Esto responde *como* implementar como un ingeniero senior.
Cargalo cuando la fase de implementacion lo pida; no lo cargues en pre-flight.

## 1. Iron Law TDD (ley de hierro)

**Cero codigo de produccion sin un test que falle primero.** No es opcional:
un cambio sin test rojo previo no tiene evidencia de que el test mida nada.

Ciclo minimo (red → green → refactor):

1. **RED** — escribi el test que describe el comportamiento que FALTA
   (ej. `#[test] fn checkout_without_items_returns_error()`), correlo y
   verificá que falla *por la razon correcta* (funcion inexistente o
   comportamiento incorrecto, no un typo del test).
2. **GREEN** — implementá el minimo que lo haga pasar (puede ser feo;
   la calidad llega en el refactor).
3. **REFACTOR** — limpiá el codigo nuevo con el test como red de seguridad.

Ejemplo de ciclo en este repo (Rust):
```
# RED
cargo test -p cortex-app session::tests::checkpoint_requires_open  # FAIL: no existe
# GREEN
cargo test -p cortex-app session::tests::checkpoint_requires_open  # PASS
# REFACTOR
cargo clippy -p cortex-app -- -D warnings && cargo fmt              # limpio
```
La suite entera corre ANTES de declarar hecho, no despues.

## 2. Tamaño de cambio y commits atomicos

- Un cambio = una unidad logica = un commit. Si el cambio toca dos
  problemas distintos, son dos commits.
- **Un gate por commit** (regla del programa): cada commit debe dejar el
  workspace compilando y sus tests verdes.
- Cambios grandes se entregan en pasos revisables (el reviewer no aprueba
  un diff de 2000 lineas). Si una refactorizacion "no se puede partir",
  parte el MOVIMIENTO del codigo del CAMBIO de comportamiento.
- Avoid commits gigantes mezclando refactor + feature: el reviewer no
  puede distinguir que cambio rompe que test.

## 3. Revision del diff propio (antes de declarar)

Antes del checkpoint, lee tu propio diff como si fuera de otro dev. Busca:

- **Cambios fuera de scope**: archivos modificados que la spec no pide.
  Si son necesarios, explicados en el checkpoint; si no, revertidos.
- **Dead code**: funciones/módulos que quedaron sin consumidores.
- **Errores silenciosos**: `unwrap()`/`expect()` en paths de error no
  controlados, errores tragados (`.ok()` descartado, `let _ =`),
  timeouts sin fallback. Cortex exige fallo EXPLICITO (patron P6/P9),
  nunca silencio.
- **Cambios que no tocan el problema**: diffs cosméticos (renames,
  reformateos) que inflan el review sin aportar.
- **El test mide de verdad**: un test que pasa aunque el codigo este roto
  (assert sobre un mock que no falla, `match` que nunca cubre el caso
  nuevo) es peor que no tener test.

## 4. Cuando delegar a subagentes vs implementar directo

| Situacion | Camino |
|---|---|
| 1-2 archivos, logica simple, cero decisiones de arquitectura | **FAST TRACK** directo |
| Needle exploracion (mapear dependencias, entender un sistema ajeno) | Delegar a `cortex-code-explorer` ANTES de tocar codigo |
| Cambio de arquitectura / data model / contratos | Delegar a `cortex-code-designer` y seguir su design doc |
| Implementacion mecanica sobre un design cerrado | Delegar a `cortex-code-implementer` con el design doc |
| Varios archivos pero territorio conocido y spec clara | **FAST TRACK** — el costo de delegar supera el beneficio |

Regla de oro: cuando el subagente delegado necesita GUIAR una decision que
cambia el design, eso es señal de que la delegacion fue prematura. La
division correcta es: DECIDIR arriba, MECANICA abajo.

## 5. Verificacion con evidencia (claims)

`verified_claims` NO es "lo hice": es "lo hice y lo probe, y el comando
esta en el claim". Escribi el comando real y su resultado, no una opinion:

| Claim debil | Claim auditable |
|---|---|
| "Arregle el bug de checkout" | "`cargo test -p x checkout` → 3/3 PASS; causa raiz: id no validado" |
| "Refactorice el modulo" | "`cargo clippy -- -D warnings` limpio; `cargo test -p x` 40/40" |
| "Los tests pasan" | "`cargo test --workspace` → 501/501 (0 failures), salida adjunta en el reporte" |

Si no pudiste verificar algo (no hay entorno, el test tarda), va a
`unverified_claims` con la razon — no lo disfraces de verificado.

## 6. Trampas especificas de este repo

- El oráculo Python esta CONGELADO (paridad-como-contrato): un cambio de
  comportamiento que altere outputs `--json` reusados por goldens es
  UNA DIVERGENCIA DECLARADA, no un ajuste silencioso — menciónelo en el
  checkpoint.
- `f64`/orden de operaciones importa (paridad bit-a-bit): no "optimices"
  sumas ni cambies acumulacion sin ADR.
- Si algo debe fallar, que falle EXPLICITO con mensaje (patron P6/P9);
  nunca truncar, nunca `zip(strict=False)` mentiroso.
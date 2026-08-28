---
name: cortex-sync-spec-craft
description: Craft on-demand para escribir specs de calidad (cargar desde cortex-sync solo cuando la fase lo necesite).
---

# Spec Craft — cómo pensar una spec como un experto

Cargá este archivo SOLO cuando estés escribiendo la spec (PASO 3/4 de
`cortex-sync`). No lo leas en cada sesión: es material de profundidad que
se activa en la fase que lo necesita.

## Antes de escribir: las preguntas del experto

1. **Objetivo medible**: ¿qué se puede OBSERVAR/verificar cuando esté
   hecho? Si el criterio no es verificable por un comando, un test o una
   lectura, todavía no es un objetivo.
2. **Alcance real**: ¿qué archivos/módulos/sistemas quedan DENTRO? Nombra
   los límites explícitamente.
3. **Anti-objetivos**: ¿qué se decide NO hacer (y por qué)? Un buen
   anti-objetivo evita la expansión silenciosa del alcance.
4. **Contexto histórico**: ¿cómo se resolvió algo parecido antes? (ya viene
   del `sync_ticket`, pero confirmá contra los ADRs del vault si aplica).

## Contrastar con código real: glob → leer → citar

Una spec que no cita el código real es ficción. Método:

1. `glob` para encontrar los archivos candidatos del ticket.
2. `read` los archivos involucrados (y 1-2 vecinos si el cambio es de
   frontera).
3. **Cita líneas concretas** en la spec (`Archivo.rs:42-58`), no solo
   nombres de archivos. Si no podés citar, todavía no entendiste el cambio.

## Trampas comunes

| Trampa | Señal | Qué hacer |
|--------|-------|-----------|
| La spec describe solución, no problema | "Cambiar X por Y" sin el "por qué" | Escribí el problema/objetivo primero; la solución es consecuencia |
| Criterios de aceptación no verificables | "debería funcionar mejor", "más limpio" | Reescribi como comando/test/lectura observable ("cargo test ... pasa", "el endpoint devuelve 200 con body X") |
| Alcance sin límites | "y también..." acumulándose | Cada extra = decisión explícita, no ejemplo |

## Ejemplo: acceptance criteria bueno vs malo

1. MALO: "La búsqueda debe ser más rápida."
   BUENO: "BM25 responde <2 ms p99 sobre el fixture de 1000 docs
   (`bench/parity/bench_bm25.py`)."

2. MALO: "El login queda más moderno."
   BUENO: "`login.html` usa la paleta de cortex-branding; los tests de
   snapshot renderizan la nueva sección de logo sin warnings."

3. MALO: "Manejar los errores."
   BUENO: "Al fallar la API, el CLI imprime el mensaje canónico del oráculo
   y sale con rc 1 (el test `cli_errors.rs` cubre el caso timeout)."
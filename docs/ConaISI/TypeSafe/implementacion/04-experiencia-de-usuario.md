# Cómo funciona para el usuario

Hay dos usuarios. El que no paga no debe notar que TypeSafe existe, salvo una línea en doctor. El que paga debe notar **mejores respuestas**, no una app distinta.

---

## 1. Quien no paga (modo A) — Cortex de siempre

```
cortex search "cómo funciona el checkpoint"
cortex context
cortex session open ...
cortex finish
cortex next
# MCP: las mismas 32 tools
```

Idéntico. Sin key, sin cuenta TypeSafe, sin red extra. `cortex doctor`:

```
judgement: disabled (default)
```

`cortex setup` pregunta, al final, **después** de embeddings y vault:

```
¿Activar juicios TypeSafe? (opcional, requiere API key de typesafe.ai)
[n]  ← default
```

Enter = no. El YAML ni siquiera escribe el bloque, o lo deja comentado. Configs antiguas no se migran.

---

## 2. Quien paga — encender sin reaprender Cortex

```
export TYPESAFE_API_KEY=tsk_...
cortex judgement enable --purpose retrieval_rerank
cortex judgement ping          # 1 noul barato, verifica 200
cortex doctor                  # judgement: typesafe ok (retrieval_rerank=on)
```

A partir de ahí:

| Comando / tool | Lo que cambia para el humano |
|---|---|
| `cortex search` / `cortex_search` | Los mismos hits, **otro orden**. El #1 es el que responde, no el que más dice la palabra. Verbose: `reranked=typesafe noul[0]=0.91` |
| `cortex context` / `cortex_context` | El bloque de 2–4k chars que se inyecta al agente es más denso. El agente IDE “recuerda” mejor el repo |
| `cortex finish` | Puede listar *contradicciones* contra ADRs (si purpose on). Interactive pregunta. Auto mode persiste `asserted`/`contradicted` de verdad |
| `cortex autopilot start` | Requests vagos → clarificación (noul ambiguous), no un detector regex |
| Brain / Companion | “buscá X” dispara search sin cargar GGUF. Chat libre sigue en llama.cpp |
| `cortex next` | Menos acciones elegibles-pero-tontas |
| `review-knowledge` | Cola ordenada (si promotion on) |
| MCP | **Mismas tools, mismos nombres.** Claude/Cursor no se reconfiguran |

El usuario no “entra a TypeSafe”. Usa Cortex. TypeSafe es el motor de ranking, como ONNX es el motor de embeddings.

---

## 3. El agente IDE (Claude Code, Cursor, Pi…)

No hay adapter nuevo. `CANONICAL_TOOLS` y `BEGIN CORTEX SECTION` se quedan.

Lo que el agente *siente*:

- `cortex_context` le trae el runbook correcto en vez de 4 notas que mencionan la misma keyword.
- `cortex_finish_session` puede devolver findings de contradicción en el briefing (el subagente documenter ya tenía el Protocol; ahora deja de ser NoOp).
- Menos alucinaciones de “el proyecto hace X” porque X estaba en un hit irrelevante inyectado.

`agent-guidelines` gana un párrafo **solo si judgement está on** (generado, no un markdown global que mienta en installs community):

```
Retrieval is judgement-reranked. Trust top hits. If a hit is flagged
contradicts/stale, treat it as disputed, not as fact.
```

---

## 4. El humano en TUI / Companion

Home, sessions, search: las mismas pantallas. Search results pueden mostrar un indicador discreto (dot / “J”) si verbose o si `judgement.show_badge: true` (default false: el ranking no se explica solo).

Companion approval de actions: igual. TypeSafe no clickea Approve.

OrgMemoryModal: si promotion on, el orden de drafts cambia; los botones no.

---

## 5. El flujo mental del producto nuevo

Hoy:

```
pregunta → lexicon → RRF → 5 hits keyword-shaped → agente rellena huecos
```

Con judgement on (retrieval):

```
pregunta → (opcional) intent calibrado → RRF over-fetch →
  1× system_one con 15–30 nouls en paralelo (~100–200 ms) →
  hits reordenados / dropeados → agente trabaja con evidencia
```

El usuario espera ~200 ms más en search. A cambio el *agente* (que cuesta segundos y dólares) trabaja menos.

Finish hoy:

```
diff + checkpoints → NoOp contradicciones → nota "verified"
```

Finish con judgement:

```
diff + search de ADRs candidatos → nouls por par →
  findings o silencio → confidence tri-estado honesto
```

El usuario ve, a veces, “esto choca con ADR-12”. Eso no existía.

---

## 6. Apagar

```
cortex judgement disable
# o
# judgement.enabled: false
```

Siguiente search: modo A. No hay migración de datos. Los jsonl de eventos quedan. El vault no tiene un formato nuevo (salvo que finish ya haya escrito findings: son notas markdown normales).

---

## 7. Doctor — la única UI obligatoria

```
judgement
  status:     disabled | typesafe | degraded
  provider:   none | typesafe
  key:        missing | present
  ping:       skipped | 200 (87ms) | 401 | 429 | timeout
  purposes:   retrieval_rerank=on  contradictions=off  ...
  fail_open:  3 skips in last 24h (from judgement-events.jsonl)
```

Tutor: **no** menciona TypeSafe en el path zero-tokens. Un topic opcional `judgement` si se escribe después, no en v1.

---

## 8. Lo que el usuario obtiene, en una frase por persona

- **Dev solo, sin key:** nada cambia.
- **Dev solo, con key:** search/context del agente dejan de ser “me trajo basura del vault”.
- **Equipo enterprise:** promote deja de copiar diarios de sesión al vault org; review-knowledge prioriza.
- **Quien usa Brain local:** comandos de memoria en 100 ms, GGUF solo para hablar.
- **Quien usa Autopilot:** menos deep-track disparado por un “how do I” que era security.

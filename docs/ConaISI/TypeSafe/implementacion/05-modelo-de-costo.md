# Modelo de costo

Fuente de precio TypeSafe (docs 2026-09-17): **$0.042 por millón de tokens de input**. Output **gratis**. Rate limit documentado: 250k tok/s, 1200 req/min (dinámico).

Cortex **no** cobra un markup. El gasto es la cuenta TypeSafe del usuario.

## Tokens por purpose (estimación de ingeniería, no un benchmark medido)

Overhead observado en ejemplos oficiales: un ticket corto + 1–3 questions ≈ **300–600 input tokens**. El state grande es lo que duele (chunks, diffs).

| Purpose | State que mandamos | Questions | Input tokens ≈ | $/call |
|---|---|---|---|---|
| `ping` / doctor | 1 frase | 1 noul | 250 | $0.000010 |
| `query_intent` | query + files abiertos | 1 choice | 400 | $0.000017 |
| `retrieval_rerank` | query + **15** chunks × ~100 tok | 15 nouls | **3 000–5 000** | **$0.00013–0.00021** |
| `retrieval_rerank` 30 hits | idem ×30 | 30 nouls | 6 000–9 000 | $0.00025–0.00038 |
| `contradictions` | diff slice + 8 ADRs | 8×2 nouls | 4 000–8 000 | $0.00017–0.00034 |
| `adr_suggest` | checkpoints + name-status | 3 nouls | 1 500 | $0.000063 |
| `quality_gate` | note + claims + hunks | 3 noul + 1 score + 1 choice | 2 000 | $0.000084 |
| `autopilot` | utterance + files | 1 choice + 1 score + 2 noul | 800 | $0.000034 |
| `brain_intent` | utterance | 1 choice | 350 | $0.000015 |
| `next_action` | session digest + 5 candidatas | 5 nouls | 1 200 | $0.000050 |
| `promotion` | nota + títulos org | 2 noul + 2 choice + 1 score | 2 000 | $0.000084 |
| `guardrail` | utterance | 2 noul + 1 score | 500 | $0.000021 |

Cap de v1: **rerank 15 candidatos** (over-fetch ×3 de `top_k: 5` del `config.yaml` actual). 30 es el techo del cookbook CLERC, no el default.

## Perfiles de uso mensual (30 días)

### P0 — Community
0 calls. **$0.**

### P1 — Solo, agente todos los días (el perfil más realista para este repo)

Supuesto: Claude/Cursor abierto, 2 sesiones/día, ~40 `cortex_search`/`cortex_context` por día, 1 finish/día, 5 `next`, 10 utterances Brain, autopilot 2/día. Solo `retrieval_rerank` on (v1).

| Purpose | Calls/día | Tok/call | Tok/día |
|---|---|---|---|
| rerank | 40 | 4 000 | 160 000 |
| finish contrad. (si on) | 0 en v1 | — | 0 |
| **Total** | | | **~160k/día → 4.8 MTok/mes** |

**Costo: 4.8 × $0.042 ≈ $0.20 / mes.**

### P2 — Solo, judgement “full” (todos los purposes on)

| Purpose | Calls/día | Tok/día |
|---|---|---|
| rerank | 40 × 4k | 160k |
| intent (call extra) | 40 × 0.4k | 16k |
| contradictions | 1 × 6k | 6k |
| adr | 1 × 1.5k | 1.5k |
| quality_gate (4 checkpoints) | 4 × 2k | 8k |
| autopilot | 2 × 0.8k | 1.6k |
| brain | 15 × 0.35k | 5.3k |
| next | 5 × 1.2k | 6k |
| **Total** | | **~205k/día → 6.2 MTok/mes** |

**Costo ≈ $0.26 / mes.**

El rerank **es** la factura. El resto es ruido.

### P3 — Equipo 8 personas, mismos hábitos, un org vault

8 × P2 ≈ 50 MTok/mes. **≈ $2.10 / mes.**

### P4 — Granja de agentes (CI + 20 agents en paralelo, 200 searches/persona/día, 10 personas)

200 × 10 × 4k tok × 30 días = 2.4 **billion** tokens? Wait: 200*10=2000 calls/day * 4000 tok = 8 MTok/day * 30 = 240 MTok/mes. **≈ $10.10 / mes.**

Rate limit 1200 rpm: 2000 calls/día es ~1.4 calls/min promedio, picos al abrir sesión. Fan-out ya mete 15 questions **en un** request: el RPM cuenta requests, no questions. Cabe.

### P5 — Shadow mode en producción (mismo volumen que P1)

Shadow **cuesta igual que on**. No es gratis. Usarlo una semana para nDCG, no dejarlo un año.

## Contra qué se compara (el dato que importa)

El agente IDE (Claude, etc.) es el gasto grande. Un turno de modelo frontier con 4–8k tokens de contexto inyectado por `to_prompt` cuesta **centavos a dólares**, no décimas de milésima.

Si un rerank de **$0.0002** evita **un** turno extra del agente (“esto no era el runbook, buscá de nuevo”):

- Conservador: un turno Claude ~ $0.01–0.05 de input.
- TypeSafe search ~ $0.0002.
- **Un turno ahorrado paga 50–250 searches.**

Tesis económica: TypeSafe no se justifica como “AI barata para jugar”. Se justifica como **filtro que ahorra el LLM caro que Cortex ya alimenta**. El usuario que no usa agentes y solo hace `cortex search` en TUI 5 veces al día paga ~$0.03/mes y nota poco. El usuario del producto real (agentes) es quien gana.

## Qué puede inflar la factura (y cómo no)

| Riesgo | Mitigación en arquitectura |
|---|---|
| Rerank de 30 hits con chunks de 2k tokens | cap 15 hits, chunk ≤ ~400 chars, matched_chunk no archivo |
| TUI search-as-you-type | no llamar en cada tecla; on submit / debounce 300 ms |
| Shadow eterno | doctor warn si shadow > 14 días |
| `purpose` todos on “por las dudas” | default YAML todos `off`; enable por purpose |
| Retry agresivo en 529 | backoff + fail-open; no 10 reintentos de un search interactivo |
| Mandar el vault en contradictions | prefiltro top 8 ADRs |
| Debug SDK log bodies | no `TYPESAFE_LOG_LEVEL=debug` en workspaces reales |

## Presupuesto en config (opcional v1.1)

```yaml
judgement:
  budget:
    max_input_tokens_per_day: 500000    # ~$0.021
    on_exceed: disable_purposes         # fail-open a modo A el resto del día
```

No hace falta para v1 ($0.20/mes no se descontrola). Útil en P4.

## Cómo reportar gasto al usuario

`cortex judgement status` lee `judgement-events.jsonl` (input_tokens por evento):

```
last 24h:  142 calls   0.58 MTok   ~$0.024
last 30d:  3100 calls  12.4 MTok   ~$0.52
purposes:  rerank 96% of tokens
```

Precio hardcodeado a $0.042/MTok como default documentado, override `judgement.usd_per_mtok` por si TypeSafe cambia `/models`. No es billing; es una estimación. El invoice real está en console.typesafe.ai.

## Gratis de verdad

- `enabled: false` → 0 calls, 0 $.
- Sin extra pip, sin feature: ni siquiera se puede llamar.
- Doctor, tutor, BM25, embeddings ONNX locales, session YAML: siguen $0 como hoy.

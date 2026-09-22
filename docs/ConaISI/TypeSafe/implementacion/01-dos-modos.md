# Dos modos, un binario

Cortex ya tiene este patrón. No inventar otro.

| Feature hoy | Apagado (default) | Prendido |
|---|---|---|
| `llm.provider` | `none` — summarizer trunca | openai/anthropic/ollama |
| enterprise | no hay `org.yaml` | promote, scope, governance |
| Brain llama | compile sin `--features llama` | GGUF |
| webgraph Flask | extra opcional | serve |
| Jira | integrations off | import HU |

TypeSafe es la misma clase de cosa: **inteligencia de red, de pago, opt-in**. Quien no paga no “usa Cortex peor”: usa Cortex *exactamente como ahora*.

## Modo A — Community (default, $0 TypeSafe)

Condición (cualquiera alcanza para quedarse acá):

- no existe bloque `judgement:` en config, o
- `judgement.enabled: false`, o
- `judgement.provider: none`, o
- no hay `TYPESAFE_API_KEY` (aunque enabled=true → **warn** en doctor y se degrada a A).

Comportamiento:

- `QueryIntentDetector` lexicon.
- RRF crudo.
- `NoOpContradictionDetector`.
- Autopilot `default.py` / regex.
- Brain `route_intent` regex.
- Scheduler fórmula.
- Promote estructural.

Cero HTTP a `api.typesafe.ai`. Cero dependencia de runtime `typesafe-sdk`. El binario nativo **compila sin feature `typesafe`**. Pytest del paquete `cortex` no necesita key.

El path caliente de `HybridSearch.search` es el de hoy más un `if client.is_none() { /* código actual */ }` que el compilador/branch predictor trata como nunca tomado si None.

## Modo B — Judgement (TypeSafe)

Condición **todas**:

1. `judgement.enabled: true`
2. `judgement.provider: typesafe`
3. `TYPESAFE_API_KEY` presente
4. el purpose concreto está `on` (o `shadow`)

Comportamiento: el código actual corre **igual hasta el seam**. Después del seam, si el client responde OK, se aplica el juicio (rerank, contradiction findings, …). Si 401/429/529/timeout: **fail-open** al modo A para esa call, log, doctor lo cuenta. Nunca un `cortex search` vacío porque TypeSafe tosió.

### Shadow

`purpose.retrieval_rerank: shadow` llama a TypeSafe, **no cambia** el ranking que ve el usuario, escribe `.cortex/judgement-events.jsonl`. Sirve para medir nDCG contra producción real sin arriesgar UX. **Cuesta dinero** (la call existe). No es el modo gratis.

## Matriz de degradación (SSoT)

```
enabled? ──no──► Modo A
   │sí
provider none? ──sí──► Modo A
   │typesafe
hay key? ──no──► Modo A + doctor warn
   │sí
purpose off? ──sí──► Modo A para ese purpose
   │on|shadow
HTTP ok? ──no──► Modo A para esa call (fail-open)
   │sí
shadow? ──sí──► aplica A, loguea B
   │on
            aplica B
```

Nadie “pierde Cortex” por no pagar. Nadie “rompe search” por una 429.

## Quién paga qué

- **Usuario community:** $0 TypeSafe. Paga (si quiere) su LLM de summarizer / su GGUF. Cortex core sigue local (ONNX, Chroma/JSONL, BM25).
- **Usuario judgement:** $ TypeSafe proporcional a calls (ver `05-modelo-de-costo.md`), más la key. Sigue sin ser obligatorio para CLI/MCP básicos.
- **Cortex el producto:** no mete la key en el repo, no proxya la API, no revendemos tokens. El contrato es usuario ↔ TypeSafe. Cortex solo es un cliente.

## Compile-time vs runtime

Dos palancas, las dos existen ya en el repo:

1. **Cargo feature `typesafe`** (como `llama`, `onnx`). Sin feature: el crate `cortex-judgement` no linkea HTTP. El CLI que se `cargo install` por default puede incluir la feature (el código está, no llama) **o** no incluirla. Recomendación: **incluir el cliente en el binario default** (ureq ya está en el workspace) y apagar por **config**. Evita dos artefactos “cortex” y “cortex-pro”. Un binario, dos modos.
2. **Python extra** `pip install cortex-memory[typesafe]` instala `typesafe-sdk`. Sin extra, `import typesafe_sdk` no ocurre (import diferido, como ContextEnricher hoy). `AgentMemory` no falla al construir.

Runtime gana a compile-time para el usuario final. Compile-time es por si un packager quiere un binario air-gapped sin el client.

## Lo que no es un “modo”

- No hay `cortex --ai`.
- No hay fork de MCP (las 32 tools y el golden no se tocan).
- No hay pantalla “upgrade to TypeSafe” en la TUI. Doctor dice el estado; setup pregunta una vez.
- No hay watermark en `to_prompt`. El agente IDE no debe saber si el ranking vino de Jev o de RRF (salvo verbose humano).

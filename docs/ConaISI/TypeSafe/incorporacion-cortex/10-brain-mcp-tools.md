# Brain y las 32 tools MCP

Módulos: `cortex-brain` (router, tools, chat, llama), `cortex-brain-app` (Tauri), `apps/brain-ui`, `cortex-mcp` (32 tools, `SERVER_VERSION=2.2`), `cortex/brain/*` DEPRECATED (oráculo).

Invariante que no se toca: **Brain no muta**. Tools `Tier::Read` o `SafeAction` (`webgraph.serve`). Mutaciones = `actions.propose` (comando CLI, no ejecución).

## Router actual

`route_intent(texto)`: slash commands primero, `_PATRONES` regex. 0 tokens. El LLM (feature `llama`) se agrega encima, protocolo TOOL + confirmación.

Esto ya es el diseño TypeSafe (demo smart-home: TypeSafe clasifica; LLM solo si conversación o split de comandos compuestos). El regex es el hueco.

## Capa 1 — Intent del utterance (reemplazo del regex, con fallback)

```text
Choice brain_intent
  search_memory: look up past work or project knowledge
  docs_related: related documentation
  health: doctor / is Cortex ok
  vault_stats: counts, inventory
  session_status: current session
  show_graph: open webgraph
  propose_actions: what should I do next
  conversation: chit-chat, explanation, something that needs generated text
  other
```

Código:

```text
slash command → gana siempre (determinista)
si brain_intent.confidence < 0.5 → conversation (el LLM es el fallback seguro, no una mutación)
si conversation → llama.cpp
si no → dispatch tool READ, 0 tokens de LLM
```

Latencia: TypeSafe ~100 ms vs GGUF mucho más. El demo smart-home dice que el overhead es negligible **incluso cuando después hay LLM**. Cuando no hay LLM, el Brain se siente instantáneo.

## Capa 2 — Skill suggestion sobre 32 tools MCP

Cuando el caller es un **agente IDE** (no el Brain), el problema es otro: 32 tools en el catálogo, el agente elige mal o llama de a una.

Cookbook skill_suggestion (182 skills Hermes → 1):

**Request 1** (barato, nombres + one-liners del `tools_catalog.rs`, no los schemas completos):

```text
Score fit_{tool_id}  (o Noul needs_{tool_id}) por cada tool
Noul needs_any_tool
  "Does this agent turn need a Cortex tool at all?"
```

32 Scores + 1 Noul en un call. Si `needs_any_tool` bajo → el agente no recibe ninguna tool extra (ahorra tool-thrashing).

**Request 2** (solo top 3 por score, ahora sí con descripción completa + input schema):

```text
Choice winner
  tool_a, tool_b, tool_c, none
```

`none` es el `other` obligatorio. El nombre de la ganadora entra en **una línea** del system / agent-guidelines, no se reescribe el catálogo MCP. El contrato de 32 tools y el orden de keys JSON (`tools_catalog.rs`, golden) **no se toca**.

Esto es harness engineering del use-case map de TypeSafe: “model routing, semantic context retrieval… at lightspeed”.

No hace falta que el servidor MCP llame a Jev en cada tool. Mejor: un wrapper `cortex_suggest_tool` interno, o un hint en `agent_guidelines.md` generado. MCP no tiene hoy una tool de promote; no agregar tools a la ligera (el golden contract es sagrado). El hint puede vivir en `cortex agent-guidelines` que ya existe.

## Capa 3 — Guardrails del LLM local

Cookbook llm_guardrails. Antes de mandar el utterance a llama.cpp y antes de mostrar la reply:

```text
Noul jailbreak
Noul asks_to_mutate
  "Does the user ask the assistant to execute a destructive or mutating command rather than propose it?"
Score harm
  0: none, 1: reversible nuisance, 2: data loss / secret leak
```

Si `asks_to_mutate` alto → no dispatch; recordar que Brain propone CLI. Si harm alto → block. Alineado a “Brain no muta”: Jev es el portero, no el ejecutor.

State adversarial: jaggedness #6. Criteria explícitos. Testear.

## Companion / HERDR

`engine.rs` Backend in-process (sesiones, acciones, search, doctor, stats). Approval `run_guarded`. El Brain panel reusa tools de `cortex-brain`. Misma capa 1–3. Approval modal se queda: TypeSafe no aprueba mutaciones.

## Qué no hacer

- Dejar que Jev genere la respuesta de chat (capa conversation = llama.cpp).
- Ejecutar el comando propuesto.
- Cambiar nombres o orden de las 32 tools.
- Mandar las 32 schemas completas en el request 1 (skill_suggestion oficial: rank primero, leer después).

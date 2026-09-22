# cortex/hooks/agent_hooks.py

## Qué tiene adentro

- **Ruta de código:** `cortex/hooks/agent_hooks.py` (159 líneas).
- **Módulo Python:** `cortex.hooks.agent_hooks`.
- **Docstring del módulo:** cortex.hooks.agent_hooks ------------------------ DEPRECATED (dueño, 2026-08-25 — doc 12 §4.4): módulo huérfano — ni templates, ni IDE adapters, ni setup lo referencian; los hooks vigentes viven en cortex/setup/session_hooks (gate P8: 38/38). Se elimina en la baja de Python.
- **Clases definidas:**
  - `CortexHook`
    - Generic hook. Wrap an agent call to automatically capture
    - Métodos públicos/especiales: `__init__`, `capture`
    - Métodos internos: `_build_input_desc`
  - `CortexLangChainCallback`
    - LangChain BaseCallbackHandler that saves agent actions as memories.
    - Métodos públicos/especiales: `__init__`, `on_agent_action`, `on_agent_finish`, `on_llm_start`, `on_llm_end`, `on_tool_start`, `on_tool_end`, `on_chain_start`, `on_chain_end`

## Para qué sirve

cortex.hooks.agent_hooks
------------------------
DEPRECATED (dueño, 2026-08-25 — doc 12 §4.4): módulo huérfano — ni templates,
ni IDE adapters, ni setup lo referencian; los hooks vigentes viven en
cortex/setup/session_hooks (gate P8: 38/38). Se elimina en la baja de Python.

Drop-in hooks / callbacks that wire cortex into popular agent frameworks.

Supported frameworks
--------------------
- LangChain  → CortexLangChainCallback
- CrewAI     → CortexCrewAIHook  (monkey-patch style)
- Generic    → CortexHook (use directly for custom agents)

## Relaciones

### Recibe de

- `cortex.core` (AgentMemory)
- Dependencias externas/stdlib: `functools`, `inspect`, `logging`, `__future__`, `collections.abc`, `typing`

### Envía a

- `cortex.hooks`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 159.
Docstrings de símbolos públicos:
- `CortexHook.capture`: Decorator. Stores the agent's input + output as a memory.

---
Fuente: código de `cortex/hooks/agent_hooks.py` (AST + grafo de imports internos). No se usó documentación previa.

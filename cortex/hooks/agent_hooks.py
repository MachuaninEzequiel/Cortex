"""
cortex.hooks.agent_hooks
------------------------
Drop-in hooks / callbacks that wire cortex into popular agent frameworks.

Supported frameworks
--------------------
- LangChain  → CortexLangChainCallback
- CrewAI     → CortexCrewAIHook  (monkey-patch style)
- Generic    → CortexHook (use directly for custom agents)
"""

from __future__ import annotations

import functools
import inspect
import logging
from collections.abc import Callable
from typing import Any

from cortex.core import AgentMemory

logger = logging.getLogger(__name__)


class CortexHook:
    """
    Generic hook. Wrap an agent call to automatically capture
    input/output as episodic memories.

    Usage::

        memory = AgentMemory()
        hook = CortexHook(memory)

        @hook.capture(memory_type="task")
        def run_agent(prompt: str) -> str:
            return llm.run(prompt)
    """

    def __init__(self, memory: AgentMemory) -> None:
        self.memory = memory

    def capture(
        self,
        memory_type: str = "general",
        tags: list[str] | None = None,
        files: list[str] | None = None,
        summarize: bool = False,
    ) -> Callable:
        """Decorator. Stores the agent's input + output as a memory."""

        def decorator(fn: Callable) -> Callable:
            @functools.wraps(fn)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                result = fn(*args, **kwargs)

                # Build a readable input description from args or kwargs
                input_desc = self._build_input_desc(fn, args, kwargs)

                content = f"Input: {input_desc}\nOutput: {result}"
                self.memory.remember(
                    content,
                    memory_type=memory_type,
                    tags=tags,
                    files=files,
                    summarize=summarize,
                )
                return result

            return wrapper

        return decorator

    @staticmethod
    def _build_input_desc(
        fn: Callable, args: tuple, kwargs: dict
    ) -> str:
        """
        Build a human-readable description of function arguments.

        Maps positional and keyword arguments to their parameter names
        so the stored memory is readable even when called with
        ``fn(value="hello")`` instead of ``fn("hello")``.
        """
        try:
            sig = inspect.signature(fn)
            bound = sig.bind_partial(*args, **kwargs)
            bound.apply_defaults()
            # Format as: param1=value1, param2=value2
            parts = []
            for name, value in bound.arguments.items():
                # Skip 'self' / 'cls' to avoid leaking large objects
                if name in ("self", "cls"):
                    continue
                val_str = str(value)
                if len(val_str) > 200:
                    val_str = val_str[:200] + "…"
                parts.append(f"{name}={val_str}")
            return ", ".join(parts) if parts else "(no arguments)"
        except Exception:
            # Fallback: raw repr of args + kwargs
            parts = []
            if args:
                parts.extend(str(a)[:200] for a in args)
            if kwargs:
                parts.extend(f"{k}={v!s}"[:200] for k, v in kwargs.items())
            return ", ".join(parts) if parts else "(no arguments)"


# ---------------------------------------------------------------------------
# LangChain callback
# ---------------------------------------------------------------------------

class CortexLangChainCallback:
    """
    LangChain BaseCallbackHandler that saves agent actions as memories.

    Usage::

        from langchain.agents import AgentExecutor
        memory = AgentMemory()
        cb = CortexLangChainCallback(memory)
        agent = AgentExecutor(agent=..., tools=..., callbacks=[cb])
    """

    def __init__(self, memory: AgentMemory) -> None:
        self.memory = memory

    def on_agent_action(self, action: Any, **kwargs: Any) -> None:
        tool = getattr(action, "tool", "unknown_tool")
        tool_input = getattr(action, "tool_input", "")
        logger.debug("CortexHook captured agent action: %s", tool)
        self.memory.remember(
            f"Used tool '{tool}' with input: {tool_input}",
            memory_type="agent_action",
            tags=["langchain", tool],
        )

    def on_agent_finish(self, finish: Any, **kwargs: Any) -> None:
        output = getattr(finish, "return_values", {}).get("output", "")
        self.memory.remember(
            f"Agent finished: {output}",
            memory_type="agent_finish",
            tags=["langchain"],
        )

    # Required no-ops for LangChain compatibility
    def on_llm_start(self, *a: Any, **kw: Any) -> None: ...
    def on_llm_end(self, *a: Any, **kw: Any) -> None: ...
    def on_tool_start(self, *a: Any, **kw: Any) -> None: ...
    def on_tool_end(self, *a: Any, **kw: Any) -> None: ...
    def on_chain_start(self, *a: Any, **kw: Any) -> None: ...
    def on_chain_end(self, *a: Any, **kw: Any) -> None: ...

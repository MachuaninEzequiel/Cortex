"""
cortex.episodic.summarizer
--------------------------
Compresses verbose agent action logs into concise memory entries
using an LLM backend (OpenAI, Anthropic, or local via Ollama).
"""

from __future__ import annotations

import logging
import os
from typing import Literal

logger = logging.getLogger(__name__)

LLMProvider = Literal["openai", "anthropic", "ollama", "none"]

COMPRESS_PROMPT = """\
You are a memory compression system for an AI agent.
Summarize the following agent activity into a single, dense sentence.
Focus on: what was done, what files were touched, and the outcome.
Be concise — max 2 sentences. Do not include timestamps.

Activity:
{content}

Summary:"""


class Summarizer:
    """
    Compresses raw agent activity logs into short memory summaries.

    Args:
        provider:  LLM backend to use for compression.
        model:     Model name/identifier for the chosen provider.
    """

    def __init__(
        self,
        provider: LLMProvider = "none",
        model: str = "",
    ) -> None:
        self.provider = provider
        self.model = model

    def compress(self, content: str) -> str:
        """
        Summarize content. Falls back to a simple truncation if no LLM
        is configured (provider == "none").
        """
        if self.provider == "none" or not content.strip():
            return self._truncate_fallback(content)

        prompt = COMPRESS_PROMPT.format(content=content)
        try:
            if self.provider == "openai":
                return self._call_openai(prompt)
            if self.provider == "anthropic":
                return self._call_anthropic(prompt)
            if self.provider == "ollama":
                return self._call_ollama(prompt)
        except Exception as exc:
            logger.warning("Summarizer error (%s): %s — using raw content.", self.provider, exc)
        return self._truncate_fallback(content)

    # ------------------------------------------------------------------
    # Backends
    # ------------------------------------------------------------------

    def _call_openai(self, prompt: str) -> str:
        from openai import OpenAI  # type: ignore

        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        resp = client.chat.completions.create(
            model=self.model or "gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.2,
        )
        return resp.choices[0].message.content.strip()

    def _call_anthropic(self, prompt: str) -> str:
        import anthropic  # type: ignore

        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        resp = client.messages.create(
            model=self.model or "claude-haiku-4-5-20251001",
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text.strip()

    def _call_ollama(self, prompt: str) -> str:
        import httpx  # type: ignore

        resp = httpx.post(
            "http://localhost:11434/api/generate",
            json={"model": self.model or "llama3", "prompt": prompt, "stream": False},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["response"].strip()

    # ------------------------------------------------------------------
    # Fallback
    # ------------------------------------------------------------------

    @staticmethod
    def _truncate_fallback(content: str, max_chars: int = 300) -> str:
        content = content.strip().replace("\n", " ")
        if len(content) <= max_chars:
            return content
        return content[:max_chars].rsplit(" ", 1)[0] + "…"

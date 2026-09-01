"""Catálogo v1 del ActionEngine (plan §3.3)."""

from __future__ import annotations

from cortex.action_engine.actions.catalog import (
    ide_resync,
    knowledge_promote,
    learn_topic,
    memory_prune,
    quality_run_gates,
    session_checkpoint_now,
    session_close_stale,
    setup_finish_bootstrap,
    vault_reindex,
    vault_validate_docs,
)
from cortex.action_engine.context import ActionContext
from cortex.action_engine.registry import Registry

__all__ = [
    "build_default_registry",
    "ide_resync",
    "knowledge_promote",
    "learn_topic",
    "memory_prune",
    "quality_run_gates",
    "session_checkpoint_now",
    "session_close_stale",
    "setup_finish_bootstrap",
    "vault_reindex",
    "vault_validate_docs",
]


def build_default_registry(ctx: ActionContext) -> Registry:
    """Registra las 10 acciones v1 sobre el contexto dado."""
    registry = Registry()
    for fabrica in (
        setup_finish_bootstrap,
        session_close_stale,
        session_checkpoint_now,
        vault_reindex,
        vault_validate_docs,
        quality_run_gates,
        learn_topic,
        knowledge_promote,
        memory_prune,
        ide_resync,
    ):
        registry.register(fabrica(ctx))
    return registry

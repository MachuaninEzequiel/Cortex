"""
cortex.tutor.topics
-------------------
Registry of all built-in tutor topics.
Each topic module exposes a class that satisfies the TutorTopic protocol.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cortex.tutor.engine import TutorTopic


def get_all_topics() -> list["TutorTopic"]:
    """Return all built-in topics in display order."""
    from cortex.tutor.topics.getting_started import GettingStartedTopic
    from cortex.tutor.topics.commands import CommandsTopic
    from cortex.tutor.topics.workflow import WorkflowTopic
    from cortex.tutor.topics.pipeline import PipelineTopic
    from cortex.tutor.topics.vault import VaultTopic
    from cortex.tutor.topics.enterprise import EnterpriseTopic
    from cortex.tutor.topics.ide_integration import IDEIntegrationTopic

    return [
        GettingStartedTopic(),
        CommandsTopic(),
        WorkflowTopic(),
        PipelineTopic(),
        VaultTopic(),
        EnterpriseTopic(),
        IDEIntegrationTopic(),
    ]

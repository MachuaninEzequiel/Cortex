"""
cortex.setup
------------
Project setup and auto-detection utilities for the ``cortex setup`` command.
"""

from __future__ import annotations

from cortex.setup.detector import ProjectContext as ProjectContext
from cortex.setup.detector import ProjectDetector as ProjectDetector
from cortex.setup.orchestrator import SetupOrchestrator as SetupOrchestrator
from cortex.setup.orchestrator import format_summary as format_summary

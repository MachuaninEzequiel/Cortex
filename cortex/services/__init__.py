"""
cortex.services
---------------
Domain service layer for Cortex.

This package contains the business-logic services extracted from
the AgentMemory orchestrator. Each service has a single, clear
responsibility (SRP).

Services
--------
- ``SpecService``    → Create and persist implementation specifications.
- ``SessionService`` → Create and persist session notes.
- ``PRService``      → Store PR context and generate fallback documentation.

Usage
-----
    from cortex.services import SpecService, SessionService, PRService
"""

from cortex.services.spec_service import SpecService
from cortex.services.session_service import SessionService
from cortex.services.pr_service import PRService

__all__ = [
    "SpecService",
    "SessionService",
    "PRService",
]

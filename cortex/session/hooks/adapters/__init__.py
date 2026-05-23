"""cortex.session.hooks.adapters — Bundled IDE hook adapters.

Each module here implements :class:`cortex.session.hooks.HookAdapter` for
a specific IDE / runtime:

* :mod:`claude_code` — Claude Code's native ``hooks`` block in
  ``settings.json``.
* :mod:`cursor`      — git ``post-commit`` script (works for Cursor,
  VSCode-with-Cline, plain editors).
* :mod:`pi`          — Pi Coding Agent ``just`` recipes.

Adapters are imported lazily by ``HookInstaller.default_installer`` so a
broken adapter does not poison the rest of the installer.
"""

from __future__ import annotations

import pytest
from pathlib import Path
from cortex.webgraph.openers import resolve_safe_vault_path, open_path
import sys
import subprocess

def test_resolve_safe_vault_path(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    note = vault / "test.md"
    note.write_text("hello")
    
    # Valid path
    resolved = resolve_safe_vault_path(vault, "test.md")
    assert resolved == note.resolve()
    
    # Path outside vault
    with pytest.raises(ValueError, match="Refusing to open path outside vault"):
        resolve_safe_vault_path(vault, "../other.md")
    
    # Non-existent path
    with pytest.raises(FileNotFoundError):
        resolve_safe_vault_path(vault, "missing.md")

def test_open_path(monkeypatch):
    path = Path("test.md")
    
    if sys.platform == "win32":
        import os
        mock_startfile = lambda x: None
        monkeypatch.setattr(os, "startfile", mock_startfile, raising=False)
        open_path(path)
    elif sys.platform == "darwin":
        mock_run = lambda cmd, check: None
        monkeypatch.setattr(subprocess, "run", mock_run)
        open_path(path)
    else:
        mock_run = lambda cmd, check: None
        monkeypatch.setattr(subprocess, "run", mock_run)
        open_path(path)

# Cortex Threat Model

> Scope: local filesystem boundary, vault isolation, and MCP input surfaces.
> Version: 0.3.0

## Surfaces

1. **Vault filesystem** — read/write of markdown files under `vault/` and `vault-enterprise/`.
2. **Workspace layout** — discovery of `.cortex/`, `config.yaml`, and project roots.
3. **MCP server** — input from IDE agents via tool calls (`cortex_search`, `cortex_context`, etc.).
4. **Enterprise promotion** — promotion of local documents into the enterprise vault.
5. **CLI / Typer commands** — user-supplied `--project-root` and file arguments.

## Threats and Mitigations

### T1 — Path Traversal via Relative Paths

An attacker supplies a relative path containing `../` to escape the vault or workspace.

**Mitigation:**
- All filesystem operations that build paths from operational input use `cortex.security.paths.resolve_safe()`.
- `resolve_safe()` rejects absolute paths and resolves the final path under the allowed root.
- `validate_under_root()` performs a second check after path construction.
- Applied to:
  - `VaultReader.index_file()`, `create_note()`, `update_note()`
  - `documentation.write_session_note()`, `write_spec_note()`, `write_tracked_item_note()`
  - `WorkItemService.get_item_note()`
  - `CortexMCPServer._extract_candidate_files()`

### T2 — Absolute Path Injection

An attacker provides an absolute path (e.g., `/etc/passwd`) to access sensitive system files.

**Mitigation:**
- `resolve_safe()` raises `PathSecurityError` immediately if the input path is absolute.
- `CortexMCPServer._extract_candidate_files()` skips absolute candidate paths.

### T3 — Workspace Boundary Confusion

A component resolves files against the wrong root (e.g., current working directory instead of project root).

**Mitigation:**
- `WorkspaceLayout` is the single source of truth for all layout paths.
- `KnowledgePromotionService` now retains the `WorkspaceLayout` resolved at construction time and reuses it in `discover_candidates()`.
- No ad-hoc path discovery is performed inside services.

### T4 — Untrusted Input in MCP Queries

MCP tool arguments contain file paths or queries that could be used to probe the filesystem.

**Mitigation:**
- `_extract_candidate_files()` only returns files that exist under `project_root` and are validated with `resolve_safe()`.
- Query strings are parsed with regex that extracts likely file paths, but each candidate is validated before being returned.

## Limitations and Accepted Risks

- **Symlinks:** `resolve_safe()` uses `Path.resolve()`, which follows symlinks. A symlink inside the vault pointing outside the vault will be detected as an escape, but this is a best-effort defense.
- **WebGraph server:** The optional Flask server is not hardened against network-level attacks in this version.
- **Embedding models:** Downloaded ONNX models are not cryptographically verified.
- **CI/CD gates:** The GitHub Actions workflows enforce quality gates but are not themselves part of the runtime threat model.

## Verification

Path-hardening tests live in `tests/unit/security/test_paths.py` and are executed as part of the standard test suite.

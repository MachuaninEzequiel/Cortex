# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.3.x   | :white_check_mark: |
| < 0.3.0 | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in Cortex, please open a private security advisory via the repository's **Security > Advisories** tab or email the maintainers directly.

Please include:
- A clear description of the vulnerability.
- Steps to reproduce.
- Expected vs actual behavior.
- Your environment (OS, Python version, Cortex version).

We aim to respond within 7 business days and will coordinate a fix and disclosure timeline.

## Scope

This security policy covers:
- Path traversal and unsafe file-system operations.
- MCP server input handling.
- Vault and workspace boundary enforcement.
- Enterprise promotion pipeline integrity.

Out of scope (by design at this stage):
- Network-level attacks against the optional WebGraph server.
- Supply-chain attacks on embedding model downloads.
- Physical access to the host machine.

## Related Documents

- [Threat Model](./docs/security/threat-model.md)

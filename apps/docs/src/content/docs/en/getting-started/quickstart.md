---
title: Quickstart (5 Minutes)
description: Learn how to initialize Cortex in a project, start a session with an AI agent, and persist cognitive memory.
---

This guide walks you through setting up Cortex in your repository and running your first AI-assisted session.

---

## 1. Install the Cortex CLI Binary

Install `cortex-cli` directly from the Rust workspace:

```bash
cargo install --path rust/crates/cortex-cli
```

Verify your installation:

```bash
cortex-cli --version
```

---

## 2. Verify Your Environment (`cortex doctor`)

Run the native health diagnostic:

```bash
cortex doctor
```

Expected output:
```text
[OK] rust_toolchain: Cargo and Rust runtime detected
[OK] workspace_layout: Valid directory structure
[OK] onnx_model: Embedding model available
[OK] vault_permissions: Read/write permissions in .cortex/
```

---

## 3. Initialize Cortex in Your Project

In your project root:

```bash
cortex init
```

This creates the `.cortex/` layout:
* `.cortex/config.yaml`: Configuration for models, search weights, and providers.
* `.cortex/workspace.yaml`: Workspace layout definition.
* `.cortex/vault/`: Root directory for canonical Markdown notes.
* `.cortex/memory/`: Episodic JSONL storage.

---

## 4. Start a Work Session

Open a new development session:

```bash
cortex session open --name "auth-migration" --notes "Refactoring JWT tokens to pure Rust"
```

Check active session status:

```bash
cortex session current
```

---

## 5. Remember and Search Knowledge

### Save a fast discovery:
```bash
cortex remember "Password hashing uses Argon2id with 3 iterations and 64MB memory" --tag auth --tag security
```

### Hybrid search:
```bash
cortex search "what is the password hashing configuration"
```

---

## 6. Finish Session with Evidence

```bash
cortex finish --intent auto
```

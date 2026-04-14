"""
examples/basic_usage.py
-----------------------
Demonstrates the full cortex workflow:
  1. Initialize AgentMemory
  2. Store episodic memories
  3. Add a semantic note to the vault
  4. Run a hybrid search
  5. Inject context into an LLM prompt
"""

from cortex import AgentMemory

# ── 1. Initialize ────────────────────────────────────────────
memory = AgentMemory(config_path="config.yaml")

# ── 2. Store episodic memories ────────────────────────────────
memory.remember(
    "Fixed login refresh token bug. The middleware was not invalidating "
    "the old token after rotation, causing duplicate sessions.",
    memory_type="bugfix",
    tags=["auth", "login", "security"],
    files=["auth.ts", "refresh_token.ts"],
)

memory.remember(
    "Refactored payment service to use BullMQ for async processing.",
    memory_type="refactor",
    tags=["payments", "queue"],
    files=["payment_service.ts"],
)

memory.remember(
    "Added integration tests for the OAuth2 flow.",
    memory_type="testing",
    tags=["auth", "oauth", "tests"],
    files=["tests/auth.test.ts"],
)

print("✅ Stored 3 episodic memories.")

# ── 3. Add a semantic note ────────────────────────────────────
memory.semantic.create_note(
    title="Login Bug Postmortem",
    content=(
        "## Root Cause\n\n"
        "The refresh token middleware was not calling `invalidateOldToken()` "
        "after issuing a new pair. This allowed stale tokens to remain valid.\n\n"
        "## Fix\n\nAdded Redis DEL call on old token hash after rotation.\n\n"
        "## Related\n\n[[auth]] [[architecture]]\n"
    ),
    tags=["postmortem", "auth", "bugfix"],
)
print("✅ Created semantic note.")

# ── 4. Sync vault ─────────────────────────────────────────────
count = memory.sync_vault()
print(f"✅ Vault synced: {count} documents.")

# ── 5. Hybrid search ──────────────────────────────────────────
print("\n🔍 Searching: 'login bug'...\n")
result = memory.retrieve("login bug", top_k=3)

print("📼 Episodic hits:")
for hit in result.episodic_hits:
    print(f"  [{hit.entry.memory_type}] {hit.entry.content[:80]}  (score={hit.score:.3f})")

print("\n📚 Semantic hits:")
for doc in result.semantic_hits:
    print(f"  {doc.title} ({doc.path})  (score={doc.score:.3f})")

# ── 6. Build LLM prompt ───────────────────────────────────────
print("\n🧠 LLM-ready context:\n")
print(result.to_prompt())

# ── 7. Stats ──────────────────────────────────────────────────
print("\n📊 Memory stats:")
import json
print(json.dumps(memory.stats(), indent=2))

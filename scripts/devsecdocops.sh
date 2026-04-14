#!/usr/bin/env bash
#
# devsecdocops.sh — DevSecDocOps Orchestrator
#
# Se ejecuta en el workflow de PR y coordina:
# 1. Captura del PR → 2. Pipeline checks → 3. Doc generation → 4. Vault sync
#
# Uso (en GitHub Actions):
#   bash scripts/devsecdocops.sh capture --title "..." --author "..." ...
#   bash scripts/devsecdocops.sh store --lint-result "pass" --audit-result "fail" ...
#   bash scripts/devsecdocops.sh search
#   bash scripts/devsecdocops.sh generate
#   bash scripts/devsecdocops.sh full --title "..." ...
#

set -euo pipefail

VAULT_PATH="${CORTEX_VAULT_PATH:-vault}"
CONTEXT_FILE="${CORTEX_CONTEXT_FILE:-.pr-context.json}"
PAST_CONTEXT_FILE="${CORTEX_PAST_CONTEXT_FILE:-.past-context.json}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_ok() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

usage() {
    cat << 'EOF'
Usage: devsecdocops.sh <command> [options]

Commands:
  capture    Capture PR metadata from environment/GitHub
  store      Store pipeline results in episodic memory
  search     Search for similar past PRs
  generate   Generate documentation from PR context
  full       Run the complete pipeline (capture + store + search + generate + sync)

Options (for capture/full):
  --title          PR title
  --body           PR body/description
  --author         PR author
  --branch         Source branch
  --commit         Commit SHA
  --pr-number      PR number
  --target-branch  Target branch (default: main)
  --labels         Comma-separated labels

Options (for store):
  --lint-result    Lint result (pass/fail)
  --audit-result   Audit result (pass/fail)
  --test-result    Test result (pass/fail)
EOF
}

# ── Parse common options ──────────────────────────────────────────

parse_options() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --title) TITLE="$2"; shift 2 ;;
            --body) BODY="$2"; shift 2 ;;
            --author) AUTHOR="$2"; shift 2 ;;
            --branch) BRANCH="$2"; shift 2 ;;
            --commit) COMMIT="$2"; shift 2 ;;
            --pr-number) PR_NUMBER="$2"; shift 2 ;;
            --target-branch) TARGET_BRANCH="$2"; shift 2 ;;
            --labels) LABELS="$2"; shift 2 ;;
            --lint-result) LINT_RESULT="$2"; shift 2 ;;
            --audit-result) AUDIT_RESULT="$2"; shift 2 ;;
            --test-result) TEST_RESULT="$2"; shift 2 ;;
            --help|-h) usage; exit 0 ;;
            *) log_error "Unknown option: $1"; usage; exit 1 ;;
        esac
    done
}

# ── Commands ──────────────────────────────────────────────────────

cmd_capture() {
    parse_options "$@"

    log_info "Capturing PR context..."

    cortex pr-context capture \
        --title "${TITLE:-Untitled PR}" \
        --body "${BODY:-}" \
        --author "${AUTHOR:-unknown}" \
        --branch "${BRANCH:-}" \
        --commit "${COMMIT:-}" \
        --pr-number "${PR_NUMBER:-0}" \
        --target-branch "${TARGET_BRANCH:-main}" \
        --labels "${LABELS:-}" \
        --output "$CONTEXT_FILE"

    log_ok "PR context captured -> $CONTEXT_FILE"
}

cmd_store() {
    parse_options "$@"

    log_info "Storing PR context in episodic memory..."

    if [[ ! -f "$CONTEXT_FILE" ]]; then
        log_error "Context file not found: $CONTEXT_FILE. Run 'capture' first."
        exit 1
    fi

    cortex pr-context store \
        --context-file "$CONTEXT_FILE" \
        --lint-result "${LINT_RESULT:-}" \
        --audit-result "${AUDIT_RESULT:-}" \
        --test-result "${TEST_RESULT:-}"

    log_ok "PR context stored in memory"
}

cmd_search() {
    parse_options "$@"

    log_info "Searching for similar past PRs..."

    if [[ ! -f "$CONTEXT_FILE" ]]; then
        log_error "Context file not found: $CONTEXT_FILE. Run 'capture' first."
        exit 1
    fi

    cortex pr-context search \
        --context-file "$CONTEXT_FILE" \
        --output "$PAST_CONTEXT_FILE"

    log_ok "Past context search saved -> $PAST_CONTEXT_FILE"
}

cmd_generate() {
    parse_options "$@"

    log_info "Generating documentation from PR context..."

    if [[ ! -f "$CONTEXT_FILE" ]]; then
        log_error "Context file not found: $CONTEXT_FILE. Run 'capture' first."
        exit 1
    fi

    cortex pr-context generate \
        --context-file "$CONTEXT_FILE" \
        --vault "$VAULT_PATH"

    log_ok "Documentation generated"
}

cmd_full() {
    parse_options "$@"

    log_info "═══════════════════════════════════════════════════"
    log_info "🧠 Cortex DevSecDocOps — Full PR Context Pipeline"
    log_info "═══════════════════════════════════════════════════"
    echo ""

    cmd_capture "$@"
    echo ""

    cmd_store "$@"
    echo ""

    cmd_search "$@"
    echo ""

    cmd_generate "$@"
    echo ""

    log_info "Syncing vault..."
    cortex sync-vault
    log_ok "Vault synced"
    echo ""

    log_info "═══════════════════════════════════════════════════"
    log_ok "✅ DevSecDocOps pipeline complete"
    log_info "═══════════════════════════════════════════════════"
}

# ── Main ──────────────────────────────────────────────────────────

if [[ $# -lt 1 ]]; then
    usage
    exit 1
fi

COMMAND="$1"
shift

case "$COMMAND" in
    capture)  cmd_capture "$@" ;;
    store)    cmd_store "$@" ;;
    search)   cmd_search "$@" ;;
    generate) cmd_generate "$@" ;;
    full)     cmd_full "$@" ;;
    help|-h|--help) usage; exit 0 ;;
    *) log_error "Unknown command: $COMMAND"; usage; exit 1 ;;
esac

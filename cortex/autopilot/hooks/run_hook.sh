#!/usr/bin/env bash
set -euo pipefail
# Cortex Autopilot hook wrapper for Unix-like systems.
# Usage: run_hook.sh <module_name> [args...]
# Example: run_hook.sh session_start --project-root /path/to/repo

python -m cortex.autopilot.hooks."$@" 2>&1 || {
    echo '{"error": "Hook failed or Python not in PATH"}'
    exit 1
}

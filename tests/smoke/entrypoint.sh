#!/bin/bash
set -euo pipefail

# Cortex Smoke Test — Flujo completo de usuario virgen
cd /tmp
rm -rf test-project && mkdir test-project && cd test-project

git init
git config user.name "Smoke"
git config user.email "smoke@test.com"

echo "🧠 Smoke: setup agent"
cortex setup agent --git-depth 5 --ide pi

echo "🧠 Smoke: doctor"
cortex doctor

echo "🧠 Smoke: setup full"
cortex setup full --git-depth 5

echo "🧠 Smoke: setup enterprise"
cortex setup enterprise --preset small-company --non-interactive

echo "🧠 Smoke: remember"
cortex remember "Smoke test memory" --tag smoke

echo "🧠 Smoke: search"
cortex search "smoke test"

echo "🧠 Smoke: memory-report"
cortex memory-report --json

echo "🧠 Smoke: pr-context capture"
cortex pr-context capture --title "Smoke PR" --output /tmp/pr.json

test -f /tmp/pr.json || { echo "❌ /tmp/pr.json no existe"; exit 1; }

echo "✅ Smoke test completado con éxito"

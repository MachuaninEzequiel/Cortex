# Fase 8 — Integración con Contexto y Budget: Realización

## Fecha
2026-05-09

## Resumen
Se implementó la integración entre Autopilot y el sistema de contexto (`AgentMemory.enrich()`) con presupuesto agresivo y medible. Se crearon `budget_profiles.py` y `context.py`, se extendió `AutopilotService` con `build_context()`, y se agregaron 24 tests.

## Archivos creados
1. `cortex/autopilot/budget_profiles.py` — funciones para derivar el perfil de presupuesto desde el estado, aplicar límites a `EnrichedContext`, y generar `AutopilotBudgetSnapshot`.
2. `cortex/autopilot/context.py` — orquesta `fetch_context()` que:
   - Deriva el perfil desde `AutopilotSessionState`
   - Short-circuit para `question_only` (sin embeddings, sin retrieval)
   - Limita `top_k` según el perfil (`fast_code` → 5, `deep_code` → 8)
   - Formatea output compacto y trunca a `max_chars`
   - Fallback graceful cuando `AgentMemory` no está disponible
3. `tests/unit/autopilot/test_context_budget.py` — 24 tests cubriendo perfiles, aplicación de budget, formato, conteo de items, fetch con mocks, y persistencia via `build_context()`.

## Archivos modificados
1. `cortex/autopilot/service.py`:
   - Importa `fetch_context` y `AutopilotBudgetSnapshot`
   - `preflight()` ahora siembra `state.budget.deep_track_reason` cuando la complejidad es `deep`
   - Nuevo método `build_context(session_id, memory=None)` que:
     - Llama `fetch_context()`
     - Persiste `state.budget` actualizado
     - Registra evento `"context"` en el store

## Diseño clave
- **Short-circuit agresivo**: `question_only` y perfiles con `max_items == 0` retornan prompt vacío sin tocar `AgentMemory`, ahorrando tokens y tiempo.
- **Inyección opcional de `AgentMemory`**: `fetch_context()` acepta `memory` como parámetro opcional. Si es `None`, intenta crear uno desde `project_root/config.yaml`; si falla, retorna fallback vacío. Esto hace que los tests sean rápidos (usando mocks) y el runtime sea robusto.
- **Presupuesto medible**: cada llamada retorna `ContextResult` con `prompt_text`, `budget` (chars, items, embeddings flag), y `profile_name`.
- **Integración con `EnrichedContext`**: usa `to_prompt_format(compact=True)` cuando está disponible; fallback a `to_prompt(max_chars=...)` o `str()`.
- **Truncado por perfil**:
  - `question_only`: 0 chars
  - `docs_only`: 1200 chars
  - `fast_code`: 2000 chars
  - `deep_code`: 3500 chars
  - `finish_only`: 2000 chars, sin retrieval

## Tests
- `pytest tests/unit/autopilot/test_context_budget.py` — 24/24 passed.
- Suite completa Autopilot — 218/218 passed (sin regresiones).

## Incidentes y resoluciones
1. **`question_only` no truncaba a cero**: `_format_enriched` retornaba el texto completo porque `len(text) > 0` es `False` cuando `max_chars == 0`. Se agregó un early-return explícito `if max_chars == 0: prompt_text = ""` en `apply_budget()`.
2. **`AgentMemory` requiere `config.yaml`**: en runtime esto es correcto, pero para tests se inyecta `memory` como mock. `fetch_context()` nunca falla silenciosamente; si `AgentMemory` no existe, retorna fallback vacío con budget en cero.
3. **Deep track reason se propagaba solo en `context.py`**: para que el reason persista en el estado, `preflight()` ahora guarda `detection.reason` en `state.budget.deep_track_reason` cuando `suggested_complexity == "deep"`.

---
title: "Simulación — Un día con la arquitectura Pluggable Middle"
status: draft
audience: dev nuevo a Cortex, contribuidor, evaluador
related:
  - docs/architecture/pluggable-middle-overview.md
  - docs/pluggable-middle/ARQUITECTURA-PLUGGABLE-MIDDLE.md
  - docs/enterprise/MANIFIESTO-CORTEX-ENTERPRISE.md
---

# Simulación — Un día con la arquitectura Pluggable Middle

Este documento simula, paso a paso, **una jornada típica de un dev** trabajando
sobre la nueva arquitectura de Cortex (Pluggable Middle). Hay **una simulación
por cada modo**:

1. 🟢 **Managed** — `cortex-SDDwork` orquesta todo (Deep Track).
2. 🟡 **Observed** — el dev usa su agente preferido + hooks IDE.
3. 🔵 **BYO** — desarrollo libre (manual o agente externo sin hooks).

Cada simulación termina con la promoción del conocimiento al **vault
enterprise** y una pasada por **webgraph** para ver el resultado. Entre medio
se ven los comandos auxiliares (`cortex session …`, `cortex doctor`,
`cortex search`, etc.) que el dev usa para chequear que la maquinaria sigue
viva.

> Convención de la simulación:
> - `>` líneas en el chat del IDE (lo que el dev tipea).
> - `$` líneas en una terminal.
> - Las respuestas de agentes y CLI están abreviadas pero son **fieles al
>   contrato**: no inventan tools ni outputs.

---

## 0. Preflight matinal (idéntico en los 3 modos)

09:30. El dev abre el IDE. Antes de tocar nada, valida que la infra está sana.

```
$ cortex doctor
[sessions]        OK  .cortex/sessions/ writable; active pointer valid
[autopilot]       OK  policy resolved (mode=managed); claude-code hooks installed
[pluggable_middle] OK  documenter modules importable; MCP tools registered
[enterprise]      OK  org.yaml v1 resolved (topology=multi-project-team)
[webgraph]        OK  fastapi, jinja2, uvicorn present; cache dir writable

✓ All checks passed.
```

```
$ cortex session list
ACTIVE SESSIONS
  (none)

RECENT (last 7 days)
ID                                       STATUS    CLOSED   MODE      NOTES
  2026-05-19_metrics-dashboard           closed    16h ago  observed  1 ADR
  2026-05-18_footer-styles               closed    1d ago   byo       0 ADRs
```

Nada abierto, nada huérfano. Bien. Mira el grafo para tener el mapa mental:

```
$ cortex webgraph serve --no-open
Webgraph server listening at http://127.0.0.1:8765
```

Lo deja corriendo en background y abre el navegador en una pestaña. Va a
volver al grafo cuando termine cada feature.

---

## 1. 🟢 Simulación A — Modo Managed (Deep Track)

**Ticket del día:** `AUTH-142 — Implementar refresh tokens JWT con rotación`.
Dev nuevo en el equipo, todavía no tiene skills propias; quiere disciplina
forzada y trazabilidad máxima.

### 1.1 Sync — preparar la spec

```
> /cortex-sync AUTH-142: Refresh tokens JWT con rotación cada 7 días, revocación instantánea, compatible con AWS Lambda
```

```
[cortex-sync]
→ cortex_sync_ticket(user_request="AUTH-142: refresh tokens JWT...")
  retrieved: 8 hits (3 vault, 2 ADRs, 2 session notes, 1 enterprise)
  ↳ ADR-2025-11-03 "Stateless auth con JWT" (vault enterprise)
  ↳ session 2026-04-22 "Login hardening" (vault local)
  ↳ CONTEXT.md términos canónicos: Auth Service Singleton, Session Token, Refresh Window

→ Glob: src/auth/**, tests/auth/**
→ read: src/auth/jwt.py, src/auth/middleware.py, CONTEXT.md

→ cortex_emit_proposal({
    summary: "Tres rutas posibles para rotación de refresh tokens",
    alternatives: [
      {id:"A", desc:"Server-side blacklist (Redis)", rejected:"Lambda → no warm Redis"},
      {id:"B", desc:"Rotación sin blacklist, TTL corto", rejected:"window de revocación = TTL"},
      {id:"C", desc:"Rotación + revocation table en RDS"}
    ],
    recommendation_id:"C",
    risks: ["RDS cold start", "Race entre rotation y revocation"]
  })

  📋 PROPOSAL CARD (visible al dev en el chat)
  ─────────────────────────────────────────────
  Recomendación: C (rotación + revocation table)
  ¿Aprobás? [responde ok / o sugerí cambios]
```

```
> ok
```

```
[cortex-sync]
→ cortex_create_spec(
    title="Refresh tokens JWT con rotación",
    files_in_scope=["src/auth/jwt.py","src/auth/middleware.py","src/auth/revocation.py","tests/auth/test_refresh.py"],
    verification_hooks=[
      {name:"tests",   command:"pytest tests/auth/", required:true},
      {name:"types",   command:"mypy src/auth/",     required:true},
      {name:"lint",    command:"ruff check src/auth/", required:false}
    ],
    proposal_mode="required",
    proposal_confirmed=true
  )
  ✓ spec persistida → .cortex/vault/specs/2026-05-20_refresh-tokens-jwt.md
  ✓ session abierta → .cortex/sessions/2026-05-20_refresh-tokens-jwt.yaml
  ✓ start_commit=8530f31  start_branch=feature/refresh-tokens

✅ Spec técnica completada y persistida en el Vault.
   ¿Cómo querés desarrollar?
     1. cortex-SDDwork (managed, recomendado)
     2. Tu propio agente
     3. Manual
```

Quick sanity check antes de seguir:

```
$ cortex session status
📋 Session: 2026-05-20_refresh-tokens-jwt
   Status:    🟢 open
   Mode:      unknown (se infiere al cerrar)
   Spec:      .cortex/vault/specs/2026-05-20_refresh-tokens-jwt.md
   Files in scope: 4 | Verification hooks: 3 (2 required)
   Checkpoints: 0
```

### 1.2 SDDwork — orquestar Deep Track

```
> /cortex-SDDwork
```

```
[cortex-SDDwork]
→ cortex_ping → status:"ok"
→ cortex_session_status → session activa: 2026-05-20_refresh-tokens-jwt

Routing: 4 archivos in-scope + cambio arquitectónico → 🔴 DEEP TRACK
Pipeline: explorer → designer → implementer

[1/3] Delegando a cortex-code-explorer…
```

#### Explorer

```
[cortex-code-explorer]  (subagent vía Task tool)
→ cortex_search "refresh token revocation" scope=all
  3 hits relevantes (1 enterprise ADR sobre revocation pattern).
→ read src/auth/jwt.py, src/auth/middleware.py
→ grep "issue_refresh|rotate" → solo aparece en tests legacy

→ cortex_session_checkpoint(
    source="cortex-code-explorer",
    verified_claims=[
      "jwt.py exporta encode/decode; sin estado",
      "middleware.py intercepta Authorization header en línea 42",
      "no existe tabla revocation_tokens en schema actual"
    ],
    unverified_claims=[],
    artifacts_touched=["src/auth/jwt.py","src/auth/middleware.py","tests/auth/test_login.py"],
    note="designer: hace falta nueva tabla revocation_tokens (jti, revoked_at). implementer: middleware.py espera dict, no objeto JWT — cuidado con el shape."
  )

✅ Exploración terminada. Checkpoint emitido. (3 archivos; 2 dependencias)
```

```
[cortex-SDDwork]
→ cortex_review_checkpoint  (default = último)
  result: { action: "accept", reason: "claims trazables y completos" }

[2/3] Delegando a cortex-code-designer…
```

#### Designer

```
[cortex-code-designer]
→ read spec, read checkpoint del explorer
→ write_design_note_canonical(
    title="Design — refresh tokens JWT",
    session_id="2026-05-20_refresh-tokens-jwt",
    architecture_decision="Rotación + revocation table en RDS...",
    data_model_changes=[
      "Nueva tabla revocation_tokens (jti PK, revoked_at, user_id FK)",
      "Migración 0042_revocation_tokens.sql"
    ],
    api_contracts=[
      "issue_refresh(user_id: str) -> (access_jwt, refresh_jwt)",
      "rotate_refresh(refresh_jwt: str) -> (access_jwt, refresh_jwt)",
      "revoke(jti: str) -> None"
    ],
    test_plan=[
      "test_refresh.py: rotación happy path",
      "test_refresh.py: revocación inmediata invalida",
      "test_refresh.py: refresh expirado falla"
    ],
    risks=["RDS cold start en Lambda","Race entre rotate y revoke (mitigación: SELECT FOR UPDATE)"]
  )
  ✓ vault/designs/2026-05-20_refresh-tokens-jwt.md

→ cortex_session_checkpoint(
    source="cortex-code-designer",
    verified_claims=["design doc persistido"],
    note="implementer: NO uses TTL hardcodeado; pasalo por config. ADR-candidato: trade-off RDS-vs-Redis."
  )

✅ Design completado. Path: vault/designs/2026-05-20_refresh-tokens-jwt.md.
```

```
[cortex-SDDwork]
→ cortex_review_checkpoint → action: "accept"

[3/3] Delegando a cortex-code-implementer con design path…
```

#### Implementer

```
[cortex-code-implementer]
→ read vault/designs/2026-05-20_refresh-tokens-jwt.md  (NO improvisar)
→ write src/auth/revocation.py
→ edit  src/auth/jwt.py        (issue_refresh, rotate_refresh)
→ edit  src/auth/middleware.py (chequea revocation_tokens)
→ write tests/auth/test_refresh.py
→ execute_command "pytest tests/auth/"  →  12 passed in 1.8s

→ cortex_session_checkpoint(
    source="cortex-code-implementer",
    verified_claims=[
      "src/auth/revocation.py creado (jti, revoked_at)",
      "src/auth/jwt.py: rotate_refresh con SELECT FOR UPDATE",
      "pytest tests/auth/ — 12/12 passed",
      "mypy src/auth/ — Success"
    ],
    unverified_claims=["performance bajo carga (no benchmarked)"],
    artifacts_touched=[
      "src/auth/jwt.py","src/auth/middleware.py",
      "src/auth/revocation.py","tests/auth/test_refresh.py",
      "migrations/0042_revocation_tokens.sql"
    ],
    note="documenter: TTL movido a config.yaml (REFRESH_TTL=604800). Posible ADR: elegir RDS sobre Redis (cumple 3 criterios). Race condition mitigada con SELECT FOR UPDATE."
  )

✅ Implementación terminada. (5 archivos; 12 tests OK)
```

```
[cortex-SDDwork]
→ cortex_review_checkpoint → action: "accept"
→ cortex_session_checkpoint(
    source="cortex-SDDwork",
    verified_claims=["Deep Track completo: explorer+designer+implementer ejecutados"],
    note="documenter: candidato ADR claro (RDS vs Redis). 1 archivo nuevo + 4 modificados."
  )

🚀 Implementación completada (Deep Track).
   Cambia al anchor de cierre:
     /cortex-documenter
   o (rápido sin criterio editorial):
     cortex finish-session
```

### 1.3 Chequeo intermedio antes de cerrar

```
$ cortex session show
📋 Session: 2026-05-20_refresh-tokens-jwt
   Status:    🟢 open
   Mode:      managed (inferido: solo checkpoints Cortex)
   Files touched: 5 (4 in scope, 1 nuevo — migrations/0042…sql ⚠️ scope drift)
   Lines:         +234 -47   Commits: 3 since start_commit

📍 Checkpoints (4)
   ├─ explorer    "no existe tabla revocation_tokens"
   ├─ designer    "design persistido"
   ├─ implementer "12/12 tests OK"
   └─ SDDwork     "Deep Track completo"

🎯 Spec Verification
   ⏸  tests (not yet run by documenter)
   ⏸  types
   ⏸  lint

💡 Next: cortex finish-session --interactive
```

```
$ cortex session diff | wc -l
       287
```

El scope drift de la migration es esperado (lo recomendó el designer). Cierra
en modo **interactive** para ver el draft antes de persistir.

### 1.4 Documenter — cierre interactivo

```
$ cortex finish-session --interactive

[documenter] Reconstruyendo session 2026-05-20_refresh-tokens-jwt
[documenter] git diff 8530f31..HEAD → 5 archivos
[documenter] Verification hooks:
             ✅ tests (pytest tests/auth/ — 12 passed)
             ✅ types (mypy — Success)
             ✅ lint  (ruff — clean)
[documenter] Cross-check contradictions in memoria… 0 conflictos.
[documenter] ADR candidates: 1 (RDS vs Redis — cumple 3/3 criterios)

═══════════════════════════════════════════════════════════
DRAFT SESSION NOTE
═══════════════════════════════════════════════════════════
# Refresh Tokens JWT — rotación + revocation
status: completed   date: 2026-05-20   tags: [session, auth, jwt]

## Cambios verificados
- src/auth/revocation.py (nuevo, +58)
- src/auth/jwt.py: issue_refresh, rotate_refresh (+72 -12)
- src/auth/middleware.py: lookup revocation_tokens (+18 -3)
- migrations/0042_revocation_tokens.sql (nuevo)
- tests/auth/test_refresh.py (+86)

## Decisiones in-flight
- TTL movido a config.yaml (REFRESH_TTL). Antes hardcodeado.
- SELECT FOR UPDATE en rotate_refresh para evitar race con revoke.

## Discrepancias detectadas
- (ninguna)

═══════════════════════════════════════════════════════════
ADR SUGERIDO
═══════════════════════════════════════════════════════════
🟢 ADR-2026-05-20 — "Revocation en RDS sobre Redis para Lambda"
   ✓ Hard to reverse (migración + código de middleware)
   ✓ Surprising (default sería Redis)
   ✓ Trade-off real (cold start vs warm cache)
   → ¿Crear? [Y/n/edit]:  Y

═══════════════════════════════════════════════════════════
[A]probar y persistir   [E]ditar   [H]andoff   [C]ancelar
> A

✅ vault/sessions/2026-05-20_refresh-tokens-jwt.md  (87 lines)
✅ vault/adrs/2026-05-20_revocation-rds-vs-redis.md
✅ Session 2026-05-20_refresh-tokens-jwt → status: closed (mode: managed)
✅ Indexed en memoria episódica + semántica (3 chunks)
```

### 1.5 Promoción al vault enterprise

Esta es una decisión arquitectónica con valor cross-project. El dev quiere
que viva en el vault corporativo, no sólo en su repo.

```
$ cortex review-knowledge candidate vault/adrs/2026-05-20_revocation-rds-vs-redis.md \
    --reason "ADR transversal: misma decisión va a aparecer en payments + notifications"

✓ Candidato registrado.
  id:           cand-2026-05-20-a7f3
  source:       vault/adrs/2026-05-20_revocation-rds-vs-redis.md
  dest (plan):  enterprise/adrs/2026-05-20_revocation-rds-vs-redis.md
  status:       pending
```

El reviewer del equipo (otro dev, el tech lead, o el mismo dev con permisos)
revisa el queue:

```
$ cortex review-knowledge pending
PENDING (1)
  cand-2026-05-20-a7f3   ADR  revocation-rds-vs-redis   by: ezequiel
                         reason: "ADR transversal: misma decisión va a aparecer…"

$ cortex review-knowledge approve cand-2026-05-20-a7f3 \
    --reviewer "tech-lead@org" --note "OK; aplica a auth+payments+notifications"
✓ Candidato aprobado. status: reviewed.
```

Ahora el dev (o un job de CI) promueve los aprobados:

```
$ cortex promote-knowledge --dry-run
Planned promotions: 1
  - vault/adrs/2026-05-20_revocation-rds-vs-redis.md -> enterprise/adrs/2026-05-20_revocation-rds-vs-redis.md  (cand-2026-05-20-a7f3)

$ cortex promote-knowledge --apply --actor ezequiel
Promoted 1 document(s) into /org/cortex-enterprise-vault
  - vault/adrs/2026-05-20_revocation-rds-vs-redis.md -> enterprise/adrs/2026-05-20_revocation-rds-vs-redis.md

$ cortex sync-enterprise-vault
Enterprise vault synced (1 docs indexed, 0 warning(s)).
Validation report: .enterprise-doc-validation.json
```

Verifica que la memoria multi-nivel ya lo retorna:

```
$ cortex search "revocation rds lambda" --scope enterprise --limit 3
  [0.91] enterprise/adrs/2026-05-20_revocation-rds-vs-redis.md
         "...elegimos RDS sobre Redis para que el cold start de Lambda no…"
  [0.74] enterprise/adrs/2025-11-03_stateless-auth-jwt.md
  [0.63] enterprise/sessions/2025-09-12_lambda-cold-start.md
```

```
$ cortex memory-report --scope enterprise --json | jq '.promotions.last_7d'
{
  "candidates":   3,
  "reviewed":     2,
  "promoted":     1,
  "rejected":     1
}
```

### 1.6 Webgraph — ver el nodo nuevo

El dev refresca la pestaña del webgraph (que dejó abierta en 09:30):

- En el grafo aparece **un nodo nuevo verde** (session note) con dos aristas:
  - `→ spec` (relación `derives_from`)
  - `→ adr` (relación `produces`)
- El ADR nuevo tiene **edge punteada** hacia el vault enterprise (relación
  `promoted_to`), porque fue promovido.

Si quiere snapshot estático para el PR:

```
$ cortex webgraph export --mode hybrid --output reports/refresh-tokens-graph.json
Webgraph snapshot exported -> reports/refresh-tokens-graph.json
```

```
$ cortex session list
ACTIVE SESSIONS
  (none)
RECENT
  ► 2026-05-20_refresh-tokens-jwt   closed  6m ago  managed  1 ADR  1 promoted
```

✅ Modo Managed cerrado. Tiempo total: ~1h 50min.

---

## 2. 🟡 Simulación B — Modo Observed (Cursor + IDE hooks)

13:45. Vuelve de almorzar. Próximo ticket: `UI-87 — Dashboard de métricas:
agregar widget de p95 latency`. El dev **prefiere Cursor Composer** con sus
skills custom de React; no quiere que SDDwork orqueste. Pero igual quiere
que Cortex registre la sesión.

### 2.1 Instalar hooks IDE (una sola vez por repo)

```
$ cortex session hooks install --ide cursor
✓ instalado: .git/hooks/post-commit  → cortex session checkpoint --source ide-hook --event commit
✓ instalado: .git/hooks/pre-push    → cortex session checkpoint --source ide-hook --event push
✓ slash command registrado: /cortex-checkpoint en Cursor
```

```
$ cortex session hooks list
ide          status   path
cursor       active   .git/hooks/post-commit, .git/hooks/pre-push
claude-code  active   .claude/settings.json
pi           -        (not installed)
```

### 2.2 Sync (sigue siendo obligatorio)

```
> /cortex-sync UI-87: agregar widget p95 latency al dashboard de métricas
```

```
[cortex-sync]
→ cortex_sync_ticket → 4 hits (1 ADR sobre chart library, 2 sessions, 1 enterprise note)
→ glob src/dashboard/**
→ cortex_emit_proposal({A:"recharts",B:"d3 manual",C:"recharts + memoized selector"}, rec="C")
> ok
→ cortex_create_spec(
    files_in_scope=["src/dashboard/Widgets.tsx","src/dashboard/selectors.ts","tests/dashboard.test.tsx"],
    verification_hooks=[
      {name:"tests", command:"npm test -- dashboard"},
      {name:"types", command:"tsc --noEmit"},
      {name:"snapshot", command:"npm run snapshot:dashboard"}
    ]
  )
✓ session abierta: 2026-05-20_dashboard-p95-widget
```

### 2.3 Cursor Composer trabaja (Cortex sólo observa)

El dev abre Cursor y le pasa el spec a su skill custom. **No** invoca
`/cortex-SDDwork`. Trabaja durante 50 minutos. Mientras tanto:

```
# commit 1 — implementación inicial
$ git commit -m "feat: add p95 widget skeleton"
[post-commit hook]
  → cortex session checkpoint --source ide-hook --event commit \
        --note "feat: add p95 widget skeleton" \
        --artifacts src/dashboard/Widgets.tsx

# commit 2 — selector memoizado
$ git commit -m "perf: memoize p95 selector"
[post-commit hook]
  → cortex session checkpoint --source ide-hook --event commit ...

# tests
$ npm test -- dashboard
PASS  tests/dashboard.test.tsx (8 tests)
$ cortex session checkpoint --source user-skill \
    --verified "npm test dashboard — 8/8 ok" \
    --note "decisión: useMemo en lugar de useCallback porque recompila gráfico"
```

Mira cómo va el progreso:

```
$ cortex session show

📋 Session: 2026-05-20_dashboard-p95-widget
   Mode (inferred so far): observed
   Checkpoints (3):
     ├─ 14:02 ide-hook    commit "feat: add p95 widget skeleton"
     ├─ 14:31 ide-hook    commit "perf: memoize p95 selector"
     └─ 14:48 user-skill  "npm test dashboard — 8/8 ok"
   Files touched: 3 (3 in scope)
   Lines: +112 -8
```

### 2.4 Cierre (interactive de nuevo, porque sigue habiendo decisiones)

```
$ cortex finish-session --interactive

[documenter] Modo: observed (3 checkpoints: 2 ide-hook + 1 user-skill)
[documenter] Verification hooks:
             ✅ tests (8/8)
             ✅ types
             ✅ snapshot (regenerado)

═══════════════════════════════════════════════════════════
DRAFT SESSION NOTE
═══════════════════════════════════════════════════════════
# Dashboard p95 latency widget
status: completed   tags: [session, dashboard, ui]

## Cambios verificados
- src/dashboard/Widgets.tsx: nuevo P95Widget (+89)
- src/dashboard/selectors.ts: selector memoizado (+15 -3)
- tests/dashboard.test.tsx: 3 nuevos tests (+8 -5)

## Decisiones in-flight (de checkpoints user-skill)
- useMemo > useCallback porque recompila el gráfico.

## ADR sugerido
- (ninguno) — no cumple criterios 3/3.

[A/E/H/C]> A

✅ vault/sessions/2026-05-20_dashboard-p95-widget.md
✅ Session → closed (mode: observed)
```

### 2.5 ¿Promover esto? No

```
$ cortex search "dashboard widget memoization" --scope local --limit 3
  [0.88] vault/sessions/2026-05-20_dashboard-p95-widget.md
```

El dev decide **no promover**: es una decisión local de UX, no transversal.
Lo deja en el vault local. **No todo va al enterprise; el filtro es señal.**

### 2.6 Webgraph

Refresca el grafo y ve el nuevo nodo session conectado al spec, **sin** edge
hacia enterprise (no fue promovido). Útil para verificar de un vistazo que
**lo importante sí está promovido y lo local no contamina** el vault
corporativo.

✅ Modo Observed cerrado. Tiempo total: ~1h.

---

## 3. 🔵 Simulación C — Modo BYO (vibe coding total)

16:30. Último ticket del día: `STYLE-09 — Ajustar padding y color del footer
del landing`. Triviaridad pura. El dev no quiere ni Cursor: lo hace a mano en
un editor cualquiera, sin agentes, sin hooks. Pero **quiere igual la nota de
sesión** para que mañana cuando alguien busque "footer padding" en RRF lo
encuentre.

### 3.1 Sync (sigue siendo el contrato de entrada)

Aún en BYO, **el spec con verification_hooks es obligatorio** — es lo que le
da al documenter algo objetivo para validar al cierre.

```
> /cortex-sync STYLE-09: ajustar padding del footer del landing a 24px y color a #f5f5f7
```

```
[cortex-sync]
→ cortex_sync_ticket → 1 hit (ADR enterprise sobre design tokens)
→ glob src/landing/**, src/styles/tokens.css
→ cortex_emit_proposal({A:"hex hardcoded",B:"design token",C:"design token + storybook snapshot"}, rec="C")
> ok
→ cortex_create_spec(
    files_in_scope=["src/landing/Footer.tsx","src/styles/tokens.css"],
    verification_hooks=[
      {name:"build",    command:"npm run build"},
      {name:"snapshot", command:"npm run snapshot:landing"}
    ]
  )
✓ session abierta: 2026-05-20_footer-tweaks
```

### 3.2 Trabajo BYO

```
> (cierra el chat, abre Notepad++, cambia 2 archivos a mano, vuelve)
```

Sin checkpoints, sin agentes, sin hooks. Cero ruido.

```
$ cortex session show
📋 Session: 2026-05-20_footer-tweaks
   Mode (inferred so far): byo
   Checkpoints (0)
   Files touched: 2 (2 in scope)   Lines: +4 -4
```

### 3.3 Cierre (modo auto está bien — cambio trivial)

```
$ cortex finish-session
[documenter] Modo: byo (0 checkpoints)
[documenter] git diff abc123..HEAD → 2 archivos
[documenter] Verification hooks:
             ✅ build (npm run build — 0 errors)
             ✅ snapshot (sin diff visual significativo — 1px tolerance OK)
[documenter] ADR candidates: 0
[documenter] No interactividad solicitada — persistiendo auto.

✅ vault/sessions/2026-05-20_footer-tweaks.md
   "# Footer padding ajustado a 24px (token --space-6)
    ## Cambios verificados
    - src/styles/tokens.css: --footer-pad 16px → 24px
    - src/landing/Footer.tsx: usa token en lugar de hardcoded
    ## Decisiones in-flight
    - (ninguna)
    ## ADR sugerido
    - (ninguno)"
✅ Session → closed (mode: byo)
```

### 3.4 Promoción — sólo si toca tokens del design system enterprise

Cambiar el token `--space-6` afecta a **todos los productos** que importan
el design system desde el vault enterprise. Lo nomina:

```
$ cortex review-knowledge candidate vault/sessions/2026-05-20_footer-tweaks.md \
    --reason "Cambio de token afecta a otros productos que importan design system"

✓ Candidato registrado: cand-2026-05-20-b8c1   status: pending
```

El reviewer lo mira y **lo rechaza** (es chico, no amerita ruido en el vault
corporativo):

```
$ cortex review-knowledge reject cand-2026-05-20-b8c1 \
    --reviewer "tech-lead@org" --note "Es un tweak local; si cambia el design system de verdad, abrimos ADR"
✗ Candidato rechazado.

$ cortex review-knowledge pending
PENDING (0)
```

Esto **también es señal**: el queue de promoción no se contamina; el
enterprise vault sólo recibe lo que el equipo aprobó explícitamente.

### 3.5 Webgraph final

Refresca por última vez:

- Nodo session **gris** (modo BYO, low-context).
- **Sin** edges salientes a enterprise.
- El ADR de la mañana sigue iluminado con su edge `promoted_to` hacia el
  vault enterprise.

```
$ cortex memory-report --scope all
LOCAL VAULT
  sessions: 3 (+3 hoy)   adrs: 1 (+1)   handoffs: 0

ENTERPRISE VAULT
  promotions today:   1 ADR (cand-2026-05-20-a7f3)
  pending review:     0
  rejected today:     1 (cand-2026-05-20-b8c1)
  total docs:         147   last sync: 8m ago
```

---

## 4. Resumen de la jornada (mapa mental para el dev nuevo)

| Hora  | Ticket    | Modo     | Subagentes | Checkpoints | ADR | Promovido |
|-------|-----------|----------|------------|-------------|-----|-----------|
| 09:30 | preflight | —        | —          | —           | —   | —         |
| 10:00 | AUTH-142  | Managed  | explorer, designer, implementer | 4 | 1 | ✅ ADR |
| 13:45 | UI-87     | Observed | (Cursor)   | 3 (2 hook + 1 skill) | 0 | ❌ |
| 16:30 | STYLE-09  | BYO      | (ninguno)  | 0           | 0   | ❌ rechazado |

### Principios que se reforzaron en el día

1. **Sync y documenter no son negociables.** Cualquier modo arranca con
   `cortex-sync` (que abre la Session) y termina con `cortex finish-session`
   (que dispara al documenter).
2. **El middle es elección, no obligación.** Managed sirve para dev nuevo o
   tareas complejas; Observed para quien tiene tooling propio; BYO para
   triviales.
3. **El spec con `verification_hooks` es el contrato.** Sin eso, el
   documenter no puede cerrar la sesión con `complete` — la cierra como
   `handoff` y el equipo lo ve en el grafo.
4. **Checkpoint rico > checkpoint frecuente.** 1–3 checkpoints por sesión,
   no 50.
5. **La promoción al enterprise vault es deliberada.** El queue de
   `review-knowledge` filtra el ruido: lo que no aporta cross-project, se
   queda en el vault local (o se rechaza).
6. **Webgraph + memory-report son los espejos.** Cualquier divergencia entre
   lo que el dev cree que pasó y lo que la memoria muestra se ve ahí — no
   en el chat del IDE.

### Atajos / comandos de bolsillo que el dev usó hoy

```
cortex doctor                       # antes de empezar
cortex session list                 # ver qué hay abierto
cortex session status               # detalle de la activa
cortex session show <id>            # detalle de cualquiera
cortex session diff                 # diff desde start_commit
cortex session hooks install --ide cursor
cortex session watch                # TUI live de la sesión activa
cortex finish-session [--interactive | --handoff]
cortex review-knowledge candidate <path> --reason "..."
cortex review-knowledge pending | approve <id> | reject <id>
cortex promote-knowledge --dry-run | --apply
cortex sync-enterprise-vault
cortex search "..." --scope enterprise
cortex memory-report --scope all --json
cortex webgraph serve | export
```

---

## 5. Anti-patterns observados (y evitados)

| Antipatrón                                                    | Por qué falla                                                    |
|---------------------------------------------------------------|------------------------------------------------------------------|
| Saltarse `cortex-sync` y empezar a codear                     | MCP rechaza `create_spec` sin `sync_ticket` previo               |
| Emitir 50 checkpoints granulares                              | El documenter pierde señal; SDDwork prescribe 1–3 ricos          |
| Forzar promoción de todo                                      | Contamina el vault enterprise; el RRF cross-project pierde foco  |
| Cerrar con `complete` cuando los tests fallan                 | El verification gate fuerza `handoff` — no se puede forzar       |
| Invocar `cortex-documenter` directamente desde SDDwork        | Rompe el contrato: el usuario dispara el cierre con CLI/skill    |
| Editar manualmente `.cortex/sessions/<id>.yaml`               | El append-only se rompe; usar `cortex session checkpoint`        |

---

## 6. Próximos pasos sugeridos para el dev

- Mañana: revisar el queue de promoción con `cortex review-knowledge pending`
  apenas empieza la jornada.
- Cada viernes: `cortex memory-report --json > reports/memory-$(date +%F).json`
  para tener serie temporal de salud de memoria.
- Cuando aparezca un patrón cross-project: nominarlo como ADR enterprise
  desde el principio, no esperar a que se descubra retroactivamente.
- Para dudas: `cortex agent-guidelines` muestra las reglas canónicas; el
  webgraph muestra qué se ha tocado y qué no.

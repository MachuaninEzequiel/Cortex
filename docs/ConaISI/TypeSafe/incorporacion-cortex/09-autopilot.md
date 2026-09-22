# Autopilot

Módulos: `cortex/autopilot/{service,policies,detectors/*}.py`, `cortex-autopilot` (Rust), MCP `cortex_autopilot_{start,preflight,checkpoint,finish,status}`.

Capa de **política** sobre Session, no un segundo ciclo de vida (ficha del paquete). Lifecycle: start → preflight → checkpoint → finish. Policies: modos + enforcement + budget profiles (`fast_code` default).

## Detectores actuales

CodeChange, DocsOnly, QuestionOnly, SecuritySensitive, LargeRefactor, Noop, AmbiguousRequest. Protocol + resolution en `base.py`.

Son el input de:

- qué policy aplica,
- qué budget_profile recibe el enricher,
- si preflight exige clarificación.

Lexicon. SecuritySensitive pierde cambios de crypto con nombres inocentes. Ambiguous es un detector cuando debería ser **confidence baja**.

## Un call TypeSafe por request de Autopilot

State (ya lo tiene `DetectionRequest` / observer): utterance del usuario o del agente, files tocados/abiertos, keywords, sesión activa si hay.

```text
Choice task_kind
  code_change: implementation that edits code
  docs_only: documentation, vault notes, comments in markdown, no code behavior
  question_only: a question; no file changes expected
  security_sensitive: auth, crypto, permissions, secrets, tenancy, injection
  large_refactor: many files/modules, deep track
  noop: nothing to do, already done, or not a Cortex task
  other

Score complexity
  0: Simple lookup or standard procedure
  1: Multi-step but standard
  2: Unusual, cross-cutting, or escalation

Noul needs_clarification
  "Is the request too vague to start preflight without asking a clarifying question?"

Noul touches_secrets_or_auth
  companion de security_sensitive, más literal (jaggedness #1): 
  "Do the files or the request involve authentication, cryptography, authorization, or secret handling?"
```

Código (policies **sin reescribir**):

```text
si needs_clarification.noul >= 0.7 → AmbiguousRequest (el detector viejo muere como regex, vive como umbral)
si task_kind.confidence < 0.5 → tratar como mixed/fast_code, no deep_track
si task_kind.choice == security_sensitive o touches_secrets.noul >= 0.7 → policy security (enforcement más duro)
si large_refactor y complexity.score >= 1.5 → deep track + budget grande
si question_only → no abrir sesión de implementación; Brain/search
si noop → NoopDetector
```

`task_kind` con 7 opciones incluye `other` (docs TypeSafe: lista puede no cubrir). `other` + confidence media → humano / assist mode, no autopilot.

## Qué no mover

- `AutopilotService` lifecycle.
- `DocumenterFinalize` trait.
- `AutopilotError` tipados.
- Budget profiles como **datos** (`budget_resolver`). Solo cambia el detector que elige el perfil.
- Skills `using-cortex-autopilot` / extensión Pi: el contrato MCP de 5 tools se queda. El agente no sabe que adentro hay Jev.

## Relación con enricher y retrieval

El mismo Choice `task_kind` puede **compartirse** (un call, varias consumers). No preguntar task_type dos veces. El wrapper de juicio cachea por hash de state en el request HTTP del agente (no un cache global sucio).

## Mejora

Autopilot deja de ser “si el mensaje contiene `how do I` es QuestionOnly”. Un “how do I rotate the JWT secret without downtime?” es **security_sensitive** + complexity alta, no question_only. Eso cambia budget, policy y si se abre Deep Track. Es Intent routing del cookbook, aplicado al seam que Cortex ya llamó “Policy + hooks layer”.

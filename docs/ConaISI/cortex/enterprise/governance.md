# cortex/enterprise/governance.py

## Qué tiene adentro

- **Ruta de código:** `cortex/enterprise/governance.py` (153 líneas).
- **Módulo Python:** `cortex.enterprise.governance`.
- **Docstring del módulo:** cortex.enterprise.governance - Multi-tenant permissions and visibility.
- **Clases definidas:**
  - `GovernancePermissionError` (PermissionError)
    - Raised when a governance check denies an action.
- **Funciones de módulo:**
  - `user_team(actor, org)` — Resolve which team ``actor`` belongs to.
  - `team_can_promote(team_id, org)` — ``True`` if the team is allowed to promote knowledge.
  - `team_can_review(team_id, org)` — ``True`` if the team can approve/reject pending promotions.
  - `classification_visible_to(classification, team_id, org)` — Return ``True`` if ``team_id`` can see notes with the given classification.
  - `allowed_classifications_for(team_id, org)` — Return the list of classifications a team is allowed to see.
  - `assert_can_promote(actor, org)` — Validate that ``actor`` can promote; return the resolved team id.
  - `assert_can_review(actor, org)` — Validate that ``actor`` can review; return the resolved team id.
- **Constantes / símbolos de módulo:** `ADMIN_TEAM`, `__all__`

## Para qué sirve

cortex.enterprise.governance - Multi-tenant permissions and visibility.

Resolves *who can do what* and *who can see what* inside an enterprise
deployment, based on the ``teams`` / ``classifications`` / ``policies``
sections of ``org.yaml``.

The module is intentionally pure: it does not read filesystem, does not
import the writer or retrieval layers. It only reasons over the
``EnterpriseOrgConfig`` instance the caller already loaded.

Usage::

    org = EnterpriseOrgConfig.model_validate(yaml.safe_load(...))
    team_id = user_team("alice@cortex.ai", org)
    if not team_can_promote(team_id, org):
        raise PermissionError(...)

## Relaciones

### Recibe de

- `cortex.enterprise.models` (EnterpriseOrgConfig)
- Dependencias externas/stdlib: `__future__`

### Envía a

- `cortex.enterprise.promotion_doctype`

### Notas de implementación observadas en el código

Parseo AST correcto. Líneas: 153.
Docstrings de símbolos públicos:
- `user_team`: Resolve which team ``actor`` belongs to.
- `team_can_promote`: ``True`` if the team is allowed to promote knowledge.
- `team_can_review`: ``True`` if the team can approve/reject pending promotions.
- `classification_visible_to`: Return ``True`` if ``team_id`` can see notes with the given classification.
- `allowed_classifications_for`: Return the list of classifications a team is allowed to see.
- `assert_can_promote`: Validate that ``actor`` can promote; return the resolved team id.
- `assert_can_review`: Validate that ``actor`` can review; return the resolved team id.

---
Fuente: código de `cortex/enterprise/governance.py` (AST + grafo de imports internos). No se usó documentación previa.

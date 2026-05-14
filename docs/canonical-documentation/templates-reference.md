# Templates Reference - Jinja2 Templates Canonicos

**Documento:** templates `.md.j2` para cada DocType
**Audiencia:** implementadores
**Estado:** especificacion normativa

---

## 1. Ubicacion

```text
cortex/documentation/templates/
    session.md.j2
    handoff.md.j2
    spec.md.j2
    adr.md.j2
    decision.md.j2
    incident.md.j2
    postmortem.md.j2
    runbook.md.j2
    architecture.md.j2
    changelog.md.j2
    hu.md.j2
    glossary.md.j2
```

---

## 2. Convenciones

1. **Solo el body.** El template NO incluye el frontmatter YAML; el writer lo prepende.
2. **Jinja2 con autoescape OFF.** Markdown no escapa por defecto.
3. **Variables del template == campos del `XData` dataclass.** Convencion estricta.
4. **Secciones condicionales:** `{% if cond %}...{% endif %}` para campos opcionales.
5. **Listas con bullets:** `{% for item in list %}- {{ item }}\n{% endfor %}`.
6. **Wiki-links explicitos:** `[[name]]` para referencias internas.
7. **Headers consistentes:** H1 reservado para el titulo (a veces se omite si el frontmatter ya lo tiene); contenido empieza en H2.

---

## 3. Templates

### 3.1 `session.md.j2`

```jinja
## Original Specification

{{ spec_summary or "(none)" }}

## Changes Made

{% if changes_made %}
{% for change in changes_made %}- {{ change }}
{% endfor %}
{% else %}
(none)
{% endif %}

## Files Touched

{% if files_touched %}
{% for file in files_touched %}- `{{ file }}`
{% endfor %}
{% else %}
(none)
{% endif %}

## Key Decisions

{% if key_decisions %}
{% for decision in key_decisions %}- {{ decision }}
{% endfor %}
{% else %}
(none)
{% endif %}

## Next Steps

{% if next_steps %}
{% for step in next_steps %}- [ ] {{ step }}
{% endfor %}
{% else %}
(none)
{% endif %}

{% if verified_state %}
## Verified State

{% for v in verified_state %}- {{ v }}
{% endfor %}
{% endif %}

{% if unverified_claims %}
## Unverified Claims

{% for c in unverified_claims %}- {{ c }}
{% endfor %}
{% endif %}

{% if blockers %}
## Blockers

{% for b in blockers %}- {{ b }}
{% endfor %}
{% endif %}

{% if suggested_skills %}
## Suggested Skills for Next Session

{% for s in suggested_skills %}- {{ s }}
{% endfor %}
{% endif %}
```

### 3.2 `handoff.md.j2`

```jinja
## Context Required

{{ context_required }}

## What's Verified

{% for v in verified_state %}- {{ v }}
{% endfor %}

## What's Unverified

{% for c in unverified_claims %}- {{ c }}
{% endfor %}

## Blockers

{% for b in blockers %}- {{ b }}
{% endfor %}

## Next Session Needs

{% for n in next_session_needs %}- [ ] {{ n }}
{% endfor %}

## Suggested Skills

{% for s in suggested_skills %}- {{ s }}
{% endfor %}

## Parent Session

[[{{ parent_session_id }}]]
```

### 3.3 `spec.md.j2`

```jinja
## Goal

{{ goal }}

## Requirements

{% for r in requirements %}- {{ r }}
{% endfor %}

## Files in Scope

{% for f in files_in_scope %}- `{{ f }}`
{% endfor %}

## Constraints

{% for c in constraints %}- {{ c }}
{% endfor %}

## Acceptance Criteria

{% for a in acceptance_criteria %}- [ ] {{ a }}
{% endfor %}
```

### 3.4 `adr.md.j2`

```jinja
## Context

{{ context }}

## Decision

{{ decision }}

## Alternatives Considered

{% for alt in alternatives_considered %}- {{ alt }}
{% endfor %}

## Consequences

{{ consequences }}

{% if supersedes %}
## Supersedes

{% for prev in supersedes %}- [[{{ prev }}]]
{% endfor %}
{% endif %}
```

### 3.5 `decision.md.j2`

```jinja
## Context

{{ context }}

## Decision

{{ decision }}

## Alternative Rejected

{{ alternative_rejected }}

## Reason

{{ reason }}

{% if reversible_within_days > 0 %}
## Reversibility

This decision can be reverted within {{ reversible_within_days }} days without significant cost.
{% endif %}
```

### 3.6 `incident.md.j2`

```jinja
## Short Description

{{ short_description }}

## Severity

**{{ severity | upper }}**

## Affected Services

{% for svc in affected_services %}- {{ svc }}
{% endfor %}

## Impact

{{ impact }}

## Timeline

{% for event in timeline %}- {{ event }}
{% endfor %}

{% if root_cause_postmortem %}
## Root Cause

See [[{{ root_cause_postmortem }}]].
{% else %}
## Root Cause

Pending postmortem.
{% endif %}
```

### 3.7 `postmortem.md.j2`

```jinja
## Incident Reference

See [[{{ incident_path }}]].

## Severity

**{{ severity | upper }}**

## Root Cause

{{ root_cause }}

## Contributing Factors

{% for f in contributing_factors %}- {{ f }}
{% endfor %}

## Timeline

{% for event in timeline %}- {{ event }}
{% endfor %}

## What Went Well

{% for w in what_went_well %}- {{ w }}
{% endfor %}

## What Went Wrong

{% for w in what_went_wrong %}- {{ w }}
{% endfor %}

## Action Items

{% for a in action_items %}- [ ] {{ a }}
{% endfor %}
```

### 3.8 `runbook.md.j2`

```jinja
## Description

{{ description }}

## Kind

**{{ runbook_kind }}**

## Applies To

{% for s in applies_to %}- {{ s }}
{% endfor %}

## Prerequisites

{% for p in prerequisites %}- [ ] {{ p }}
{% endfor %}

## Procedure

{% for step in procedure %}
### Step {{ loop.index }}

{{ step }}
{% endfor %}

{% if rollback_procedure %}
## Rollback Procedure

{% for step in rollback_procedure %}
### Rollback Step {{ loop.index }}

{{ step }}
{% endfor %}
{% endif %}

## Verification

{% for v in verification %}- [ ] {{ v }}
{% endfor %}

{% if estimated_duration_minutes %}
## Estimated Duration

{{ estimated_duration_minutes }} minutes
{% endif %}

{% if last_verified_at %}
## Last Verified

{{ last_verified_at }}
{% endif %}
```

### 3.9 `architecture.md.j2`

```jinja
## Summary

{{ summary }}

## Components

{% for c in components %}- {{ c }}
{% endfor %}

{% if diagrams %}
## Diagrams

{% for d in diagrams %}
![{{ d }}]({{ d }})
{% endfor %}
{% endif %}

## Contracts

{% for c in contracts %}- {{ c }}
{% endfor %}

## Rationale

{{ rationale }}

{% if related_adrs %}
## Related ADRs

{% for adr in related_adrs %}- [[{{ adr }}]]
{% endfor %}
{% endif %}
```

### 3.10 `changelog.md.j2`

```jinja
# {{ version }}

{% if release_date %}**Released:** {{ release_date }}{% endif %}

{% if added %}
## Added

{% for a in added %}- {{ a }}
{% endfor %}
{% endif %}

{% if changed %}
## Changed

{% for c in changed %}- {{ c }}
{% endfor %}
{% endif %}

{% if deprecated %}
## Deprecated

{% for d in deprecated %}- {{ d }}
{% endfor %}
{% endif %}

{% if removed %}
## Removed

{% for r in removed %}- {{ r }}
{% endfor %}
{% endif %}

{% if fixed %}
## Fixed

{% for f in fixed %}- {{ f }}
{% endfor %}
{% endif %}

{% if security %}
## Security

{% for s in security %}- {{ s }}
{% endfor %}
{% endif %}
```

### 3.11 `hu.md.j2`

```jinja
## Description

{{ description }}

## Acceptance Criteria

{% for a in acceptance_criteria %}- [ ] {{ a }}
{% endfor %}

## Metadata

- **External ID:** `{{ external_id }}`
- **Source:** {{ source }}
- **Kind:** {{ kind }}
{% if assignee %}- **Assignee:** {{ assignee }}{% endif %}
{% if external_url %}- **External URL:** {{ external_url }}{% endif %}
{% if synced_at %}- **Last sync:** {{ synced_at }}{% endif %}
```

### 3.12 `glossary.md.j2`

```jinja
# {{ term }}

{% if domain %}**Domain:** {{ domain }}{% endif %}

## Definition

{{ definition }}

{% if examples %}
## Examples

{% for ex in examples %}- {{ ex }}
{% endfor %}
{% endif %}

{% if related_terms %}
## Related Terms

{% for r in related_terms %}- [[{{ r }}]]
{% endfor %}
{% endif %}
```

---

## 4. Rendering helper

```python
# cortex/documentation/templates.py
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path

TEMPLATES_DIR = Path(__file__).parent / "templates"

_env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(disabled_extensions=("md.j2",)),
    trim_blocks=True,
    lstrip_blocks=True,
)

def render_template(template_name: str, data: dict) -> str:
    """Render a template with the given data dict.

    Args:
        template_name: ej. "adr.md.j2"
        data: dict of variables to inject.

    Returns:
        Rendered markdown string (body only, no frontmatter).

    Raises:
        TemplateRenderError if template not found or render fails.
    """
    try:
        template = _env.get_template(template_name)
        return template.render(**data)
    except Exception as e:
        raise TemplateRenderError(f"Failed to render {template_name}: {e}") from e
```

---

## 5. Tests por template

Cada template tiene test unitario en `tests/unit/documentation/templates/`:

```python
# tests/unit/documentation/templates/test_adr_template.py
def test_adr_template_minimal():
    """Renders with minimum required fields."""

def test_adr_template_full():
    """Renders with all optional fields populated."""

def test_adr_template_no_supersedes():
    """No 'Supersedes' section when list is empty."""

def test_adr_template_empty_alternatives():
    """Renders empty alternatives without error."""
```

12 templates x 4 tests = 48 tests minimo.

---

## 6. Convencion de placeholders

Variables Jinja2 disponibles en cada template == campos de la dataclass `XData` correspondiente. Es responsabilidad del writer pasar el dict correcto.

Ejemplo para `adr.md.j2`:

```python
template_vars = {
    "title": data.title,
    "context": data.context,
    "decision": data.decision,
    "alternatives_considered": data.alternatives_considered,
    "consequences": data.consequences,
    "supersedes": data.supersedes,
}
body = render_template("adr.md.j2", template_vars)
```

El frontmatter se genera por separado (`build_frontmatter_yaml(data)`) y se prepende al body.

---

## 7. Editabilidad post-deploy

Los templates viven en `cortex/documentation/templates/*.md.j2` como archivos. Para editar:

1. Modificar el template `.md.j2`.
2. Re-deploy (los templates no se cachean al inicio salvo en produccion).
3. Tests deben seguir pasando.

No es necesario tocar Python para ajustar la presentacion de las notas.

---

## 8. Casos especiales por template

### 8.1 `session.md.j2`: cortex_telemetry no esta en el body

`cortex_telemetry` vive en el frontmatter, no en el body. El template no lo renderiza. El writer lo agrega al frontmatter antes de prepender al body.

### 8.2 `glossary.md.j2`: titulo en H1

Para glosario, el titulo (== termino) se renderiza explicitamente en H1 en el body para que la nota sea autosuficiente leida fuera del contexto del frontmatter.

### 8.3 `changelog.md.j2`: titulo es la version

Mismo principio: la version se renderiza en H1 en el body.

### 8.4 Templates condicionales

Los templates con `{% if %}` solo renderizan secciones cuando hay contenido. Esto evita "## Section\n(none)" feo en el output.

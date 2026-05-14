# Fase 12 - Cleanup

**Fuente:** `docs/canonical-documentation/README.md`
**Estado:** Pendiente de ejecucion
**Esfuerzo estimado:** 0.5 dia
**Riesgo:** bajo
**Dependencias:** Fase 11

---

## 1. Objetivo

Cerrar la iniciativa eliminando deuda residual:
1. Eliminar carpetas muertas (que no tienen escritor canonico).
2. Eliminar la version legacy del documenter (`cortex-pi/.pi/agents/cortex-documenter.md`).
3. Remover shims de compatibilidad en `cortex/documentation.py` (DeprecationWarnings).
4. Validar gate global de la iniciativa.
5. Generar reporte final y documento `REALIZACION.md` global.

---

## 2. Archivos a tocar

```text
cortex/setup/
    orchestrator.py             # remove dead folder creation
    templates.py                # update stub creation per DocType

cortex/documentation.py          # ELIMINAR (despues de DeprecationWarning ciclo)

cortex-pi/.pi/agents/
    cortex-documenter.md         # ELIMINAR (legacy)

.cortex/subagents/
    cortex-documenter.md         # update tabla de routing actualizada

vault/
    # eliminar carpetas vacias post-Fase 11

tests/
    # eliminar tests que probaban funciones legacy
    # mantener tests del shim hasta eliminar shim

docs/canonical-documentation/
    REALIZACION.md               # NUEVO: reporte final consolidado
```

---

## 3. Tareas

### 3.1 Eliminar carpetas muertas en setup

```python
# cortex/setup/orchestrator.py - antes:
dirs = [
    layout.episodic_memory_path,
    layout.vault_path / "sessions",
    layout.vault_path / "decisions",
    layout.vault_path / "runbooks",
    layout.vault_path / "incidents",
    layout.vault_path / "hu",
    layout.vault_path / "specs",
]

# Despues: SOLO las que tienen writer Y se usan
dirs = [
    layout.episodic_memory_path,
    layout.vault_path / "sessions",
    layout.vault_path / "handoffs",
    layout.vault_path / "specs",
    layout.vault_path / "decisions",          # adr + decision
    layout.vault_path / "incidents",
    layout.vault_path / "postmortems",
    layout.vault_path / "runbooks",
    layout.vault_path / "architecture",
    layout.vault_path / "changelog",
    layout.vault_path / "hu",
    layout.vault_path / "glossary",
]
```

12 carpetas canonicas. Todas tienen writer.

### 3.2 Seed inicial en lugar de `.gitkeep`

En vez de `.gitkeep`, sembrar un archivo seed valido por cada carpeta:

```python
def _seed_canonical_folders(vault: VaultReader) -> None:
    """Create initial seed notes per canonical folder."""
    # decisions/
    write_adr_note(
        ADRData(
            title="ADR-001: Adopt Cortex Canonical Documentation",
            context="...",
            decision="...",
            consequences="...",
            adr_number=1,
        ),
        vault=vault,
    )
    # glossary/
    write_glossary_entry(
        GlossaryEntryData(term="DocType", definition="...", ...),
        vault=vault,
    )
    # ... etc
```

Esto cierra la promesa: cada carpeta tiene contenido legitimo desde el setup.

### 3.3 Eliminar version legacy del documenter

```bash
# Borrar archivo
$ rm cortex-pi/.pi/agents/cortex-documenter.md

# Actualizar referencias en config
$ grep -r "cortex-documenter" cortex-pi/
# Si hay referencias en agent-chain.yaml, removerlas
```

### 3.4 Actualizar el documenter canonico

```markdown
# .cortex/subagents/cortex-documenter.md - update

## Tabla de Routing (referencia)

Cada documento que escribis debe ir al tipo correcto:

| Cuando quieras documentar... | doc_type | Funcion |
|---|---|---|
| Que se hizo en una sesion de trabajo | session | write_session_note |
| Entrega de trabajo abierto a proxima sesion | handoff | write_handoff_note |
| Especificacion de algo a implementar | spec | write_spec_note |
| Decision arquitectural con Tripartita | adr | write_adr_note |
| Decision no arquitectural pero registrable | decision | write_decision_note |
| Caida o bug critico | incident | write_incident_note |
| Analisis post-incidente | postmortem | write_postmortem_note |
| Procedimiento operativo paso a paso | runbook | write_runbook_note |
| Diseno de un componente o sistema | architecture | write_architecture_note |
| Cambios por release | changelog | write_changelog_note |
| Work item externo (Jira/Linear) | hu | write_hu_note |
| Termino del ubiquitous language | glossary | write_glossary_entry |

Usa la funcion MCP correspondiente. NO crees archivos manualmente.
```

### 3.5 Remover shims de compatibilidad

`cortex/documentation.py` (archivo viejo) - decidir:

**Opcion A:** Eliminar completo. Codigo cliente externo se rompe.
**Opcion B:** Mantener shim 1 release mas. Eliminar en proxima.

Recomendacion: **Opcion B**. Eliminar en proximo major release.

### 3.6 Validar gate global

```bash
# Tests
$ pytest tests/

# Validacion del vault
$ cortex docs validate --all

# Memory report
$ cortex memory-report --since 30d

# Webgraph
$ cortex webgraph stats

# Routing table
$ cortex docs routing-table

# Vectorization
$ cortex docs vectorization stats
```

Resultados esperados (gate global del `README.md` seccion 13):

1. `pytest` pasa al 100%.
2. `cortex docs validate` reporta 0 drift.
3. `cortex memory-report` muestra `cortex_telemetry` poblado >= 5 sessions.
4. Carpetas muertas eliminadas o pobladas.
5. Webgraph muestra nodos coloreados.
6. Setup con `regulated-organization` exige campos.
7. `REALIZACION.md` en cada fase.
8. Legacy documenter eliminado.

### 3.7 Generar `REALIZACION.md` global

```markdown
# Cortex Canonical Documentation - Realizacion

**Fechas:** 2026-05-14 a YYYY-MM-DD
**Esfuerzo:** ~18 dias persona
**PRs:** lista de PRs

## Resumen

[High-level: que se logro, que no, que quedo pendiente]

## Por fase

[Resumen de cada REALIZACION.md de fase]

## Metricas finales

[Tabla de metrics.md con valores reales]

## Decisiones tomadas durante implementacion

[ADRs creados en el proceso]

## Pendientes / Backlog

[Trabajo no incluido pero identificado]
```

---

## 4. Tests

```python
# tests/unit/setup/test_canonical_folders.py

def test_setup_creates_12_canonical_folders():
    """Setup creates exactly the 12 canonical folders."""

def test_setup_no_dead_folders():
    """No folders without writers."""

def test_seed_notes_validate(tmp_vault):
    """Seed notes pass schema validation."""
```

```python
# tests/integration/test_gate_global.py

def test_full_vault_validates(cortex_vault):
    """All notes in Cortex vault validate."""

def test_routing_table_complete(cortex_vault):
    """All DocTypes have writer assigned."""

def test_memory_report_has_telemetry(cortex_vault_after_sessions):
    """Sessions post-Fase 05 have cortex_telemetry."""
```

---

## 5. Checklist

- [ ] Carpetas muertas eliminadas en `orchestrator.py`
- [ ] Setup crea 12 carpetas canonicas con seed notes
- [ ] Version legacy del documenter eliminada
- [ ] Documenter canonico actualizado con tabla de routing
- [ ] Decision sobre shims (Opcion A o B) tomada
- [ ] Gate global ejecutado y verificado
- [ ] `REALIZACION.md` global creado
- [ ] `REALIZACION.md` en cada subcarpeta de fase

---

## 6. Gate de salida

Gate global del README.md seccion 13:

- [ ] `pytest` pasa al 100%
- [ ] `cortex docs validate --all` reporta 0 drift
- [ ] `cortex memory-report` muestra `cortex_telemetry` en >= 5 sessions
- [ ] Carpetas muertas eliminadas
- [ ] Webgraph coloreado por doc_type
- [ ] Setup enterprise exige campos
- [ ] `REALIZACION.md` en cada fase
- [ ] Legacy documenter eliminado

Si TODOS los items pasan, la iniciativa esta cerrada.

---

## 7. Riesgos y mitigaciones

| Riesgo | Mitigacion |
|---|---|
| Eliminar shims rompe consumidores externos | Mantener 1 release mas con DeprecationWarning |
| Seed notes inicial confunde al usuario | Documenter explica que son seed; user puede borrar |
| Algun gate del README no se cumple | NO mergear Fase 12; volver atras a la fase incompleta |
| Documenter actualizacion fragil | Tests del prompt verifican estructura |
| Carpetas canonicas crecen mas alla de 12 | Requiere ADR explicito |
| Tests legacy a eliminar tienen valor | Identificar tests utiles, refactorizar; no borrar a ciegas |
| Reporte global incompleto | Checklist explicito; cada fase reporta su parte |
| Gate global toma tiempo | Aceptar 1 dia adicional para verificar bien |

---

## 8. Notas para agentes implementadores

1. **No saltar el gate global.** Es la prueba real.
2. **Carpetas canonicas == 12.** Ni mas ni menos.
3. **Seed notes son referencias, no placeholder.** Deben ser utiles.
4. **Documenter legacy se elimina con git.** No solo deshabilitar.
5. **`REALIZACION.md` por fase es contractual.** Sin ello, la fase no esta completa.
6. **Shims pueden quedar.** Decision pragmatica.
7. **Reporte global consolida, no resume.** Datos reales.

---

## 9. Referencias

- `docs/canonical-documentation/README.md` seccion 13 - gate global
- `docs/canonical-documentation/metrics.md` - metricas finales
- Cada `docs/canonical-documentation/fase-NN-*/REALIZACION.md` - input para reporte global
- `cortex/setup/orchestrator.py:231-237` - lista de carpetas a modificar

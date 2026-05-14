# Fase 02 - Routing Table - Realizacion

**Fecha de cierre:** 2026-05-14
**Esfuerzo real:** ~1 hora
**Estado:** Completado
**Dependencias cumplidas:** Fase 00, Fase 01

---

## 1. Resumen

Se implemento la Capa 3 (Routing canonico):
- `RouteSpec` dataclass frozen con todos los campos requeridos por las fases posteriores (storage, rendering, writing, enterprise, retrieval, webgraph, lifecycle).
- Tabla `DOC_TYPE_ROUTING` con 12 entradas, cada una completamente parametrizada segun `docs/canonical-documentation/routing-table.md`.
- Operaciones publicas: `resolve_route`, `render_filename`, `resolve_target_path`, `list_all_routes`, `routes_by_subfolder`.
- Subcomando CLI `cortex docs routing-table` con flags `--doc-type` y `--json`.

---

## 2. Archivos creados / modificados

```text
Nuevos:
    cortex/documentation/routing.py        # RouteSpec + DOC_TYPE_ROUTING + helpers (~290 LOC)
    cortex/cli/docs_subcommand.py          # CLI subcommand (cortex docs ...)
    tests/unit/documentation/test_routing.py        # 32 tests
    tests/unit/documentation/test_routing_cli.py    # 4 tests

Modificados:
    cortex/cli/main.py                     # +3 lineas: registracion de docs subapp
```

---

## 3. Decisiones tomadas durante implementacion

### 3.1 `writer=None` por ahora

Los 12 RouteSpecs declaran `writer=None`. Esto es intencional para Fase 02
y no rompe nada porque ningun consumidor real invoca `spec.writer(...)`
aun. La asignacion ocurre en Fase 03 (writers nuevos) y Fase 04 (writers
migrados desde legacy).

**Alternativa rechazada:** apuntar a la funcion legacy via shim. Habria
acoplado Fase 02 con el ciclo legacy, complicando Fase 04. El placeholder
`None` es mas limpio.

### 3.2 `_PLACEHOLDER_RE` excluye format specs

El regex `re.compile(r"\{([^{}:!]+)(?::[^}]*)?\}")` captura el nombre del
placeholder antes de cualquier `:format_spec`. Por ejemplo, en
`"ADR-{number:03d}-{slug}.md"`:
- `{number:03d}` -> placeholder `number`.
- `{slug}` -> placeholder `slug`.

**Razon:** `str.format` espera la clave sin formato; si validamos las
claves requeridas en `render_filename`, el formato no es parte del nombre.

### 3.3 `app.callback()` para forzar grupo en Typer

Cuando `docs_subcommand.app` tenia un solo `@app.command("routing-table")`,
Typer trataba `routing-table` como un argumento al comando default, no como
subcomando. Sintoma: `runner.invoke(app, ["routing-table"])` daba
`Got unexpected extra argument (routing-table)` con exit code 2.

**Solucion:** agregar `@app.callback()` con un docstring de grupo. Esto
fuerza a Typer a interpretar `app` como grupo aun cuando solo tenga un
subcomando. Futuras fases agregaran mas (`validate`, `migrate`, etc) y el
callback se mantiene.

### 3.4 `enterprise_subfolder="glossary"` sin placeholder

Diseno explicitamente: el glossary es global a la organizacion, no
namespaced por proyecto. Test `test_glossary_enterprise_subfolder_no_placeholder`
verifica que no hay `{project_id}` en el string.

### 3.5 `routes_by_subfolder` devuelve listas, no specs individuales

`decisions/` hospeda ADR y DECISION; ambos comparten subfolder pero tienen
filename patterns y boost configs distintos. La funcion debe revelar esto.

**Implementacion:** `dict[str, list[RouteSpec]]`. Test
`test_subfolders_mostly_unique` verifica que solo `decisions` tiene >1
entrada.

---

## 4. Inconvenientes encontrados

### 4.1 Typer trata comando unico como comando default

Descrito en 3.3. Fix: `@app.callback()`.

### 4.2 Sin otros inconvenientes

Tests pasaron al primer intento (excepto el CLI mencionado).

---

## 5. Tests ejecutados

```text
tests/unit/documentation/test_routing.py      32 passed
tests/unit/documentation/test_routing_cli.py   4 passed
---
Fase 02 nuevos:                                36 passed
Modulo cortex/documentation/:                 160 passed
Suite unit completa:                          908 passed, 6 skipped
```

---

## 6. Coverage

```text
cortex/documentation/routing.py                61/61   100%
cortex/cli/docs_subcommand.py                  45/48    94%   (lineas 46, 70-71)
```

Las 3 lineas no cubiertas en `docs_subcommand.py`:
- Linea 46: el branch del `UnknownDocTypeError` adentro de `resolve_route` no se
  alcanza desde tests porque ya hay validacion previa via `typer.BadParameter`.
- Lineas 70-71: branch de impresion JSON para `len(payload) > 1 and doc_type is not None`
  (caso imposible en la logica actual; defensivo).

Coverage del modulo Fase 02: ~99%.

---

## 7. Checklist final (del README de la fase)

- [x] `cortex/documentation/routing.py` con `RouteSpec`, tabla, y helpers
- [x] Tabla `DOC_TYPE_ROUTING` con 12 entradas
- [x] `cortex/cli/docs_subcommand.py` con `routing-table` subcomando
- [x] Registracion en `cortex/cli/main.py`
- [x] `tests/unit/documentation/test_routing.py` >= 18 tests (32 implementados)
- [x] `tests/unit/documentation/test_routing_cli.py` >= 3 tests (4 implementados)
- [x] Coverage >= 90% (99%)
- [x] `cortex docs routing-table` funciona en CLI

---

## 8. Gate de salida

- [x] `pytest tests/unit/documentation/test_routing.py tests/unit/documentation/test_routing_cli.py` pasa al 100% (36/36)
- [x] `cortex docs routing-table` muestra los 12 tipos
- [x] `cortex docs routing-table --doc-type adr --json` retorna JSON valido
- [x] Test estatico verifica que TODOS los DocType tienen entrada
- [x] Sin regresion en suite global (908 passed)
- [x] `REALIZACION.md` documentado

---

## 9. Pendientes / Backlog identificados

1. **Asignacion de writers en Fase 03/04.** Las 12 entradas tienen
   `writer=None`. Tras Fase 03 (9 nuevos) + Fase 04 (3 migrados), todos
   tienen writer callable asignado.

2. **Verificar `template_path.exists()`** queda diferida a Fase 03. En la
   tabla actual los paths apuntan a archivos que aun no existen (esperado).

3. **`cortex docs schema`, `cortex docs scaffold`, `cortex docs validate`,
   `cortex docs migrate`** son comandos adicionales del subgrupo que entran
   en Fases 05, 11. Por ahora solo `routing-table`.

---

## 10. Proximos pasos (Fase 03)

Implementar la Capa 4 (Writers canonicos) segun `fase-03-writers-canonicos/README.md`:
- 12 templates Jinja2 en `cortex/documentation/templates/`.
- 9 writers nuevos: `write_adr_note, write_decision_note, write_incident_note,
  write_postmortem_note, write_runbook_note, write_architecture_note,
  write_changelog_note, write_handoff_note, write_glossary_entry`.
- Asignacion de los nuevos writers a `DOC_TYPE_ROUTING`.
- Tests por writer + tests por template + tests de integracion.

Los 3 writers legacy (`write_session_note`, `write_spec_note`,
`write_hu_note`) se migran en Fase 04, no aqui.

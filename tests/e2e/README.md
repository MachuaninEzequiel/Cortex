# Cortex E2E Tests

Suite de tests end-to-end que ejecutan la CLI de Cortex como un usuario real,
mediante `subprocess`, en directorios temporales aislados.

---

## Cómo correr

### Todos los tests E2E
```bash
pytest tests/e2e/scenarios/ -m e2e -v
```

### Excluir tests E2E (solo unit + integración)
```bash
pytest -m "not e2e"
```

### Tests de artefactos (no requieren cortex instalado)
```bash
pytest tests/e2e/test_artefact_integrity.py -m artefact -v
```

### Escenario específico
```bash
pytest tests/e2e/scenarios/test_setup_basic.py -v
```

---

## Requisitos

- Cortex instalado en modo editable:
  ```bash
  pip install -e ".[dev]"
  ```
- Git instalado (para tests que usan `isolated_git_repo`).

---

## Estructura

```
tests/e2e/
├── conftest.py              # Fixtures neutrales (e2e_project_dir, isolated_git_repo)
├── helpers.py               # run_cortex(), assert_valid_config_yaml(), etc.
├── README.md                # Este archivo
├── test_artefact_integrity.py   # Tests de consistencia de artefactos (FASE 2)
└── scenarios/
    ├── conftest.py          # autouse: verifica cortex instalado (solo escenarios)
    ├── test_setup_basic.py
    ├── test_setup_full.py
    ├── test_enterprise_setup.py
    ├── test_memory_lifecycle.py
    └── test_pr_devsecdocops.py
```

---

## Notas

- Cada test E2E usa un directorio temporal (`tmp_path`) aislado. Nunca escribe
  en el repositorio fuente.
- `CORTEX_ENV=sandbox` se setea automáticamente para evitar que Cortex descubra
  configuraciones del repo padre.

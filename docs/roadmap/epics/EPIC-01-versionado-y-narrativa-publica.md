# EPIC-01 - Versionado y narrativa publica

> Importante: marcar cada tarea completada en este archivo.
> Al cerrar la epica, completar [EPIC-01-versionado-y-narrativa-publica-REALIZACION.md](./EPIC-01-versionado-y-narrativa-publica-REALIZACION.md).

## Objetivo

Eliminar inconsistencias entre version del paquete, narrativa publica, changelog y documentacion visible para que Cortex comunique un solo estado de version y madurez.

## Historia de usuario 1

**Como** maintainer del proyecto  
**Quiero** que la metadata interna del paquete exponga una unica version  
**Para** evitar contradicciones entre instalacion, importacion y packaging.

### Tarea 1.1 - Alinear version y madurez del paquete

**Archivos principales a cambiar**

- `pyproject.toml`
- `cortex/__init__.py`

**Dependencias que deben revisarse o corregirse por arrastre**

- `README.md` - badges y claims de release
- `CHANGELOG.md` - entrada de normalizacion de versionado
- `CONTRIBUTING.md` - cualquier referencia a release o estado del proyecto
- `docs/vision/ARQUITECTURA-GLOBAL-CORTEX.md` - version publica visible
- `docs/enterprise/MANIFIESTO-CORTEX-ENTERPRISE.md` - branding de version enterprise

**Checklist**

- [x] Definir explicitamente la version objetivo que quedara como fuente de verdad.
- [x] Cambiar `project.version` en `pyproject.toml` para reflejar esa version objetivo.
- [x] Revisar el classifier `Development Status` en `pyproject.toml` y ajustarlo al estado real acordado.
- [x] Sincronizar `__version__` en `cortex/__init__.py` con la version final elegida.
- [x] Confirmar que no quede una segunda version distinta expuesta desde el paquete.

### Tarea 1.2 - Corregir encabezado y narrativa publica del README

**Archivo principal a cambiar**

- `README.md`

**Dependencias que deben revisarse o corregirse por arrastre**

- `pyproject.toml` - version y classifier finales
- `CHANGELOG.md` - release vigente y foco actual
- `docs/guides/getting-started.md` - no contradecir install/setup
- `docs/vision/ARQUITECTURA-GLOBAL-CORTEX.md` - claims visibles de version

**Checklist**

- [x] Reemplazar badges estaticos de release por texto o badges que no contradigan la version real.
- [x] Quitar o corregir claims no auditables de cobertura y CI del encabezado.
- [x] Revisar el bloque introductorio para que no prometa un nivel de madurez distinto al acordado.
- [x] Revisar toda mension textual de `v2.0`, `v3.0`, `Enterprise Edition` o frases equivalentes para dejar una sola narrativa.

### Tarea 1.3 - Normalizar changelog y guia de contribucion

**Archivos principales a cambiar**

- `CHANGELOG.md`
- `CONTRIBUTING.md`

**Dependencias que deben revisarse o corregirse por arrastre**

- `README.md`
- `pyproject.toml`
- `docs/vision/PLAN_CORTEX_MAXIMO_IMPACTO.md`

**Checklist**

- [x] Registrar en `CHANGELOG.md` la normalizacion de versionado y de narrativa publica.
- [x] Revisar que el `Unreleased` no contradiga la situacion real del repo.
- [x] Revisar `CONTRIBUTING.md` para eliminar o corregir afirmaciones de roadmap ya no vigentes.
- [x] Verificar que la arquitectura descripta en `CONTRIBUTING.md` no vuelva a introducir claims falsos de estado o version.

## Validacion de la epica

- [x] Ejecutar `pytest -q` y confirmar que esta epica no introdujo nuevas fallas.
- [x] Revisar visualmente `README.md`, `pyproject.toml` y `cortex/__init__.py` para confirmar una sola version publica.
- [x] Completar el archivo de realizacion de la epica.

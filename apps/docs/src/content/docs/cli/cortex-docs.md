---
title: cortex docs
description: Búsqueda estructural avanzada con ContextEnricher, validación de schemas y migración de vaults.
---

El comando `cortex docs` provee herramientas avanzadas de **búsqueda estructurada, validación y mantenimiento del Vault**.

---

## Subcomandos

```text
Usage: cortex docs <COMMAND>

Commands:
  search    Búsqueda avanzada con filtros estructurales en el Vault
  validate  Valida la conformidad de todos los Markdown contra el schema Zod
  migrate   Ejecuta migraciones de esquema en notas del Vault
  backup    Crea o restaura copias de seguridad del Vault
```

---

## `cortex docs search`

Ejecuta búsquedas en el Vault aplicando filtros tipados sobre el frontmatter mediante el [`ContextEnricher`](file:///home/chucho/Cortex/rust/crates/cortex-app/src/context/mod.rs).

```bash
cortex docs search <QUERY> [OPCIONES]
```

### Opciones de Búsqueda:
* `-k, --top-k <N>`: Cantidad de notas a retornar (por defecto: `5`).
* `--doc-type <SLUG>`: Filtra por tipo de documento (ej: `adr`, `spec`, `runbook`, `design`). Repetible.
* `--exclude-doc-type <SLUG>`: Excluye ciertos tipos de documento de los resultados.
* `--status <STATUS>`: Filtra por estado (`draft`, `accepted`, `deprecated`, `stable`).
* `--tag <TAG>`: Requiere que la nota contenga todos los tags especificados.
* `--tag-any <TAG>`: Requiere que la nota contenga al menos uno de los tags.
* `--scope <local|enterprise|all>`: Limita la búsqueda al vault local o al compartido.
* `--max-age-days <N>`: Filtra notas con fecha de modificación inferior a N días.
* `--strict`: Modo estricto que descarta notas que no cumplan al 100% con los filtros.
* `-f, --format <text|json|compact>`: Formato de salida.

### Ejemplo:
```bash
cortex docs search "estrategia de migración de base de datos" \
  --doc-type adr \
  --doc-type design \
  --status accepted \
  --format text
```

---

## `cortex docs validate`

Verifica que todos los archivos Markdown dentro de `.cortex/vault/` cumplan con los campos obligatorios correspondientes a su `doc_type` y que los enlaces internos (`links`) no estén rotos:

```bash
cortex docs validate
```

---

## `cortex docs migrate`

Permite actualizar notas antiguas a nuevos esquemas de frontmatter o migrar ubicaciones de archivos sin perder el historial ni los identificadores de grafo:

```bash
cortex docs migrate --dry-run
cortex docs migrate --apply
```

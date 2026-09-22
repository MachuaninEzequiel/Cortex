# apps/docs/astro.config.mjs

## Qué tiene adentro

`defineConfig` de Astro con integración Starlight. Campos: `site`, `title`, `description`, `defaultLocale`/`locales` (root=es, en), `social.github`, `customCss` vacío, `sidebar` (arrays de `{label, items: [{label, slug}]}`).

## Para qué sirve

Configura el sitio de docs: URL canónica, i18n y navegación.

## Relaciones

### Recibe de
`@astrojs/starlight`. Los slugs apuntan a archivos bajo `src/content/docs/`.

### Envía a
Astro en `dev`/`build`. El HTML generado vive en `dist/`.

### Notas de implementación observadas en el código
La descripción del sitio afirma «Core Rust 100% nativo». El CLI nativo (`cortex-cli/src/main.rs`) confirma dispatch sin passthrough a Python; el paquete Python `cortex-memory` 0.7.0 sigue existiendo en `pyproject.toml` como superficie histórica/oráculo.

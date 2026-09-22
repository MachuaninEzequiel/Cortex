# apps/docs/package.json

## Qué tiene adentro

Nombre `cortex-docs`, version `0.1.0`, `private`, `type: module`. Scripts: `dev`/`start` → `astro dev`, `build`, `preview`, `astro`, `check` → `astro check`. Deps: `@astrojs/check`, `@astrojs/starlight` ^0.32.6, `astro` ^5.18.2, `sharp`, `typescript`.

## Para qué sirve

Manifiesto npm del sitio de documentación.

## Relaciones

### Recibe de
Registro npm. Lockfiles: `pnpm-lock.yaml`, `pnpm-workspace.yaml`.

### Envía a
Scripts invocados por el operador. No se relaciona en runtime con `cortex-cli` ni con `brain-ui`.

# apps/docs/src/content/config.ts

## Qué tiene adentro

```
export const collections = {
  docs: defineCollection({ schema: docsSchema() }),
};
```

Usa `defineCollection` de `astro:content` y `docsSchema` de `@astrojs/starlight/schema`.

## Para qué sirve

Declara la content collection `docs` que Starlight espera. Valida frontmatter de los markdown del sitio.

## Relaciones

### Recibe de
Archivos bajo `src/content/docs/`.

### Envía a
Astro content layer → páginas del sidebar.

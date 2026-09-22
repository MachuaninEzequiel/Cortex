# apps/ — estructura interna (código)

Dos aplicaciones frontend. No hay un workspace npm único en la raíz de `apps/`; cada una tiene su propio `package.json`.

```
apps/
  brain-ui/     UI React+Vite+Tailwind del Cortex Brain (Tauri)
  docs/         Sitio de documentación Astro Starlight
```

## brain-ui

Paquete `brain-ui` 0.1.0, private, type module.

Scripts: `dev` (vite), `build` (`tsc -b && vite build`), `preview`, `typecheck`.

Dependencias runtime: `react` 18.3, `react-dom` 18.3. Dev: `@tauri-apps/api` 2, Vite 5, Tailwind 3, TypeScript 5.

Árbol de fuente (sin `node_modules/` ni `dist/`):

```
apps/brain-ui/
  package.json
  package-lock.json
  vite.config.ts
  tailwind.config.js
  postcss.config.js
  tsconfig.json
  index.html
  src/
    main.tsx
    App.tsx          (si existe en el lote documentado)
    index.css
    i18n.ts
    types.ts
    vite-env.d.ts
    hooks/useTauri.ts
    components/
      Chat.tsx
      DoctorModal.tsx
      GovernanceBar.tsx
      MarkRam.tsx
      OrgMemoryModal.tsx
      SettingsModal.tsx
      Sidebar.tsx
      StatusBar.tsx
      ToolApprovalModal.tsx
      TopBar.tsx
      WebGraphModal.tsx
```

Puente con el backend: `useTauri.ts` llama `invoke` / `listen` de `@tauri-apps/api`. Sin runtime Tauri, `tauriInvoke` lanza error (no hay backend web). El backend vive en `rust/crates/cortex-brain-app` (comandos Tauri, IPC, chat, graph, org_memory, projects).

Fichas: `ConaISI/apps/brain-ui/` y `ConaISI/apps/_brain-ui-indice.md`.

## docs

Paquete `cortex-docs` 0.1.0, private. Astro 5 + `@astrojs/starlight` 0.32 + sharp + typescript.

Scripts: `astro dev/build/preview/check`.

`astro.config.mjs` fija `site: https://docs.cortex.dev`, título `Cortex Docs`, descripción «Sistema de memoria cognitiva híbrida para agentes de IA (Core Rust 100% nativo)», locales root=es y en, GitHub `MachuaninEzequiel/Cortex`, sidebar con secciones Comenzando, Arquitectura, CLI Rust, MCP (32 tools), IDE, Enterprise, CortexBrain.

`src/content/config.ts` registra la collection `docs` con `docsSchema()` de Starlight.

Los `.md`/`.mdx` bajo `src/content/docs/` son contenido del sitio. En este inventario **no se usaron como fuente de verdad de arquitectura** (pedido explícito: no leer documentación previa). Se listan en `apps/docs/00-estructura.md` como archivos del paquete.

`dist/` y `.astro/` son build cache; no se documentan como fuente.

Fichas de config: `ConaISI/apps/docs/`.

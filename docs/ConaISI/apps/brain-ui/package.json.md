# apps/brain-ui/package.json

## Qué tiene adentro

Package privado `brain-ui` 0.1.0, `"type": "module"`. Scripts: `dev` vite, `build` `tsc -b && vite build`, `preview`, `typecheck`.

Dependencies: `react`/`react-dom` ^18.3. Dev: `@tauri-apps/api` ^2, vite 5, tailwind 3, typescript 5, autoprefixer, postcss, types React.

## Para qué sirve

Instalación npm del frontend desktop.

## Relaciones

### Recibe de

- npm registry

### Envía a

- `vite`/`tsc` → `dist/`; Tauri `beforeBuildCommand` corre `npm --prefix ... run build`

### Notas de implementación observadas en el código

`@tauri-apps/api` está en devDependencies (la UI se embebe, no se publica).

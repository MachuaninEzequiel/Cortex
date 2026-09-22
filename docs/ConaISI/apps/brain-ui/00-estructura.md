# apps/brain-ui — estructura interna

Frontend React 18 + Vite + Tailwind de la app Tauri Cortex Brain. Dist consumido por `rust/crates/cortex-brain-app/tauri.conf.json`.

```
apps/brain-ui/
├── package.json / package-lock.json
├── vite.config.ts          # puerto 1420 strict, env VITE_/TAURI_
├── tsconfig.json / tsconfig.tsbuildinfo (artefacto tsc)
├── tailwind.config.js / postcss.config.js
├── index.html
├── .gitignore
└── src/
    ├── main.tsx            # logs → log_to_terminal, ErrorBoundary
    ├── App.tsx             # estado global, invoke/listen
    ├── types.ts            # espejo de payloads Rust
    ├── i18n.ts
    ├── index.css
    ├── vite-env.d.ts
    ├── hooks/useTauri.ts
    └── components/
        ├── Chat.tsx / ChatInput.tsx / ChatMessage.tsx
        ├── Sidebar.tsx / TopBar.tsx / StatusBar.tsx / GovernanceBar.tsx
        ├── SettingsModal.tsx / ToolApprovalModal.tsx
        ├── WebGraphModal.tsx / DoctorModal.tsx / OrgMemoryModal.tsx
        └── MarkRam.tsx
```

No se documenta `node_modules/` ni `dist/`.

## Relaciones

- **Recibe de:** commands/eventos Tauri definidos en `cortex-brain-app/src/lib.rs`.
- **Envía a:** `invoke` / `listen` vía `@tauri-apps/api`; logs a `log_to_terminal`.

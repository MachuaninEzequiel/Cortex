# Índice apps/brain-ui

Frontend React/Vite/Tailwind de Cortex Brain. Código en `apps/brain-ui/`; backend Tauri en `rust/crates/cortex-brain-app/`.

No se documentan `node_modules/`, `dist/` ni `tsconfig.tsbuildinfo` (artefacto tsc).


## Documentos (29)

- `apps/brain-ui/.gitignore.md`
- `apps/brain-ui/00-estructura.md`
- `apps/brain-ui/index.html.md`
- `apps/brain-ui/package-lock.json.md`
- `apps/brain-ui/package.json.md`
- `apps/brain-ui/postcss.config.js.md`
- `apps/brain-ui/src/App.tsx.md`
- `apps/brain-ui/src/components/Chat.tsx.md`
- `apps/brain-ui/src/components/ChatInput.tsx.md`
- `apps/brain-ui/src/components/ChatMessage.tsx.md`
- `apps/brain-ui/src/components/DoctorModal.tsx.md`
- `apps/brain-ui/src/components/GovernanceBar.tsx.md`
- `apps/brain-ui/src/components/MarkRam.tsx.md`
- `apps/brain-ui/src/components/OrgMemoryModal.tsx.md`
- `apps/brain-ui/src/components/SettingsModal.tsx.md`
- `apps/brain-ui/src/components/Sidebar.tsx.md`
- `apps/brain-ui/src/components/StatusBar.tsx.md`
- `apps/brain-ui/src/components/ToolApprovalModal.tsx.md`
- `apps/brain-ui/src/components/TopBar.tsx.md`
- `apps/brain-ui/src/components/WebGraphModal.tsx.md`
- `apps/brain-ui/src/hooks/useTauri.ts.md`
- `apps/brain-ui/src/i18n.ts.md`
- `apps/brain-ui/src/index.css.md`
- `apps/brain-ui/src/main.tsx.md`
- `apps/brain-ui/src/types.ts.md`
- `apps/brain-ui/src/vite-env.d.ts.md`
- `apps/brain-ui/tailwind.config.js.md`
- `apps/brain-ui/tsconfig.json.md`
- `apps/brain-ui/vite.config.ts.md`

## Flujo UI → Rust (commands/eventos observados en App.tsx + lib.rs)


| UI | Rust |
|---|---|
| list_projects / refresh_projects | projects.rs |
| chat_turn_stream + evento chat-chunk | chat.rs BrainEngine |
| list_models / download_model + download-progress / set_active_model | chat.rs + download de cortex-brain |
| reap_idle / loaded_projects | BrainEngine idle 90s |
| load/save/clear_chat_history | `.cortex/brain/history.jsonl` |
| get_project_graph / get_session_status / run_doctor_inspect | graph.rs |
| get_org_memory / approve_org_candidate / reject_org_candidate | org_memory.rs |
| execute_cortex_tool | lib.rs → CLI cortex-rs/cortex |
| open_webgraph_browser | spawn `cortex webgraph serve` + xdg-open :8765 |
| toggle/hide/show_window, set_always_on_top | ventana Tauri |
| log_to_terminal | stderr |
| atajo Ctrl+Shift+B | tauri-plugin-global-shortcut |

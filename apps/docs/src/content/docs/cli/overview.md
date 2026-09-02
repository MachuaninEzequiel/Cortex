---
title: Referencia General de la CLI
description: Resumen completo de comandos de cortex-cli, arquitectura de despacho en Rust y modos de ejecución.
---

El ejecutable `cortex-cli` (accesible también mediante el alias `cortex`) es el punto de entrada unificado para interactuar con Cortex desde la terminal.

---

## Arquitectura de Despacho de Comandos

En [`cortex-cli/src/main.rs`](file:///home/chucho/Cortex/rust/crates/cortex-cli/src/main.rs), el despacho de comandos sigue un flujo 100% nativo en Rust con Clap:

1. **Invocación sin argumentos (`cortex`):** Lanza de forma automática la interfaz gráfica de terminal interactiva ([TUI en Ratatui](/es/cli/cortex-tui/)) o un snapshot en entornos no interactivos.
2. **Flags globales (`--version`, `--help`):** Muestran la versión del binario o la ayuda formateada.
3. **Subcomandos nativos:** Despacha el control directamente al crate especializado correspondiente.
4. **Comandos desconocidos:** Retorna un error tipado con código de salida `rc=2`.

---

## Tabla Resumen de Comandos

| Comando | Descripción Breve | Crate Responsable |
| :--- | :--- | :--- |
| **`cortex`** | Abre el Dashboard interactivo TUI (Ratatui). | `cortex-tui` |
| **[`cortex doctor`](/es/cli/cortex-doctor/)** | Valida prerrequisitos y salud del entorno. | `cortex-doctor` |
| **[`cortex init`](/es/cli/cortex-setup/)** | Inicializa la estructura `.cortex/` en el proyecto. | `cortex-setup` |
| **[`cortex setup`](/es/cli/cortex-setup/)** | Asistente de configuración guiada y perfiles. | `cortex-setup` |
| **[`cortex session`](/es/cli/cortex-session/)** | Gestión de sesiones de trabajo, checkpoints y tareas. | `cortex-app` |
| **[`cortex search`](/es/cli/cortex-search/)** | Búsqueda cognitiva híbrida en memoria y vault. | `cortex-core` / `cortex-app` |
| **[`cortex context`](/es/cli/cortex-search/)** | Recupera contexto formateado para prompts de IA. | `cortex-app` |
| **[`cortex stats`](/es/cli/cortex-search/)** | Métricas de tamaño, notas e índices de memoria. | `cortex-core` |
| **[`cortex remember`](/es/cli/cortex-remember/)** | Almacena un evento rápido en memoria episódica. | `cortex-app` |
| **[`cortex forget`](/es/cli/cortex-remember/)** | Invalida o elimina un registro episódico. | `cortex-app` |
| **[`cortex hu`](/es/cli/cortex-hu/)** | Importa y sincroniza historias de usuario / Jira. | `cortex-app` |
| **[`cortex next`](/es/cli/cortex-next/)** | Sugiere la siguiente mejor acción (ActionEngine). | `cortex-actions` |
| **[`cortex webgraph`](/es/cli/cortex-webgraph/)** | Exporta y sirve el grafo semántico (Axum). | `cortex-webgraph-server` |
| **[`cortex autopilot`](/es/cli/cortex-autopilot/)** | Capa de ejecución y decisión autónoma. | `cortex-autopilot` |
| **[`cortex ide`](/es/cli/cortex-ide/)** | Inyecta configuración y MCP en editores e IDEs. | `cortex-setup` |
| **[`cortex tutor`](/es/cli/cortex-tutor/)** | Guía interactiva offline de conceptos de Cortex. | `cortex-tutor` |
| **[`cortex hint`](/es/cli/cortex-tutor/)** | Sugerencia contextual en una línea (Zero-tokens). | `cortex-tutor` |
| **[`cortex ci`](/es/cli/cortex-ci-pr/)** | Validación de PRs y reclamos de sesión en CI/CD. | `cortex-app` |
| **[`cortex pr-context`](/es/cli/cortex-ci-pr/)** | Genera contexto enriquecido para Pull Requests. | `cortex-app` |
| **[`cortex docs`](/es/cli/cortex-docs/)** | Búsqueda, validación y migración de notas. | `cortex-services` |
| **[`cortex mcp-server`](/es/mcp/overview/)** | Inicia el servidor nativo Model Context Protocol. | `cortex-mcp` |
| **[`cortex finish`](/es/cli/cortex-session/)** | Cierra la sesión activa consolidando evidencia. | `cortex-app` |

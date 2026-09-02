import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

// https://astro.build/config
export default defineConfig({
	site: 'https://docs.cortex.dev',
	integrations: [
		starlight({
			title: 'Cortex Docs',
			description: 'Sistema de memoria cognitiva híbrida para agentes de IA (Core Rust 100% nativo)',
			defaultLocale: 'root',
			locales: {
				root: {
					label: 'Español',
					lang: 'es',
				},
				en: {
					label: 'English',
					lang: 'en',
				},
			},
			social: {
				github: 'https://github.com/MachuaninEzequiel/Cortex',
			},
			customCss: [
				// Custom styles can be added here
			],
			sidebar: [
				{
					label: 'Comenzando',
					items: [
						{ label: 'Bienvenido a Cortex', slug: 'getting-started/welcome' },
						{ label: 'Inicio Rápido (5 min)', slug: 'getting-started/quickstart' },
						{ label: 'Instalación y Requisitos', slug: 'getting-started/installation' },
						{ label: 'Diagnóstico con Doctor', slug: 'getting-started/doctor' },
					],
				},
				{
					label: 'Arquitectura y Conceptos',
					items: [
						{ label: 'Visión General', slug: 'concepts/overview' },
						{ label: 'Memoria Tripartita', slug: 'concepts/tripartite-memory' },
						{ label: 'Búsqueda Híbrida y RRF', slug: 'concepts/hybrid-search-rrf' },
						{ label: 'Embeddings Locales ONNX', slug: 'concepts/onnx-embeddings' },
						{ label: 'Estructura del Vault y Documentos', slug: 'concepts/vault-structure' },
						{ label: 'Workspace Layout y Configuración', slug: 'concepts/workspace-layout' },
					],
				},
				{
					label: 'Referencia CLI (Rust Nativo)',
					items: [
						{ label: 'Resumen de Comandos', slug: 'cli/overview' },
						{ label: 'cortex (TUI Dashboard)', slug: 'cli/cortex-tui' },
						{ label: 'cortex doctor', slug: 'cli/cortex-doctor' },
						{ label: 'cortex init & setup', slug: 'cli/cortex-setup' },
						{ label: 'cortex session', slug: 'cli/cortex-session' },
						{ label: 'cortex search & context', slug: 'cli/cortex-search' },
						{ label: 'cortex remember & forget', slug: 'cli/cortex-remember' },
						{ label: 'cortex hu (Historias y Tareas)', slug: 'cli/cortex-hu' },
						{ label: 'cortex next (ActionEngine)', slug: 'cli/cortex-next' },
						{ label: 'cortex webgraph', slug: 'cli/cortex-webgraph' },
						{ label: 'cortex autopilot', slug: 'cli/cortex-autopilot' },
						{ label: 'cortex ide', slug: 'cli/cortex-ide' },
						{ label: 'cortex tutor & hint', slug: 'cli/cortex-tutor' },
						{ label: 'cortex ci & pr-context', slug: 'cli/cortex-ci-pr' },
						{ label: 'cortex docs', slug: 'cli/cortex-docs' },
					],
				},
				{
					label: 'Protocolo MCP (32 Tools)',
					items: [
						{ label: 'Visión General de MCP', slug: 'mcp/overview' },
						{ label: 'Health & Ping', slug: 'mcp/ping-health' },
						{ label: 'Búsqueda y Contexto', slug: 'mcp/search-context' },
						{ label: 'Ciclo de Sesiones', slug: 'mcp/session-tools' },
						{ label: 'Documentos, Specs y Diseños', slug: 'mcp/docs-specs' },
						{ label: 'Autopilot MCP', slug: 'mcp/autopilot-tools' },
						{ label: 'Integración Tickets y Vault', slug: 'mcp/tickets-vault' },
					],
				},
				{
					label: 'Enterprise y Gobernanza',
					items: [
						{ label: 'Gobernanza y org.yaml', slug: 'enterprise/governance' },
						{ label: 'Revisión y Promoción de Conocimiento', slug: 'enterprise/review-promotion' },
						{ label: 'Reportes de Memoria', slug: 'enterprise/memory-report' },
					],
				},
				{
					label: 'Integraciones IDE',
					items: [
						{ label: 'Claude Code y Claude Desktop', slug: 'ide/claude' },
						{ label: 'Cursor y Windsurf', slug: 'ide/cursor' },
						{ label: 'Pi IDE y OpenCode', slug: 'ide/pi-opencode' },
						{ label: 'OpenAI Codex y Antigravity', slug: 'ide/codex-antigravity' },
					],
				},
				{
					label: 'CortexBrain (App de Escritorio)',
					items: [
						{ label: 'CortexBrain Tauri v2', slug: 'cortexbrain/overview' },
						{ label: 'Visualizador WebGraph', slug: 'cortexbrain/webgraph' },
					],
				},
			],
		}),
	],
});

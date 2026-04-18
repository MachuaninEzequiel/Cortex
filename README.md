<div align="center">
  <br />
    <a href="https://github.com/MachuaninEzequiel/Cortex" target="_blank">
      <img src="assets/logo.png" alt="Cortex Logo" width="500">
    </a>
  <br />

  <h1>CORTEX v2.0</h1>

  <p>
    <strong>Calidad, Seguridad y Documentación como sistema de gobernanza para Organizaciones y DevAgents</strong>
  </p>

  <p>
    <a href="https://github.com/MachuaninEzequiel/Cortex"><img src="https://img.shields.io/badge/Release-2.0.0--Core-blueviolet.svg" alt="Release 2.0.0" /></a>
    <a href="https://github.com/MachuaninEzequiel/Cortex"><img src="https://img.shields.io/badge/Architecture-Hybrid--Memory-orange.svg" alt="Architecture" /></a>
    <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT" /></a>
  </p>

</div>

---

##  El Manifiesto Cortex: Gobernanza Total

En la era de los agentes de IA, la **Amnesia de Sesión** es el mayor enemigo de la productividad. Los agentes convencionales inician cada tarea en blanco, ignorando las decisiones arquitectónicas pasadas, las vulnerabilidades detectadas y el contexto histórico de tu negocio.

**Cortex redefine la relación humano-agente.** No es solo una base de conocimientos; es un **Sistema de Gobernanza** que obliga a la IA a seguir un ciclo de vida disciplinado de ingeniería de software, garantizando que el "saber hacer" nunca se pierda y que cada commit esté respaldado por documentación técnica de alta fidelidad.

---

##  El Modelo de Ejecución Tripartito (SDDwork)

La Release 2.0 introduce **Cortex-SDDwork**, un sistema de orquestación donde la responsabilidad se divide en tres roles especializados para maximizar la precisión:

### 1. `Cortex-sync` (El Analista / SPECsWriter)
Su misión es la **preparación**. Recupera contexto histórico del Vault y de la memoria episódica para refinar los requisitos.
- **Output**: Generación de una **Especificación Técnica (`create-spec`)** validada antes de tocar una sola línea de código.

### 2. `Cortex-SDDwork` (El Orquestador)
Coordina la implementación técnica mediante subagentes especializados:
- **CodeSubAgent**: Encargado de la lógica funcional.
- **SecuritySubAgent**: Revisa vulnerabilidades y cumplimiento de estándares en tiempo real.
- **TestSubAgent**: Asegura la cobertura y estabilidad del cambio.

### 3. `Sug-agent cortex-documenter` (El Guardián)
Es el paso final obligatorio. Ninguna tarea se considera terminada si este agente no ha persistido el conocimiento en el Vault. Es un subagente llamado por el orquestador de forma obligatoria al final de la realizacion completa de un SPEC, posee reglas definidas y SKILLS optimizadas para la generacion de documentacion tecnica de alta fidelidad, con los estandares estrictos de Obsidian.
- **Output**: **Notas de Sesión (`save-session`)** estructuradas que alimentan la memoria futura de todo el equipo.

---

##  Pilares Tecnológicos

###  Memoria Híbrida RRF (Reciprocal Rank Fusion)
Cortex combina dos capas cognitivas para una recuperación perfecta:
- **Capa Episódica**: Eventos de CI, logs y resúmenes de PRs almacenados en **ChromaDB**.
- **Capa Semántica**: El conocimiento profundo de la empresa almacenado como archivos **Markdown** en tu Vault.
- El motor realiza búsquedas cruzadas y fusiona resultados para dar al agente el contexto exacto.

###  Aislamiento y Anti-Amnesia
Cortex prohíbe explícitamente el uso de memorias genéricas o volátiles. En un repositorio gobernado por Cortex, la **única fuente de verdad** es el sistema local sincronizado, eliminando alucinaciones y fugas de contexto.

###  Eficiencia ONNX
Sin dependencias pesadas. Cortex utiliza un backend basado en **ONNX Runtime** para embeddings, permitiendo inicializaciones en `< 1ms` incluso en hardware modesto.

---

##  CLI Reference (v2.0)

Todas las funciones están gobernadas por el envoltorio CLI de Typer:

| Comando | Función en el Ciclo de Vida |
|---------|-----------------------------|
| `cortex setup agent` | **Cognitive**: Configura Vault, Memoria, Skills y el Servidor MCP en tu IDE. |
| `cortex setup pipeline` | **DevOps**: Configura Workflows de GitHub y scripts de auditoría (`devsecdocops.sh`). |
| `cortex setup full` | **Total**: Instalación completa (Agente + Pipeline). |
| `cortex create-spec` | **Pre-Work**: Define metas, requerimientos y criterios de aceptación. |
| `cortex save-session` | **Post-Work**: Persiste cambios, decisiones y TODOs en el Vault. |
| `cortex search` | **Retrieve**: Búsqueda híbrida en ambas capas de memoria. |
| `cortex context` | **Enrich**: Inyecta contexto temprano basado en archivos modificados. |
| `cortex install-skills`| **Coach**: Inyecta habilidades de Obsidian en `.cortex/skills/`. |
| `cortex mcp-server` | **Bridge**: Inicia el servidor universal para integración con IDEs. |

---

##  Integración Universal (MCP Server)

Cortex expone sus capacidades nativamente mediante el **Model Context Protocol (MCP)**. Configúralo en tu IDE favorito para que tus asistentes tengan "superpoderes" cognitivos:

- **Antigravity / Claude Desktop**: Configura el comando `python -m cortex.mcp_server`.
- **VSCode (Cline / Roo)**: Agrega Cortex a tus `mcp_settings.json`.
- **Cursor**: Registra un nuevo MCP Server apuntando a `python -m cortex.mcp_server`.

---

##  Instalación

Clona el repositorio e instala en modo desarrollo (Early Access):

```bash
git clone https://github.com/MachuaninEzequiel/Cortex.git
cd Cortex
pip install -e .

# Para desarrolladores (Setup Cognitivo + IDE):
cortex setup agent

# Para DevOps (Setup de CI/CD):
cortex setup pipeline

# Para Startups sin CI/CD, a punto de iniciar un proyecto:
cortex setup full
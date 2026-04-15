<div align="center">
  <br />
    <a href="https://github.com/MachuaninEzequiel/cortex-devsecdocops-test" target="_blank">
      <img src="assets/logo.png" alt="Cortex Logo" width="200">
    </a>
  <br />

  <h1>CORTEX</h1>

  <p>
    <strong>Memoria Institucional Híbrida para Agentes de IA en Flujos DevSecDocOps</strong>
  </p>

  <p>
    <a href="https://pypi.org/project/cortex-memory/"><img src="https://img.shields.io/pypi/v/cortex-memory.svg" alt="PyPI version" /></a>
    <a href="https://pypi.org/project/cortex-memory/"><img src="https://img.shields.io/pypi/pyversions/cortex-memory.svg" alt="Python" /></a>
    <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT" /></a>
  </p>

</div>

---

## Visión General: El Paradigma Agent-First

La mayoría de los agentes de Inteligencia Artificial (Copilot, Cursor, Claude Code) sufren de **Amnesia de Sesión**. Inician en blanco. No conocen tus *Architecture Decision Records (ADRs)*, ni recuerdan el bug que fixearon la semana pasada.

**Cortex soluciona esto.** No es un simple RAG, es un motor DevSecDocOps que captura el contexto de tu trabajo local, lo enriquece matemáticamente, exige que tus agentes escriban documentación continua, y lo valida todo algorítmicamente en tu pipeline de Integración Continua (CI/CD).

### Documentación Completa Oficial
> 👉 Lee el manual arquitectónico exhaustivo en **[Cortex Documentation Portal](http://localhost:5173/)**.

---

## Arquitectura Core v2.0

### 1. El Motor Proactivo (Context Enricher)
Cortex observa tus archivos modificados y ejecuta 6 estrategias de búsqueda concurrentes (Topic, File, Keyword, Entity, etc.) para inyectar contexto a tu agente **antes de que pregunte**. Todo el sistema es balanceado por:
- **Typed Co-occurrence Graph:** Entiende dependencias a nivel de código fuente (`imported_by` > `references`).
- **Memory Decay:** Decaimiento temporal exponencial de la memoria antigua (half-life de 168 horas), protegiendo eternamente registros de arquitectura vitales.
- **Domain Detector:** Matelización estricta por regex hacia 12 dominios críticos con fallback hacia distancia Euclidiana vía *Embeddings*.

### 2. Zero-Dependency y Backend ONNX
Desarrollado para entornos empresariales, Cortex transicionó de la dependencia pesada de PyTorch hacia **ONNX Runtime embebido** (`all-MiniLM-L6-v2`).
- Inicialización en CPU en **< 1 ms**.
- Latencia cero en CI/CD. Cero GPUs necesarias.

### 3. Memoria Híbrida (Episódica + Semántica)
Cortex emula la mente humana usando algoritmos de *Reciprocal Rank Fusion* (RRF):
- **Episódica**: Eventos de CI, logs y resúmenes de PRs indexados automáticamente en base de datos vectorial local (ChromaDB).
- **Semántica**: El "saber hacer" de la empresa escrito por agentes de IA directamente a un _Obsidian Markdown Vault_.

### 4. Eficiencia de Tokens Extrema (Estrategia Dual-Profile)
Instala de manera automática (en OpenCode / VSCode) nuestra estrategia dividida:
- **`Cortex-Sync`**: Perfil inicial (carga alta: ~450 tokens) que lee, entiende el vault y coordina integraciones de GitHub.
- **`Cortex-Work`**: Perfil productivo (ultra-ligero: ~60 tokens). Tras estar "cebado", ahorrá hasta un **90%** en tus cuotas mensuales mediante purga sistemática de gobernanza.

---

## Instalación y Setup en 1 Minuto

Instalar a través de Pip en tu entorno de desarrollo Python (>= 3.10):

```bash
pip install cortex-memory
```

Luego, inicializá el orquestador automático en la raíz de tu proyecto:

```bash
cortex setup
```
Este sub-comando es "mágia oscura": Detecta tu lenguaje, tu framework, tu orquestador de CI, inicializa el almacén de ChromaDB en `.memory/`, escupe el Vault Markdown inicial, y acopla los workflows `.yml` de Github Actions todo a la vez.

---

## El Pipeline DevSecDocOps
Una vez inicializado, ¿qué sucede en tu rutina diaria?

1. El developer programa co-piloteado por su Agente IA favorito.
2. Al final, **el agente escribe la documentación de la sesión en el Vault `(cortex/vault)`**.
3. El developer hace un PR a GitHub.
4. Las pruebas de Lint, SAST y Security se corren en CI. Sus fallos son absorbidos como recuerdos de fallos para Cortex.
5. Cortex **verifica** el PR. Si halla la documentación del agente, la indexa a la base vectorial semántica. Si no la halla, genera actas de fallback muy primitivas evidenciando al equipo que no se ha cumplido el estándar.

---

## CLI (Command Line Interface)

Todas las funciones están gobernadas por el envoltorio CLI de Typer:

| Comando | Descripción de Acción |
|---------|-----------------------|
| `cortex install-ide` | Interviene los config locales del IDE instalando los perfiles `Sync` y `Work`. |
| `cortex search "query"`| Ejecuta la Búsqueda Híbrida RRF y devuelve scores cruzados. |
| `cortex sync-vault` | Fuerza validación por Pydantic indexando todos los archivos Markdown nuevamente. |
| `cortex context` | Fuerza detección temprana inyectado el grafo tipado (staged/unstaged files). |
| `cortex pr-context *` | Set maestro ejecutado dentro del CI/CD de GitHub. |

---

## Cómo Contribuir

Cortex es desarrollado para revolucionar el paradigma de documentación del software. Por favor, lee nuestra **[Guía de Contribución](CONTRIBUTING.md)** antes de hacer Pull Requests, proponer heurísticas nuevas, o reportar bugs de decaimiento en el algoritmo.

---

## Licencia

Este proyecto está distribuido y protegido bajo la **[Licencia MIT](LICENSE)**.

> *Hecho con rigor por el Cortex Core Team.*

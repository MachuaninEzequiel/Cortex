# Documentación de Implementación: Fase 4

## Fecha: 2026-04-30

---

## Fase 4: Documentación Extendida (`docs/guides/`)

### Archivos creados

| Archivo | Contenido |
| --- | --- |
| `docs/guides/getting-started.md` | Instalación, primer workflow, comandos esenciales, conexión IDE |
| `docs/guides/pipeline-setup.md` | 4 stages DevSecDocOps, config.yaml, modos advisory vs enforced |
| `docs/guides/pipeline-custom-modules.md` | Cómo intercambiar linter/test/security, ejemplos JS/Go/Python, scripts custom |
| `docs/guides/vault-structure.md` | Anatomía del vault, qué genera cada comando, qué va a Git, indexación y búsqueda |
| `docs/guides/enterprise-vault.md` | Modelo 2 niveles, flujo de promoción, topologías, estrategia Git, retrieval multi-nivel |
| `docs/guides/configuration-reference.md` | Referencia campo por campo de config.yaml y org.yaml, presets, profiles |

### Principios de diseño

1. **Cada guía es autocontenida**: Un usuario puede leer una sola guía y entender el tema completo.
2. **Cross-links al final**: Cada guía termina con "Siguiente lectura" apuntando a las guías relacionadas.
3. **Código primero**: Cada concepto se explica con un ejemplo de config o comando concreto, no solo prosa.
4. **Sin dependencia del tutor**: Las guías funcionan perfectamente como markdown en GitHub, independientes del sistema tutor.

### Relación con el Tutor

El tutor muestra un **super-resumen de 20 líneas** de cada tema. Al final de cada panel dice `📖 Guía completa: docs/guides/<archivo>.md`. El usuario que quiera profundizar va directo al doc.

---

## Estado final

- [x] Fase 1: Infraestructura (engine, protocol, CLI registration)
- [x] Fase 2: 7 tópicos (getting_started, commands, workflow, pipeline, vault, enterprise, ide)
- [x] Fase 3: Sistema hint (ProjectState, HintEngine, 8 niveles)
- [x] Fase 4: Documentación extendida (5 guías en docs/guides/)

**Todas las fases completadas.**

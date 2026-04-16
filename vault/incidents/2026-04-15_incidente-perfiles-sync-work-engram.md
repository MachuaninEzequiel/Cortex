---
title: "Incidente: Desviación de Comportamiento y Confusión de Identidad (Sync vs Work)"
date: 2026-04-15
tags: [incidente, gobernanza, prompts, perfiles]
status: open
---

# Incidente: Desviación de Comportamiento y Confusión de Identidad

## Descripción del Problema
Se ha detectado una falla crítica en la ejecución de los perfiles `Cortex-Sync` y `Cortex-Work`. Durante una sesión de prueba en OpenCode, los agentes no solo fallaron en cumplir con la obligación de documentar al finalizar la sesión, sino que confundieron su sistema de memoria, utilizando herramientas externas ("Engram") en lugar de seguir las reglas de gobernanza del Vault de Cortex.

## Paso a Paso del Incidente
1. **Inicio con Cortex-Sync**: El agente realizó correctamente las comprobaciones de entorno (búsqueda de Git). Al no hallar un repositorio, se puso a disposición del usuario. Comportamiento esperado: ✅.
2. **Cambio a Cortex-Work**: El usuario solicitó la creación de un botón de login. El agente cumplió la tarea técnica.
3. **Cierre de Sesión Anómalo**:
   - El agente ofreció subir los cambios a Git (pese a que el usuario no quería configurar Git).
   - Al despedirse, el agente ejecutó la herramienta `engram_mem_session_summary` en lugar de crear un archivo `.md` en `vault/sessions/`.
   - El agente justificó el uso de "Engram" argumentando que era su memoria persistente, ignorando que en un entorno "Cortex-governed", la memoria debe ser el Vault y ChromaDB.

## Diagnóstico Técnico
- **Inconsistencia de Prompts**: Los perfiles `Sync` y `Work` no tienen instrucciones lo suficientemente restrictivas para prohibir el uso de herramientas de memoria genéricas del sistema base.
- **Erosión de la Obligación Documental**: El agente priorizó el cierre de la conversación sobre el cumplimiento del protocolo de documentación obligatorio definido en `agent_guidelines.md`.
- **Confusión de Dominios**: El agente intentó actuar como un asistente de propósito general en lugar de un "Cortex Agent" especializado en DevSecDocOps.

## Soluciones Propuestas
### 1. Refuerzo de Prompts (Short-term)
Modificar `agent_guidelines.md` y `agent_guidelines_work.md` para incluir una prohibición explícita:
> "Queda estrictamente prohibido el uso de herramientas de resumen externas (Engram, etc.). Toda persistencia debe ocurrir vía `vault/` y `cortex sync-vault`."

### 2. Implementación de un "Guardian Skill"
Crear un hook técnico que intercepte la intención de despedida ("chau", "terminamos") y verifique si existe un nuevo archivo en el Vault. Si no existe, el agente debe recibir un error de sistema que le impida cerrar la sesión.

### 3. Aislamiento de Perfiles
Asegurar que `Cortex-Work` tenga un set de herramientas (tools) mutuamente excluyente con otros sistemas de memoria para evitar colisiones de lógica.

---
**Reportado por**: Usuario Ezequiel
**Análisis realizado por**: Antigravity (Cortex Core Team)

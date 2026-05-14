---
name: cortex-vault
description: "Interaccion con la memoria hibrida de Cortex (episodica y semantica). Cargalo cuando necesites buscar contexto con cortex search, guardar decisiones, o consultar el vault antes de implementar."
---

# Skill: Cortex Vault — Interacción con la Memoria

## Descripción

Este skill te enseña a interactuar con el sistema de memoria híbrida de Cortex.
Cárgalo cuando necesites buscar contexto, guardar decisiones, o interactuar con el vault.

## Comandos Esenciales

### Búsqueda en Memoria (SIEMPRE antes de implementar)

```bash
# Búsqueda RRF cross-source (episódica + semántica)
cortex search "término de búsqueda"

# Con más resultados
cortex search "término" --top-k 10

# Solo en memoria episódica (eventos CI, PRs, logs)
cortex search "término" --source episodic

# Solo en vault semántico (arquitectura, decisiones)
cortex search "término" --source semantic
```

### Enriquecimiento de Contexto

```bash
# Enriquecer con archivos modificados en git
cortex context

# Con archivos específicos
cortex context --files cortex/core.py cortex/retrieval/hybrid_search.py
```

### Persistencia de Memoria

```bash
# Guardar memoria episódica manual
cortex remember "Decisión: usamos ONNX en lugar de sentence-transformers por <1ms latencia"

# Con tags para mejor recuperación
cortex remember "Bug: ChromaDB falla con nombres de colección > 63 chars" --tags "bug,chromadb"

# Con summarización LLM (requiere LLM configurado)
cortex remember "texto largo..." --summarize

# Save-session completo al terminar tarea
cortex save-session
cortex save-session --pr 123
cortex save-session --tag "2026-04-21-jwt-auth"
```

### Estadísticas y Gestión

```bash
cortex stats          # resumen de vault + memoria episódica
cortex search "x" | head -5  # preview rápido
```

## Estrategia de Búsqueda

Cuando recibas una tarea, usa esta secuencia:

1. **Búsqueda amplia** → `cortex search "<dominio principal>"`
2. **Búsqueda específica** → `cortex search "<término técnico exacto>"`
3. **Contexto de archivos** → `cortex context` (si ya tienes archivos modificados)
4. **Revisar resultados** → prioriza score >0.7, fuentes recientes

## Interpretación de Resultados RRF

```
[0.89] EPISODIC: PR #119 fix-auth-middleware (2026-04-15)
[0.85] SEMANTIC: vault/architecture/auth-patterns.md
[0.82] EPISODIC: CI failure log - test_auth.py (2026-04-14)
```

- **Score >0.80**: Muy relevante, leer completo
- **Score 0.60-0.80**: Posiblemente relevante, revisar
- **Score <0.60**: Baja relevancia, ignorar a menos que no haya más
- **EPISODIC**: Eventos recientes (CI, PRs, sesiones)
- **SEMANTIC**: Conocimiento estable (arquitectura, decisiones)

## Estructura del Vault

```
vault/
├── sessions/      # Notas de sesión (save-session output)
├── architecture/  # Decisiones arquitectónicas
├── patterns/      # Patrones reutilizables
├── bugs/          # Bugs conocidos y sus fixes
└── adr/           # Architecture Decision Records
```

## CONTEXT.md awareness (Tripartita Refinada — 0.5.0)

Junto al vault, el workspace puede tener un `CONTEXT.md` (en `.cortex/CONTEXT.md` para
new layout, o `CONTEXT.md` en root para legacy). Este archivo es **un prompt asset**: una
tabla de términos de dominio canónicos que el equipo decidió usar para este proyecto.
El uso correcto:

1. **Antes de buscar** — si el usuario menciona un término que parece de dominio
   (no genérico de programación), revisá `CONTEXT.md` para ver si tiene un sinónimo
   canónico. Si lo tiene, buscá por el canónico en lugar del término del usuario.
2. **Antes de persistir memoria** — si vas a guardar una memoria episódica que mencione
   un concepto recurrente, usá el término canónico del `CONTEXT.md`. Esto mejora la
   recuperación futura porque ONNX colocaliza embeddings sobre el mismo término.
3. **Si un término nuevo emerge** — no lo agregues a `CONTEXT.md` vos mismo. Sugerilo
   en el `suggested_context_terms` del handoff para que el `cortex-documenter` decida
   si amerita ser canónico (criterio: el término aparece ≥3 veces en sesiones distintas).

CONTEXT.md vacío significa "proyecto nuevo, sin glosario aún" — no significa "irrelevante".

## Confidence labels en respuestas (Tripartita Refinada — 0.5.0)

A partir de 0.5.0, los hits que retorna `cortex search` y `cortex context` pueden traer
un label `[verified]`, `[asserted]` o `[contradicted]` junto al `memory_type`. Significa:

- **`[verified]`** — el documenter cruzó esta memoria contra el `git diff` real al persistirla.
  Confiá: el contenido refleja cambios que efectivamente ocurrieron.
- **`[asserted]`** — el implementador la reportó pero el Verification Gate no la pudo cruzar
  contra evidencia. Tratala como hipótesis, no como hecho.
- **`[contradicted]`** — la memoria afirma algo que el diff contradice. Ignorala o pedí
  confirmación al usuario antes de usarla.

Memorias sin label son pre-0.5.0 y no pasaron por el Verification Gate. Tratalas con
confianza media (mejor que `[asserted]`, peor que `[verified]`).

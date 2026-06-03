---
name: cortex-vault
description: "Interacción con la memoria híbrida de Cortex (episódica y semántica). Cargala cuando necesites buscar contexto, ubicar dónde va una nota en el vault, registrar una decisión o persistir el cierre de una sesión."
---

# Cortex Vault — Interacción con la Memoria

Cortex mantiene la memoria del proyecto en dos capas:

- **Episódica** — eventos recientes y fechados: sesiones, PRs, commits, fallos de CI.
- **Semántica** — conocimiento estable del vault: arquitectura, decisiones, patrones.

`cortex search` consulta las dos capas a la vez y fusiona los resultados por relevancia. Consultá la memoria **antes** de escribir o implementar: evita repetir decisiones ya tomadas y mantiene la coherencia con lo que ya existe.

## Buscar contexto

```bash
cortex search "término de búsqueda"            # ambas capas, 5 resultados por fuente
cortex search "término" --top-k 10             # más resultados por fuente
cortex search "término" --tag auth --tag api   # exigir tags (deben estar todos)
cortex search "término" --show-scores          # ver score y origen de cada resultado
```

Secuencia recomendada al recibir una tarea:

1. Búsqueda amplia por el dominio principal.
2. Búsqueda específica por el término técnico exacto.
3. `cortex context` si ya hay archivos modificados.
4. Priorizá los resultados de mayor score y más recientes.

## Enriquecer contexto desde los cambios

```bash
cortex context                                 # auto-detecta los archivos modificados en git
cortex context --files ruta/a/archivo.py       # archivos explícitos
cortex context --format compact                # salida compacta para inyectar en un prompt
```

## Registrar memoria

```bash
# Memoria episódica puntual
cortex remember "Decisión: usamos X en lugar de Y por Z"
cortex remember "Bug: el parser falla con nombres > 63 chars" --tag bug --tag parser
cortex remember "texto largo..." --summarize   # resume con LLM (si hay un provider configurado)
```

## Cerrar una sesión

Al terminar una tarea, dejá una nota de sesión estructurada en el vault:

```bash
cortex save-session \
  --title "Título de la sesión" \
  --spec-summary "Qué se pedía resolver" \
  --change "Qué se hizo" \
  --decision "Decisión clave tomada" \
  --next-step "Pendiente para la próxima" \
  --tag release
```

`--title` y `--spec-summary` son obligatorios; el resto es opcional y repetible.

## Estadísticas

```bash
cortex stats        # conteos y resumen de ambas capas de memoria
```

## Interpretar los resultados

Cada resultado trae un score de relevancia y la capa de origen:

- **Score alto** — muy relevante, leelo completo.
- **Score medio** — posiblemente relevante, revisalo.
- **Score bajo** — ignoralo salvo que no haya nada mejor.
- **Episódica** — evento reciente (sesión, PR, CI).
- **Semántica** — conocimiento estable (arquitectura, decisiones).

## Dónde vive cada cosa

```
vault/
├── sessions/      # Notas de cierre de sesión
├── architecture/  # Decisiones arquitectónicas
├── patterns/      # Patrones reutilizables
├── bugs/          # Bugs conocidos y sus soluciones
└── adr/           # Architecture Decision Records
```

Al crear una nota, ubicala en la carpeta que corresponde a su tipo.

## Glosario de dominio (CONTEXT.md)

El proyecto puede incluir un `CONTEXT.md`: una tabla con los términos canónicos que el equipo acordó usar en este dominio. Aprovechalo así:

- **Antes de buscar** — si aparece un término de dominio, fijate si `CONTEXT.md` tiene su forma canónica y buscá por esa.
- **Antes de registrar memoria** — usá siempre el término canónico, no un sinónimo. Así las búsquedas futuras recuperan mejor el contenido.
- **Si surge un término nuevo y recurrente** — no lo agregues vos mismo: proponelo para que se evalúe si merece volverse canónico.

Un `CONTEXT.md` vacío significa "proyecto nuevo, sin glosario todavía", no "irrelevante".

## Confianza de cada memoria

Los resultados pueden traer una etiqueta de confianza:

- **verified** — la memoria fue contrastada contra los cambios reales del código. Confiá en ella.
- **asserted** — fue reportada pero no se pudo contrastar contra evidencia. Tratala como hipótesis.
- **contradicted** — afirma algo que los cambios contradicen. Ignorala o pedí confirmación antes de usarla.

Una memoria sin etiqueta no pasó por esa verificación: tratala con confianza media.

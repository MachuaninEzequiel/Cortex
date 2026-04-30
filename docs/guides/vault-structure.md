# Vault — Estructura y Funcionamiento

## ¿Qué es el Vault?

El vault es la **base de conocimiento** de tu proyecto. Es una carpeta de archivos Markdown que contiene todo lo que Cortex sabe: especificaciones, sesiones de trabajo, decisiones, guías operativas y work items.

A diferencia de la memoria episódica (`.memory/`, que es una base de datos ChromaDB), el vault es **legible por humanos** y **versionable en Git**.

---

## Estructura de carpetas

```
vault/
├── specs/        # Especificaciones técnicas (creadas con cortex create-spec)
├── sessions/     # Sesiones de trabajo (creadas con cortex save-session)
├── decisions/    # Decisiones arquitectónicas (ADRs)
├── runbooks/     # Guías operativas y procedimientos
└── hu/           # Work items importados (Jira, tickets, etc.)
```

### `vault/specs/`

Cada archivo es una especificación técnica creada **antes** de empezar a codear. Contiene:
- Título y objetivo
- Contexto del problema
- Archivos relevantes
- Plan de implementación

```bash
cortex create-spec --title "Auth JWT" --goal "Implementar refresh tokens"
# Crea: vault/specs/2026-04-30-auth-jwt.md
```

### `vault/sessions/`

Cada archivo es una sesión de trabajo guardada **después** de terminar una tarea. Contiene:
- Qué se hizo
- Archivos modificados
- Decisiones tomadas
- Próximos pasos

```bash
cortex save-session --title "JWT Auth" --spec-summary "Refresh tokens implementados"
# Crea: vault/sessions/2026-04-30-jwt-auth.md
```

### `vault/decisions/`

Registros de decisiones arquitectónicas (Architecture Decision Records). Documentan el **por qué** de decisiones técnicas importantes.

### `vault/runbooks/`

Guías operativas paso a paso. Útiles para procedimientos repetibles (deploy, rollback, migración, etc.).

### `vault/hu/`

Work items importados desde sistemas de tickets:

```bash
cortex hu import PROJ-123    # Importar desde Jira
cortex hu get PROJ-123       # Consultar un work item guardado
```

---

## ¿Qué va a Git?

| Ruta | ¿Va a Git? | Razón |
| --- | --- | --- |
| `vault/` | ✅ Sí | Es tu knowledge base, debe estar versionada |
| `config.yaml` | ✅ Sí | Configuración compartida del proyecto |
| `.cortex/org.yaml` | ✅ Sí | Topología enterprise (si aplica) |
| `.cortex/skills/` | ✅ Sí | Perfiles de agente compartidos |
| `.memory/` | ❌ No | Base de datos local (ChromaDB), en `.gitignore` |
| `__pycache__/` | ❌ No | Archivos compilados de Python |

### Regenerar `.memory/` desde el vault

Si clonás un repo que tiene vault pero no `.memory/`, podés reconstruir la memoria episódica:

```bash
cortex sync-vault    # Re-indexar todo el vault en ChromaDB
```

---

## Indexación y búsqueda

El vault alimenta dos tipos de búsqueda:

### Memoria semántica (texto plano)

Cortex busca directamente en los archivos Markdown del vault por coincidencia de texto.

### Memoria episódica (vectores)

Al guardar una sesión o sincronizar el vault, Cortex indexa el contenido en ChromaDB con embeddings vectoriales. Esto permite búsqueda por similaridad semántica.

```bash
cortex search "error handling en middleware"
# Busca en ambas memorias y fusiona resultados con RRF (Reciprocal Rank Fusion)
```

---

## Validación de docs

Cortex puede validar que los documentos del vault cumplan con la estructura esperada:

```bash
cortex validate-docs                    # Validar todos los docs
cortex validate-docs --scope specs      # Solo specs
```

Valida:
- Frontmatter requerido (título, fecha, etc.)
- Estructura de secciones
- Links rotos a archivos

---

## Siguiente lectura

- **Enterprise Vault**: [enterprise-vault.md](enterprise-vault.md)
- **Pipeline setup**: [pipeline-setup.md](pipeline-setup.md)
- **Configuración completa**: [configuration-reference.md](configuration-reference.md)

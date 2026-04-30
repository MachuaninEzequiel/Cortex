# Guía de Primeros Pasos con Cortex

## ¿Qué es Cortex?

Cortex es un sistema de **memoria cognitiva para agentes de IA**. Funciona como el "cerebro" que recuerda todo lo que se trabajó en un proyecto: especificaciones técnicas, decisiones arquitectónicas, sesiones de trabajo y documentación.

Cuando un agente de IA trabaja con Cortex, puede buscar en esa memoria para tener contexto histórico antes de hacer cambios, evitando repetir errores o reinventar soluciones.

---

## Instalación rápida

### 1. Descargar el código base (una sola vez)

```bash
# Elegí dónde guardar Cortex (ejemplo: tu carpeta personal)
cd ~
git clone https://github.com/MachuaninEzequiel/Cortex.git C:\Cortex
```

### 2. Inicializar en tu proyecto

Cortex se instala en el entorno virtual de **tu propio proyecto**:

```bash
cd /ruta/a/mi/proyecto

# 1. Crear y activar entorno virtual
python -m venv .venv

# Windows PowerShell: .venv\Scripts\Activate.ps1
# Windows CMD:        .venv\Scripts\activate.bat
# Linux/macOS:        source .venv/bin/activate

# 2. Instalar Cortex en tu proyecto
pip install -e C:\Cortex

# 3. Configurar el agente
cortex setup agent
```

Esto crea:
- `config.yaml` — Configuración de Cortex
- `vault/` — Tu base de conocimiento (archivos Markdown)
- `.cortex/skills/` — Perfiles de agente
- `.memory/` — Base de datos de memoria episódica (ChromaDB)

---

## Tu primer flujo de trabajo

### Paso 1: Crear una especificación

Antes de codear, documentá qué vas a hacer:

```bash
cortex create-spec --title "Auth JWT" --goal "Implementar refresh tokens"
```

Esto crea un archivo en `vault/specs/` con la especificación técnica.

### Paso 2: Trabajar normalmente

Hacé tu trabajo de desarrollo como siempre. Cortex no interfiere con tu flujo.

### Paso 3: Guardar la sesión

Al terminar, guardá lo que hiciste:

```bash
cortex save-session --title "JWT Auth" --spec-summary "Implementé refresh tokens con rotación"
```

Esto persiste la sesión en `vault/sessions/` y la indexa en la memoria episódica.

### Paso 4: Buscar en el futuro

La próxima vez que necesites contexto:

```bash
cortex search "refresh tokens"
cortex search "error handling en autenticación"
```

Cortex busca en la memoria episódica (ChromaDB) y semántica (vault) simultáneamente.

---

## Comandos esenciales

| Comando | Uso |
| --- | --- |
| `cortex setup agent` | Inicializar Cortex en un proyecto |
| `cortex create-spec` | Crear especificación técnica |
| `cortex save-session` | Guardar sesión de trabajo |
| `cortex search` | Buscar en la memoria |
| `cortex context` | Inyectar contexto por archivos modificados |
| `cortex doctor` | Verificar salud del proyecto |
| `cortex stats` | Estadísticas de memoria |
| `cortex tutor` | Guía interactiva offline |
| `cortex hint` | Tip contextual sobre qué hacer ahora |

Para la lista completa: `cortex --help`

---

## Conectar con tu IDE

Cortex puede funcionar como servidor MCP para tu agente de IA:

```bash
cortex inject --ide cursor        # Cursor
cortex inject --ide claude-code   # Claude Code
cortex inject                     # Menú interactivo
```

---

## Siguiente lectura

- **Pipeline CI/CD**: [pipeline-setup.md](pipeline-setup.md)
- **Estructura del Vault**: [vault-structure.md](vault-structure.md)
- **Enterprise Memory**: [enterprise-vault.md](enterprise-vault.md)
- **Configuración completa**: [configuration-reference.md](configuration-reference.md)

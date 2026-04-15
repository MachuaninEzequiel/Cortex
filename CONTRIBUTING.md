# Guía de Contribución para Cortex

¡Gracias por tu interés en contribuir a **Cortex**!   
Somos un proyecto open source mantenido por desarrolladores apasionados por la ingeniería DevSecDocOps y la arquitectura heurística para Inteligencia Artificial. Este documento describe nuestra convención de trabajo, para que la integración del código que nos envíes sea una experiencia limpia, formativa y gratificante.

##  Código de Conducta
Ante todo, esperamos profesionalismo y cortesía. Este repositorio opera bajo un Código de Conducta estricto: tratamos a toda la comunidad (desde beginners hasta seniors) con respeto y empatía. No toleramos el acoso en ninguna de sus formas en nuestros foros, PRs o reportes de Issues.

---

##  Entorno de Desarrollo (Setup Local)

Para iniciar, cloná el repositorio y levantá tu entorno de la siguiente manera:

```bash
# 1. Clonar tu fork
git clone https://github.com/TU-USUARIO/cortex
cd cortex

# 2. Configurar entorno virtual
python -m venv .venv

# En Linux/Mac:
source .venv/bin/activate
# En Windows:
.venv\Scripts\activate

# 3. Instalación de dependencias (Dev mode)
pip install -e ".[dev]"

# 4. Habilitar hooks pre-commit (Linting en vivo)
pre-commit install
```

---

##  Estilo y Calidad del Código (Ruff + Mypy)

En Cortex utilizamos **Ruff** por su abrumadora velocidad en Linter/Formateo y **Mypy** para garantizar la seguridad de tipado en nuestros grafos tipados.  
Antes de hacer un commit, por favor corré en tu CLI central:

```bash
ruff check .      # Chequeo estático de errores y estilo
ruff format .     # Auto-formateo del código local
pytest            # Verificación del Unit Testing suite actual
```

Cualquier Pull Request fallará automáticamente en nuestro pipeline si `ruff` detecta infracciones del PEP-8 o si baja la cobertura actual de testing de Pytest.

---

##  Flujo de Ramas (Git Branching)

Utilizamos ramas semánticas. Por favor, partí siempre de la rama `master / main` asegurando que la tenés sincronizada, y nombrá tu rama bajo el siguiente esquema:

- Novedades, algoritmos y features: `feat/nombre-cortito` (ej. `feat/qdrant-backend`)
- Reparaciones o errores matemáticos: `fix/nombre-del-bug` (ej. `fix/onnx-memory-leak`)
- Refactorización silenciosa: `refactor/nombre` (ej. `refactor/decay-engine`)
- Temas de documentación: `docs/nombre` (ej. `docs/cli-typos`)

---

##  Pull Requests (PRs)

1. **Revisá los Issues** antes de empezar a programar. Si el feature es muy grande o altera la arquitectura matemática del *Context Enricher*, creá un issue para poder discutirlo con los maintainers primero.
2. **Commit semántico o atómico**: Hacé commits claros. No subas mil cambios sin relación en un solo commit brutal.
3. Asegurate de actualizar y escribir nuevos tests en la carpeta `/tests` si el método Python que tocaste es una novedad.
4. **Plantilla del PR**: Tu Pull Request debe responder con total claridad el **Qué** hace, **Por qué** lo hace, y documentar visualmente el output si aplicara (usando un snippet).
5. **Espera el CI/CD**: Nuestro pipeline es rigoroso. No pidas merges apurados, espera el Ok de la maquinaria de pruebas DevSecDocOps.

---

##  ¿En qué puedes ayudar hoy?

El roadmap está repleto de integraciones emocionantes donde cualquier dev podría brillar. Acá te dejamos algunos pendientes importantes con etiqueta `help-wanted`:

- [ ] **Almacenamiento**: Soporte local o clúster vía *Qdrant backend* (para enterprise deployment).
- [ ] **Búsqueda Avanzada**: Sistema híbrido (Hybrid Search) combinando BM25 + Búsqueda Vectorial Pura para el `VaultReader`.
- [ ] **Grafos de Conocimiento**: Construcción topológica y visual de wikilinks entre memorias episódicas.
- [ ] **Agent Hooks**: Adaptadores estandarizados nativos para los ecosistemas de *CrewAI* y *OpenAI SDK*.
- [ ] **Front-End / UI**: Desarrollo de una capa local en React para visualizar memorias estilo panel administrativo en tu máquina local.

¡De nuevo, muchas gracias por sumarte a Cortex! Esperamos revisar tus aportes emocionado.

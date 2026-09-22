# Agent skill

Fuente: `https://docs.typesafe.ai/agent-skill`.

Skill drop-in para Claude Code, Codex y otros entornos de agente. Le da al coding agent contexto completo de la API TypeSafe: los tres tipos de question, los patrones, y best practices para estructurar evaluaciones.

SKILL.md: `https://github.com/typesafe-ai/skills/blob/main/skills/typesafe-ai/SKILL.md`
Raw: `https://raw.githubusercontent.com/typesafe-ai/skills/main/skills/typesafe-ai/SKILL.md`

## Instalación (una sola; evitar copias duplicadas)

**Claude Code:**

```bash
claude plugin marketplace add typesafe-ai/skills
claude plugin install typesafe@typesafe-ai
```

Update:

```bash
claude plugin marketplace update typesafe-ai
claude plugin update typesafe@typesafe-ai
```

Restart o `/reload-plugins`. Auto-update: `/plugin` → Marketplaces → typesafe-ai → Enable auto-update.

**Otros agentes:**

```bash
npx skills add typesafe-ai/skills --skill typesafe-ai
```

Project-local por default; `-g` global. Update: `npx skills update`.

**Manual:** copiar el directorio entero `skills/typesafe-ai` (incluidos reference files) al skills dir del agente.

## Example prompts oficiales

Nombrar el skill en el prompt (“use the TypeSafe skill”) funciona en cualquier agente. En Claude Code también `/typesafe:typesafe-ai`.

1. Brainstorm de dónde TypeSafe puede reemplazar parsing complejo o código frágil.
2. Con `TYPESAFE_API_KEY` exportada, correr experimentos baratos y proponer cambios según resultados.
3. Apuntar a un cookbook concreto o al índice y pedir si hay patrones similares en el proyecto.

## Good vibe coding principles (oficiales)

1. Hablarlo con el agente, usando esos prompts.
2. Review del plan antes de implementar.
3. Constantes (questions y thresholds) en **un solo lugar**, fáciles de review. Los agentes no son grandes escribiendo questions; esperar edición colaborativa.
4. No tomar assertions at face value; pedir que valide assumptions.

## Common issues oficiales

| Síntoma | Qué chequea la docs |
|---|---|
| El agente no usa el skill | Invocar `/typesafe:typesafe-ai` o “use the TypeSafe skill”. Confirmar installer y restart |
| Routing no es el esperado | Questions y thresholds. Demasiado altos → false negatives; demasiado bajos → false positives. Questions más específicas |
| Confidence thresholds en todos lados | Si solo importa la mejor opción, elegir la de mayor confidence. Si hay algoritmo estadístico, usar probabilities |
| Difícil reviewar el código TypeSafe | Lo que un humano debe reviewar: questions y constants de threshold, en un solo archivo |
| El agente inventa campos de request/response | Skill stale. Update e retry |

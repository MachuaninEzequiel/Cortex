# Fase 6 - Meta-skill y Assets de Workspace

**Fuente:** `docs/autopilot/README.md`
**Estado:** Pendiente de ejecucion

## Introduccion de la fase

En esta fase se lleva a cabo lo definido en el plan global para `Fase 6 - Meta-skill y Assets de Workspace`. El cuerpo operativo de la fase se copia directamente desde `docs/autopilot/README.md` para mantener la especificacion sin reinterpretaciones.

Al terminar la realizacion de esta fase, es obligatorio documentar lo desarrollado dentro de esta misma carpeta en un archivo `REALIZACION.md`. Esa realizacion debe incluir decisiones tomadas, archivos modificados, tests ejecutados, desviaciones respecto del plan, riesgos residuales y pendientes.

## Nota obligatoria para agentes implementadores

Esta nota baja a esta fase las reglas del item 18 del plan global. Es obligatoria antes de implementar.

### Reglas generales heredadas del item 18

- **No improvises.** Segui el alcance exacto de esta fase y no agregues campos, servicios ni adapters fuera de lo definido.
- **No saltees tests.** La fase no esta completa hasta cumplir su gate de salida.
- **Usa `WorkspaceLayout`.** No hardcodees `.cortex/`, `config.yaml`, `vault/` ni rutas legacy.
- **Cada archivo nuevo debe tener test unitario correspondiente** cuando la fase cree codigo runtime.
- **Si algo no esta claro, pregunta antes de asumir.** La racionalizacion es el enemigo del Autopilot.

### Aplicacion especifica en esta fase

- La meta-skill debe ser minima y budget-aware; no cargues todo el flujo completo por defecto.
- El setup normal sin Autopilot debe quedar igual.
- `build_all_prompts()` no debe cargar Autopilot por defecto.
- Cualquier asset Autopilot debe instalarse solo cuando Autopilot este habilitado.

## Plan operativo original

## Fase 6 - Meta-skill y Assets de Workspace

### Objetivo

Instalar la meta-skill minima y prompts asociados.

### Archivos a crear

```text
cortex/autopilot/skills/using-cortex-autopilot.md
cortex/autopilot/skills/cortex-autopilot-finish.md
tests/unit/autopilot/test_skills_assets.py
```

### Archivos a tocar

```text
cortex/setup/cortex_workspace.py
cortex/ide/prompts.py
```

### Regla importante

No cambiar las skills actuales en esta fase salvo referencia opcional.

### Contenido obligatorio de la meta-skill (referencia del plan global §10.2-10.6)

La meta-skill `using-cortex-autopilot.md` DEBE contener:

1. Prioridad de instrucciones (usuario > Autopilot > sistema) — ver §10.6.
2. Regla de no usar memoria externa.
3. Criterios para activar preflight.
4. Criterios para evitar preflight.
5. Presupuesto de contexto.
6. Regla de documentacion final.
7. Uso de Fast Track por defecto.
8. Uso de Deep Track solo con umbral.
9. Como cerrar si una tool falla.
10. Guard anti-racionalizacion — ver §10.4.
11. Regla de verificacion antes de completar — ver §10.5.

#### Guard anti-racionalizacion (§10.4 — contenido literal obligatorio)

La meta-skill DEBE incluir esta tabla. Es codigo de comportamiento, no prosa decorativa:

```markdown
## Senales de que estas saltando el flujo

Si te encontras pensando alguna de estas cosas, PARA. Estas racionalizando.

| Pensamiento | Realidad |
|-------------|----------|
| "Es una pregunta simple, no necesito preflight" | Si modifica archivos, necesita al menos un checkpoint |
| "Ya se la respuesta, no busco contexto" | El contexto tiene informacion que no recordas. Usa cortex_context |
| "Documento despues" | El cierre automatico no inventa. Si no documentas, queda auto-draft |
| "No vale la pena una session note" | Si hubo cambios observados, vale la pena |
| "Cortex ya tiene toda la info" | Verifica con cortex_context antes de asumir |
| "Es solo un fix rapido" | Los fix rapidos sin contexto son los que mas rompen |
| "Puedo saltar el checkpoint" | Si cambiaste archivos, el checkpoint protege tu trabajo |
| "No necesito verificar, se que funciona" | Ejecuta el comando de verificacion. Confianza != evidencia |
| "Esto es muy simple para el flujo completo" | Lo simple con proceso es rapido. Lo simple sin proceso se complica |
```

#### Regla de verificacion antes de completar (§10.5 — contenido literal obligatorio)

```markdown
## Regla de verificacion

Antes de afirmar que un cambio funciona:

1. Identifica que comando prueba tu afirmacion (test, build, lint).
2. Ejecuta el comando COMPLETO (no parcial, no de memoria).
3. Lee la salida completa. Verifica exit code.
4. Solo entonces afirma el resultado.
5. Si no ejecutaste verificacion, escribi "No verificado" en el checkpoint.

NO es aceptable:
- Decir "deberia funcionar" sin haber corrido tests
- Decir "listo" sin verificar que compila
- Confiar en el reporte de un subagente sin verificar el diff
- Usar "probablemente", "seguramente" o "deberia" para describir estado
```

#### Prioridad de instrucciones (§10.6 — contenido literal obligatorio)

```markdown
## Prioridad de instrucciones

1. Instrucciones explicitas del usuario (AGENT.md, system-prompt.md, requests directos) — maxima prioridad
2. Skills de Cortex Autopilot — sobreescriben comportamiento default del sistema
3. Prompt de sistema del IDE — minima prioridad

Si el usuario dice "no uses preflight" y Autopilot dice "siempre usa preflight", segui al usuario. El usuario tiene el control.
```

### Principio de tokens

La meta-skill debe ser menor a 1500 palabras en la primera version.

### Checklist

- [x] `using-cortex-autopilot` se instala solo si Autopilot esta habilitado.
- [x] El setup normal sin Autopilot queda igual.
- [x] `build_all_prompts()` no carga Autopilot por defecto.
- [x] Hay una funcion separada `build_autopilot_prompts()`.
- [x] La meta-skill incluye la tabla anti-racionalizacion (§10.4).
- [x] La meta-skill incluye la regla de verificacion (§10.5).
- [x] La meta-skill incluye la prioridad de instrucciones (§10.6).
- [x] La meta-skill no supera 1500 palabras.

### Gate de salida

- El usuario puede instalar skills Autopilot sin afectar perfiles manuales.
- La meta-skill contiene los 11 puntos obligatorios listados arriba.

---



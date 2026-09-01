# 15 · Estado de Rebranding Visual, Integración con Herdr y Evaluación de UX de la TUI

**Fecha de documento:** 29 de Agosto de 2026  
**Módulos afectados:** `crates/cortex-branding`, `crates/cortex-companion`, `integrations/herdr`  
**Estado:** Implementado / En revisión de diseño y contenido por UX

---

## 1. Resumen Ejecutivo y Contexto

Este ciclo de trabajo tuvo como objetivo resolver dos problemas centrales de la experiencia de usuario de Cortex:

1. **Rebranding Visual Integral**: Reemplazar la estética previa por la identidad voxel 3D isométrica y la paleta menta/esmeralda/bosque definida en `assets/nueva-estetica/nuevo-logo-cortex.png`.
2. **Desacople e Integración Nativa con Herdr**: Eliminar la necesidad de ocupar una ventana de terminal completa y aislada para Cortex, permitiendo una convivencia fluida, simultánea y complementaria con el agente principal de trabajo (ej. `pi`, `agy`, `codex`) dentro del multiplexor de terminales Herdr.

---

## 2. Avances Técnicos Implementados

### 2.1. Crate `cortex-branding`
- **Matrices Isométricas Voxel 3D**:
  - `LogoVariant::Full` (44×34 px): Splash y pantallas principales con iluminación cenital (`ICE` `#EAFDF5`), cuerpo menta/esmeralda (`LIGHT` `#A7F3D0` / `CYAN` `#34D399`), estantes inferiores escalonados (`BLUE` `#10B981`) y sombra de profundidad (`DEEP` `#064E3B`).
  - `LogoVariant::Compact` (28×20 px): Versión intermedia para layouts medianos.
  - `LogoVariant::Mark` (13×10 px): Isotipo compacto para headers de paneles y barras angostas.
- **Wordmark "CORTEX" Voxel 3D**:
  - Modelado en pixel-font 5×7 para las 6 letras (`C-O-R-T-E-X`), con caras frontales blancas/menta, aristas superiores iluminadas y extrusión diagonal 3D hacia abajo y a la derecha en verde bosque profundo.
- **Suite de Tests**: 20 tests unitarios y 7 tests de geometría geométrica pasando al 100% con verificación de ratios, paleta y silueta.

---

### 2.2. Modos de Integración con Herdr (`cortex-companion`)

Se crearon 3 entrypoints y comandos dedicados con comportamientos ergonómicos diferenciados:

```
┌────────────────────────────────────────────────────────────────────────┐
│ MODOS DE INTEGRACIÓN HERDR                                             │
├────────────────────────────────────────────────────────────────────────┤
│ 1. cortex-herdr-sidecar   ──> Dock Lateral Izquierdo (30% / 70%)       │
│ 2. cortex-herdr-float     ──> Bottom Drawer HUD (25% alto abajo)       │
│ 3. cortex-herdr-copilot   ──> Co-Pilot Dual con inyección de prompts   │
└────────────────────────────────────────────────────────────────────────┘
```

#### A. `cortex-herdr-sidecar` (Dock Lateral 30/70)
- **Mecanismo**: Abre un split en Herdr, ejecuta un swap de paneles para posicionar a Cortex a la izquierda y reajusta el tamaño mediante `herdr pane resize` para dejar a Cortex en el 30% de ancho y al agente en el 70% derecho.
- **Layout Adaptativo**: Layout vertical con botones en cuadrícula 2×2 con altura fija de 3 filas para evitar cualquier solapamiento.
- **Sidebar de Herdr**: Reporta automáticamente metadata al panel nativo de Herdr:
  ```json
  { "agent": "cortex", "agent_status": "working", "custom_status": "30% Dock" }
  ```

#### B. `cortex-herdr-float` (Bottom Drawer HUD)
- **Mecanismo**: Abre un split inferior (`direction = down`) y redimensiona a un 25% de altura. El agente permanece activo y 100% visible en el 75% superior de la pantalla.
- **Layout Horizontal Compacto (`hud_screen.rs`)**: Diseñado exclusivamente para espacios de 8 a 14 filas:
  - Fila superior: Resumen de telemetría en una sola línea (proyecto, rama, sesión activa, estado de doctor, memoria).
  - Columna izquierda: Próxima acción con score y costo.
  - Columna derecha: Botones horizontales espaciados (`[⚡ Aprobar]`, `[Sesiones]`, `[Brain]`, `[Menú]`, `[Esc Salir]`).
  - Cierre rápido con `Esc` o `q`.

#### C. `cortex-herdr-copilot` (Co-Pilot Dual con Inyección Directa)
- **Mecanismo**: Detecta automáticamente el pane del agente adyacente en el mismo workspace (ej. `pi` en `wD:p1`).
- **Superficie de Interacción (`copilot_screen.rs`)**:
  - Badge de vinculación en vivo: `● VINCULADO: pi (wD:p1)`.
  - Visualizador de fases de trabajo: `1.SPEC ➔ 2.PLAN ➔ ▶ 3.IMPLEMENTACIÓN ➔ 4.VERIFICACIÓN`.
  - Caja de instrucción propuesta para el agente.
  - Botón interactivo de inyección: Al presionar `Enter` o clickear `[ 🚀 Inyectar Próxima Instrucción al Agente ]`, Cortex envía el comando/prompt directo a la terminal del agente mediante `herdr pane send-text <pane_id> "<texto>\n"`.

---

### 2.3. Aislamiento y Resiliencia de Terminal (I/O)
- **Eliminación de artefactos JSON**: Se redirigió `stdin`, `stdout` y `stderr` a `Stdio::null()` / `Stdio::piped()` en todas las llamadas CLI a Herdr para evitar que fragmentos de JSON ensucien la pantalla del TUI.
- **Limpieza de framebuffer**: Invocación explícita de `terminal.clear()` antes del bucle principal y al salir para asegurar transiciones sin basura visual.

---

## 3. Registro de Disconformidad y Crítica del Usuario (Feedback Actual)

> [!IMPORTANT]
> **Punto Crítico Registrado**: El usuario ha manifestado expresamente que **no le convence el diseño estético ni el contenido actual que muestra la TUI de Cortex**, considerando que aún no resulta suficientemente funcional ni atractiva.

### 3.1. Crítica sobre la Estética y el Logo
- Aunque se implementó la lógica de renderizado por medio bloque (`▀`/`▄`) y la paleta verde/menta/blanca, la resolución de caracteres en terminal puede dar una sensación de tosquedad si no se ajusta la escala y los espacios vacíos.
- La tipografía CORTEX y el isotipo requieren una mayor armonización con el espacio útil de la pantalla para no restar protagonismo a la información operativa.

### 3.2. Crítica sobre el Contenido y la Utilidad Real de la TUI
- **Baja relevancia operativa de la metadata**: Mostrar únicamente tarjetas de "sesión activa", "doctor: OK" o "conteos de memoria" no le aporta valor tangible al desarrollador mientras está programando con su agente.
- **Falta de dinamismo en el flujo**: La TUI actual se comporta más como un "dashboard estático" que como un asistente inteligente que empuja el trabajo hacia adelante.
- **Sobrecarga de botones secundarios**: Los botones como `[ Menú ]` o `[ Sesiones ]` ocupan espacio valioso sin ofrecer una acción directa sobre el código en el 90% del tiempo de uso.

---

## 4. Propuestas de Rediseño de Contenido y UX (Roadmap de Mejora)

Para transformar la TUI en una herramienta verdaderamente potente y atractiva, se plantean las siguientes líneas de evolución:

```
┌────────────────────────────────────────────────────────────────────────┐
│ PROPUESTA DE REDISEÑO DE CONTENIDO Y VALOR REAL                        │
├────────────────────────────────────────────────────────────────────────┤
│ 1. Radar de Contexto & Desvíos del Agente (Agent Guardrails)           │
│ 2. Buffer de Diff en Vivo / Aprobación Visual de Cambios               │
│ 3. Historial de Decisiones de Arquitectura (ADRs on-the-fly)           │
│ 4. Consola de Prompts Rápidos con Templates Contextuales              │
│ 5. Estética Minimalista "Cyber-Terminal" con menos cajas y más datos   │
└────────────────────────────────────────────────────────────────────────┘
```

### 4.1. Sustitución de Paneles Estáticos por Información Operativa
1. **Radar de Guardrails del Agente**:
   - Monitorear si el agente adyacente (`pi`) se está saliendo de la especificación o tocando archivos fuera del scope.
   - Mostrar alertas en tiempo real: `⚠ Pi modificó un archivo fuera de la obra activa`.
2. **Buffer de Aprobaciones con Diff Visual**:
   - En lugar de un botón genérico de "Aprobar", mostrar el diff sintáctico coloreado de lo que el agente va a modificar antes de que lo aplique.
3. **Selector Rápido de Contexto & Skills**:
   - Un selector rápido (tipo fuzzy finder `Ctrl+K`) para inyectar contexto de documentación, esquemas o reglas al agente sin tener que escribirlo a mano.

### 4.2. Rediseño Visual y Estético
1. **Estilo Minimalista Técnico**:
   - Reducir el grosor y cantidad de bordes de cajas rectangulares (`Borders::ALL`) que saturan la vista.
   - Utilizar divisores de línea sutiles (`─`) y tipografía con contraste jerárquico claro.
2. **Header Compacto y Elegante**:
   - Mantener el logo isotipo voxel en escala limpia (5 filas) sin invadir el área de trabajo.
   - Texto de marca sobrio y moderno con acentos en verde menta neón.

---

## 5. Conclusión y Estado Actual de los Archivos

- **Código fuente en producción**:
  - `rust/crates/cortex-branding/src/logo.rs` y `wordmark.rs` con matrices voxel 3D.
  - `rust/crates/cortex-companion/src/screens/hud_screen.rs` para el modo float inferior.
  - `rust/crates/cortex-companion/src/screens/copilot_screen.rs` para el modo Co-Pilot.
  - `rust/crates/cortex-companion/src/herdr.rs` con swap 30/70, split inferior y detección de agentes.
- **Binarios instalados y funcionales**: `cortex-herdr-sidecar`, `cortex-herdr-float`, `cortex-herdr-copilot`.
- **Próximo foco acordado**: Rediseñar la propuesta de contenido, jerarquía visual y valor interactivo de la TUI para que no sea un simple dashboard, sino una herramienta indispensable en el flujo de desarrollo.

# Spec 10: SystemOne, Model Router y Límites de Host (Host Boundaries)

**Estado:** Aprobado para implementación (Fase 0 y Fase 1 en curso).  
**Rama:** `typesafe`  
**Extiende:** [01-dos-modos.md](01-dos-modos.md), [02-arquitectura-modular.md](02-arquitectura-modular.md), [08-direct-y-jevdd.md](08-direct-y-jevdd.md), [09-portero.md](09-portero.md).

---

## 1. Motivación y Cambio de Paradigma

### 1.1 Desacoplamiento Arquitectónico: De "Jev" a "SystemOne"
No atamos la arquitectura a un modelo comercial específico (`Jev`). La arquitectura de Cortex formaliza el concepto de **`SystemOne`** (en honor al *Sistema 1* de Daniel Kahneman: inferencia rápida, instintiva, determinista, sub-10ms y costo marginal cero, frente al *Sistema 2* que son los LLMs generativos de razonamiento profundo).

* **SystemOne** es la arquitectura y el contrato de Rust.
* **TypeSafe Jev (jev-1.13.0)** es el primer *provider/driver* por defecto de SystemOne.
* El sistema es agnóstico: en el futuro puede admitir drivers locales (ONNX), modelos open-source cuantizados u otros backends de juicio rápido sin reescribir Cortex.

### 1.2 Formato Canónico Obligatorio: `provider:model_id`
Queda terminantemente prohibido usar nombres aislados y ambiguos como `"Claude 3.5 Sonnet"` o `"GPT-4"`.
Todo modelo debe identificarse con su par canónico:
```
<provider>:<model_id>
```
Ejemplos reales:
* `openrouter:anthropic/claude-3.5-sonnet`
* `openai-codex:gpt-4o`
* `google:gemini-2.5-pro`
* `anthropic:claude-3-5-sonnet-20241022`

---

## 2. Aislamiento de Entornos y Límites de Política (Host Boundaries)

### 2.1 Cumplimiento Estricto de Términos de Servicio (ToS)
* **Google Antigravity**: Los Términos de Servicio de Antigravity prohíben explícitamente usar tokens o credenciales de su suscripción Pro fuera del CLI/IDE de Antigravity.
* **Aislamiento de runtime**: Cuando el usuario trabaja dentro de un CLI específico, no se deben cruzar credenciales ni forzar APIs incompatibles.

### 2.2 Matriz de Políticas por Host Environment

| Host Detectado | Proveedores Permitidos | Política Estricta |
|---|---|---|
| **Antigravity (`agy`)** | `google` | Únicamente modelos del ecosistema Google/Gemini autorizados en la sesión. Bloqueo estricto de llamadas externas a Anthropic/OpenAI directo que rompan el sandbox. |
| **Pi (`pi.dev`)** | `openai-codex`, `openrouter`, `xai` (según `auth.json`) | Solo proveedores autenticados en `~/.pi/agent/auth.json`. Bloqueo de modelos AGY fuera de Antigravity. |
| **Claude Code (`claude`)** | `anthropic` | Solo modelos accesibles por la suscripción de Claude Code. |
| **Cortex Brain Standalone** | Múltiples (según CLIs instalados o API keys) | Gestión de perfiles independientes por host. |

---

## 3. CLI Model Discovery Engine

Cortex no obliga al usuario a escribir texto ciego en un input. Un módulo nativo en Rust inspecciona localmente y de forma pasiva los stores de los CLIs instalados:

1. **Pi CLI**:
   - Lee `~/.pi/agent/auth.json` (proveedores activos).
   - Lee `~/.pi/agent/models-store.json` (catálogo cacheado de modelos reales).
2. **Antigravity CLI**:
   - Lee `~/.gemini/antigravity-cli/` y tokens de sesión de Google.
3. **Claude Code CLI**:
   - Lee `~/.claude/.credentials.json`.

Devuelve una lista unificada de tuplas seguras:
```rust
pub struct ProviderModelInfo {
    pub provider: String,
    pub model_id: String,
    pub display_name: String,
    pub source_cli: String,
    pub is_active: bool,
}
```

---

## 4. Model Router Inteligente (`Purpose::ModelRouting`)

### 4.1 Roles Especializados de Subagentes
El Model Router asigna cada paso del flujo a un tier o modelo específico configurado por el usuario:
* **`Architect / Designer` (`cortex-code-designer`)**: Modelo de razonamiento profundo para contratos y arquitectura.
* **`Implementer` (`cortex-code-implementer` / `cortex-SDDwork`)**: Modelo de código principal para refactorización e implementación.
* **`Documenter` (`cortex-documenter`)**: Modelo rápido, económico y excelente en prosa para redactar notas de sesión, ADRs y changelogs al cierre.
* **`Auditor / Reviewer` (`review_checkpoint`)**: Validación analítica de diffs y verificación de claims.

### 4.2 Nueva Primitiva: `Score` (escala 0..2)
Junto con `Choice` y `Noul`, se añade la primitiva `Score` (número fraccionario de 0.0 a 2.0):
* Para calificar el **impacto de ADRs**: `0.0` (cosmético), `1.0` (diseño local), `2.0` (ADR estructural innegociable).
* Para calificar la **solidez de claims**: medir objetivamente la evidencia de tests provista por el subagente.

### 4.3 Despacho Dinámico: "Rebuild the Menu"
* `cortex_session_status` evalúa en vivo qué subagentes están disponibles según el estado de la sesión.
* SystemOne elige el próximo paso con umbral de confianza $\ge 0.85$.
* Si la confianza es menor a `0.85`, se escala a confirmación con el usuario antes de bifurcar la ejecución.

---

## 5. Memoria en Dos Niveles (Tiered Memory)

1. **Memoria Primaria (Alta Prioridad en RRF)**:
   - ADRs vigentes, especificaciones canónicas, contratos de API e invariantes.
   - Ponderación de búsqueda máxima.
2. **Memoria de Archivo (Baja Prioridad / Tag `archive`)**:
   - Volcados completos de diffs, logs de compilación y notas intermedias.
   - Persistidos en el Vault y SQLite para que **nunca se pierda la información**, pero marcados con `tier: archive` para no generar ruido en consultas cotidianas salvo búsqueda histórica explícita.

---

## 6. Persistencia en `config.yaml`

```yaml
system_one:
  enabled: true
  provider: typesafe
  model_router:
    enabled: true
    hosts:
      antigravity:
        designer: "google:gemini-2.5-pro"
        implementer: "google:gemini-2.5-pro"
        documenter: "google:gemini-2.5-flash"
        auditor: "google:gemini-2.5-flash"
      pi:
        designer: "openrouter:anthropic/claude-3.5-sonnet"
        implementer: "openrouter:anthropic/claude-3.5-sonnet"
        documenter: "openai-codex:gpt-4o-mini"
        auditor: "openai-codex:gpt-4o-mini"
      claude_code:
        designer: "anthropic:claude-3-5-sonnet"
        implementer: "anthropic:claude-3-5-sonnet"
        documenter: "anthropic:claude-3-5-haiku"
        auditor: "anthropic:claude-3-5-haiku"
```

---

## 7. Interfaz de Usuario en Cortex Brain (`apps/brain-ui`)

* Pestaña renombrada a **SystemOne & Routing**.
* Badge visual del **Host Activo** detectado.
* Dropdowns inteligentes poblados automáticamente con los modelos reales logueados en los CLIs del usuario (`provider:model_id`).
* Tarjetas pedagógicas explicando cada subagente.
* Todo 100% Opt-in y con modo Fail-Open (si SystemOne está apagado, Cortex opera sin dependencias en Direct).

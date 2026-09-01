# Prompt para el siguiente agente (G-A3: scan de proyectos)

Copiá y pegá esto cuando le pidas al siguiente agente que continue
la Obra 20 (Cortex Brain App) desde donde la dejé:

---

Sos un agente de coding. Vas a continuar el desarrollo de **Cortex
Brain App** (Obra 20) sobre la rama `feature/transformacion-2026-08`
del repo `/home/chucho/Cortex`. El último commit mergeado es
`f3efa5d` (G-A2 cerrado). Tu próximo gate es **G-A3: scan
recursivo de proyectos Cortex con cache**.

**Paso 1 — Leer el handoff completo:**
`/home/chucho/Cortex/handoffs/HANDOFF-CORTEX-BRAIN-APP.md`.
Ahí está todo el contexto: decisiones cerradas, lecciones
aprendidas, convenciones, código que tenés que tocar, y las 2
decisiones pendientes que tenés que cerrar con el dueño.

**Paso 2 — Leer los docs canónicos en este orden:**
1. `/home/chucho/Cortex/docs/transformacion/21-CORTEX-BRAIN-APP-ESTADO.md`
   (estado actual, lo más concreto).
2. `/home/chucho/Cortex/docs/transformacion/20-CORTEX-BRAIN-APP.md`
   (propuesta completa, G-A3 está en §4.1).
3. `/home/chucho/Cortex/docs/transformacion/19-LIQUID-LOAD-UNLOAD-Y-MEJORAS.md`
   (motor LFM, contexto del cual partimos).

**Paso 3 — Cerrá con el dueño las 2 decisiones pendientes** (raíces
del scan, manejo de `config.yaml` corrupto). El handoff tiene mi
sugerencia para cada una. No asumas.

**Paso 4 — Decime el plan del commit de G-A3** (alcance exacto,
archivos a tocar, criterios de pase). Yo te apruebo o ajusto.

**Paso 5 — Implementá con los 3 gates de verificación verdes:**
- `cargo test -p cortex-brain-app`
- `cargo clippy -p cortex-brain-app --all-targets -- -D warnings`
- `cargo fmt -p cortex-brain-app --check`

**Paso 6 — Commit** con mensaje Conventional Commits en español:
`app(tauri): scan recursivo de proyectos con cache (G-A3)`.

**Reglas duras:**
- No toques crates que no sean `cortex-brain-app` (excepto
  `Cargo.toml` del workspace si hace falta).
- No agregues deps nuevas al lock si se puede evitar.
- Commits atómicos, suite verde antes de commitear.
- No abras la GUI para verificar — el dueño la abre (no tenés DISPLAY).
- Si encontrás un problema con un test que ya pasaba, **no lo
  borres**: dejalo fallando, anotalo en el output, y avisame.

Avisame al cierre de G-A3 y armamos G-A4.

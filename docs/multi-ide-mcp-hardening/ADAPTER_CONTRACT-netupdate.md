# ADAPTER_CONTRACT.md — corregido tras decompilar `pi.cpython-311.pyc`

Este documento reemplaza la versión anterior. La versión previa tenía
asunciones equivocadas sobre cómo funciona el adapter Pi de Cortex.
Esta versión describe el modelo **real** del `PiAdapter` y propone los
cambios mínimos para que `cortex-net` funcione sin romper el contrato
existente.

---

## 1. Cómo funciona el adapter Pi hoy (modelo real)

El `PiAdapter` en `cortex/ide/adapters/pi.py` implementa la interfaz
`IDEAdapter` con estas piezas clave:

### 1.1 Atributos

```python
class PiAdapter(IDEAdapter):
    name = "pi"
    display_name = "Pi Coding Agent"
```

### 1.2 Constante de módulo

```python
_SHARED_AGENTS = (
    "cortex-code-explorer.md",
    "cortex-code-implementer.md",
    "cortex-documenter.md",
)
```

Esos 3 archivos son **canónicos**: la fuente de verdad vive en
`.cortex/subagents/<archivo>.md` y el adapter los espeja al bundle
antes de cada inject.

**Observación crítica**: `cortex-code-designer.md` NO está en la lista
de shared. Vive solo en el bundle `cortex-pi/.pi/agents/`. Tampoco están
`cortex-sync.md`, `cortex-SDDwork.md`, `cortex-security-auditor.md`, ni
`cortex-test-verifier.md`.

### 1.3 `_default_pi_bundle_dir()`

```python
def _default_pi_bundle_dir() -> Path:
    """Path to the in-tree cortex-pi/ bundle.

    Path(__file__) is cortex/ide/adapters/pi.py, so 4 parents up lands at
    the repo root that contains both cortex/ and cortex-pi/.
    """
    return Path(__file__).resolve().parents[3] / "cortex-pi"
```

El bundle vive en el repo de Cortex en `<cortex-repo>/cortex-pi/` —
hermano de `cortex/` (el paquete Python).

### 1.4 `sync_canonical_subagents(project_root, bundle_dir=None)`

Antes de copiar el bundle al workspace, este método sobreescribe los
3 shared agents del bundle con la versión actual de
`.cortex/subagents/<archivo>.md` del proyecto.

```python
# Pseudocode reconstruido desde el bytecode
def sync_canonical_subagents(self, project_root, bundle_dir=None):
    layout = WorkspaceLayout.discover(project_root)
    canonical_dir = layout.subagents_dir  # .cortex/subagents/
    if not canonical_dir.is_dir():
        return []
    bundle = bundle_dir or _default_pi_bundle_dir()
    pi_bundle_agents = bundle / ".pi" / "agents"
    pi_bundle_agents.mkdir(parents=True, exist_ok=True)
    overwritten = []
    for name in _SHARED_AGENTS:
        src = canonical_dir / name
        if src.exists():
            dst = pi_bundle_agents / name
            dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
            overwritten.append(dst)
    return overwritten
```

### 1.5 `inject_profiles(project_root, prompts, sync_canonical=True)`

```python
# Pseudocode reconstruido
def inject_profiles(self, project_root, prompts, sync_canonical=True):
    if sync_canonical:
        self.sync_canonical_subagents(project_root)
    cortex_pi_dir = _default_pi_bundle_dir()
    if not cortex_pi_dir.exists():
        raise FileNotFoundError(f"cortex-pi template directory not found at {cortex_pi_dir}/")
    files_written = []
    for item in cortex_pi_dir.iterdir():
        dest = project_root / item.name
        if item.is_dir():
            shutil.copytree(item, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dest)
        files_written.append(str(dest))
    return files_written
```

Es decir: **copia todo el contenido de `cortex-pi/` al `project_root`
tal cual, sin sustituciones**. Acepta `prompts` por contrato de la
interfaz pero los ignora — Pi tiene sus propios prompts en el bundle.

### 1.6 `inject_mcp(project_root)`

```python
def inject_mcp(self, project_root):
    """Pi Coding Agent uses bash tools, MCP injection not required."""
    return []
```

**No genera `.pi/mcp.json`**. El `mcp.json` del bundle es lo que entra al
workspace. La extensión `cortex-mcp.ts` se encarga de resolver
`${cwd}` en runtime mirando el cwd actual de Pi.

### 1.7 `get_config_paths()`

```python
def get_config_paths(self):
    """Pi configuration is project-local, no global config paths."""
    return {}
```

### 1.8 `detect_installation()`

```python
def detect_installation(self):
    return shutil.which("pi") is not None
```

Detecta si el binario `pi` del paquete npm `@mariozechner/pi-coding-agent`
está en PATH.

### 1.9 `uninstall(project_root)`

```python
# Pseudocode reconstruido
def uninstall(self, project_root):
    files_removed = []
    pi_dir = project_root / ".pi"
    if pi_dir.exists():
        shutil.rmtree(pi_dir)
        files_removed.append(".pi/")
    for f in ("AGENTS.md", "justfile", "README.md", "extensions"):
        path = project_root / f
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            files_removed.append(f if path.is_file() else f + "/")
    return files_removed
```

Wipe completo de lo que `inject_profiles` puso. No discrimina entre
archivos managed y custom del usuario — si el usuario tenía un
`.pi/agents/mi-agent-custom.md`, se borra.

---

## 2. Dónde aplicar los cambios de cortex-net (mapeo correcto)

Los archivos que generé en `/home/claude/output/cortex-pi/` corresponden al
**bundle**. Para que tu proyecto Cortex los adopte, hay que copiarlos a:

```
D:\DevSecDocOps\DevSecDocOps-3erCortex\cortex-repo\cortex-pi\
```

Reemplazando el contenido actual. Pero hay 3 archivos que **además** hay
que actualizar en otro lugar:

### Archivos que viven en DOS lugares (canónicos)

| Archivo en bundle | Fuente canónica que sync_canonical va a usar |
|---|---|
| `cortex-pi/.pi/agents/cortex-code-explorer.md` | `.cortex/subagents/cortex-code-explorer.md` |
| `cortex-pi/.pi/agents/cortex-code-implementer.md` | `.cortex/subagents/cortex-code-implementer.md` |
| `cortex-pi/.pi/agents/cortex-documenter.md` | `.cortex/subagents/cortex-documenter.md` |

**Si solo actualizás el bundle**, en el próximo `cortex inject pi` el
`sync_canonical_subagents` pisa esos 3 con la versión vieja de
`.cortex/subagents/`. Hay que tocar los dos lados.

### Archivos que viven SOLO en el bundle

Todo lo demás de mi entrega vive solo en `cortex-pi/`:

- `cortex-pi/.pi/agents/cortex-sync.md` (NUEVA sección "NO PARTICIPÁS")
- `cortex-pi/.pi/agents/cortex-SDDwork.md` (reescritura completa)
- `cortex-pi/.pi/agents/cortex-code-designer.md` (tools cortex-net + sección)
- `cortex-pi/.pi/agents/cortex-security-auditor.md` (checkpoint en vez de YAML)
- `cortex-pi/.pi/agents/cortex-test-verifier.md` (checkpoint en vez de YAML)
- `cortex-pi/.pi/extensions/cortex-net.ts` (extensión nueva, ~980 líneas)
- `cortex-pi/.pi/settings.json` (carga cortex-net.ts por default)
- `cortex-pi/.pi/system.md` (directive 7 nueva)
- `cortex-pi/.pi/agents/teams.yaml` (simplificado, agrega cortex-byo)
- `cortex-pi/.pi/agents/agent-chain.yaml` (marcado como fallback)
- `cortex-pi/justfile` (recetas role-*)
- `cortex-pi/AGENTS.md` (Release 2.5+net)
- `cortex-pi/README.md` (Release 2.5+net)

---

## 3. Cambios MÍNIMOS que requeriría `pi.py` para cortex-net

El adapter actual funciona casi entero para 2.5+net. Solo hay **un cambio
opcional pero recomendado** que vos podés decidir si lo agregás:

### 3.1 (Opcional, recomendado) — Agregar el designer a `_SHARED_AGENTS`

Hoy:
```python
_SHARED_AGENTS = (
    "cortex-code-explorer.md",
    "cortex-code-implementer.md",
    "cortex-documenter.md",
)
```

Propuesto:
```python
_SHARED_AGENTS = (
    "cortex-code-designer.md",       # NUEVO en Phase 09.B
    "cortex-code-explorer.md",
    "cortex-code-implementer.md",
    "cortex-documenter.md",
)
```

**Por qué**: el designer apareció en Phase 09.B (Pluggable Middle) y es
una pieza estable del Deep Track. Es coherente que viva en
`.cortex/subagents/` como los otros agents de implementación, no como
exclusivo del bundle de Pi.

**Si NO querés hacer este cambio**: el designer queda como agent
"exclusivo de Pi". El bundle lo trae, otros IDEs no lo verán. Funcional
pero asimétrico.

### 3.2 (Recomendado fuerte) — Versión del contract en el bundle

Hoy el adapter no escribe ninguna marca de versión del bundle. Eso hace
imposible detectar drift entre versiones del bundle y versiones del
adapter. Propongo agregar al inject:

```python
# Al final de inject_profiles, antes del return
(project_root / ".pi" / ".bundle-version").write_text("2.5+net\n", encoding="utf-8")
files_written.append(str(project_root / ".pi" / ".bundle-version"))
```

Y al uninstall, agregar `.pi/.bundle-version` a los archivos a remover
(implícito porque ya borra `.pi/` entero).

### 3.3 (NO recomendado) — Generar mcp.json

Mi spec anterior decía esto. **Era incorrecto**. El mcp.json es parte
del bundle estático y la sustitución de `${cwd}` la hace la extensión
`cortex-mcp.ts` en runtime. No tocar.

---

## 4. Cómo se resuelven session_id y rol en runtime (modelo D adoptado)

**Decisión confirmada el día del rediseño**: la extensión `cortex-net.ts`
resuelve todo dinámicamente desde el filesystem y los hooks de Pi.
**Ninguna env var es obligatoria.** El adapter Python no necesita
cambios. El CLI de Cortex no necesita un wrapper de Pi.

### 4.1 session_id — leído del filesystem

La extensión llama `resolveSessionId(cwd)` que sigue este orden:

1. `process.env.CORTEX_SESSION_ID` — override explícito (tests, scripts).
2. `<cwd>/.cortex/session.lock` — fuente canónica que `cortex-sync`
   escribe al abrir una Session. Es lo que la extensión usa en uso normal.
3. `null` — si no hay ninguno, la red queda en **standby** (no se
   registra cliente) pero el hub puede estar corriendo si otro Pi lo
   levantó. Al próximo `before_agent_start` la extensión reintenta leer
   el lock por si `cortex-sync` corrió en el ínterin.

**Requisito implícito**: `cortex-sync` (o el backend de Cortex cuando
abre una Session) debe escribir el session_id en
`<workspace>/.cortex/session.lock`. Si tu implementación actual NO
hace eso, hay que agregarlo. Es **un cambio pequeño** del lado del
backend de Cortex, no del adapter Pi.

### 4.2 rol — inferido del agent activo

La extensión llama `resolveRole(activeAgentName)` que sigue este orden:

1. **`activeAgentName`** que viene del hook `before_agent_start` —
   fuente más fresca, refleja el agent que Pi acaba de activar. Si
   coincide con uno de los 7 agents Cortex mapeados, la extensión
   registra al cliente con ese rol. **Este es el camino default.**
2. `process.env.CORTEX_NET_ROLE` — escape hatch para terminales
   dedicadas (modo `just role-designer`). Solo se respeta si el hook no
   provee un agent name.
3. `process.env.CORTEX_ACTIVE_AGENT` — legacy/compat.
4. `null` — agent fuera del mapa (incluye `cortex-sync` por diseño B').

### 4.3 Re-registración dinámica al cambiar de agent

Si el usuario hace `/system cortex-code-implementer` mid-session
(estando registrado como `designer`), la extensión:

1. Detecta el cambio en `before_agent_start`.
2. Llama `client.stop()` (unregister del rol viejo).
3. Crea un nuevo cliente con `role="implementer"` y llama `.start()`.
4. Notifica al usuario en el chat.

Esto significa que **el mismo proceso Pi puede rotar entre roles** a lo
largo de una sesión sin reiniciar. Es el comportamiento natural para
Codex y otros single-agent IDEs que vienen embebidos en Pi.

### 4.4 ¿Qué necesita hacer el justfile?

Nada especial. La receta `just cortex` levanta Pi con las extensiones
y listo:

```just
cortex:
    pi -e {{EXT}}/cortex-tools.ts -e {{EXT}}/cortex-mcp.ts -e {{EXT}}/cortex-net.ts -e {{EXT}}/system-select.ts -e {{EXT}}/damage-control.ts
```

Las recetas `role-*` siguen existiendo como escape hatch para multi-terminal
demo-style. Ahí sí se exporta `CORTEX_NET_ROLE`.

### 4.5 Impacto en el adapter

**Ninguno.** El adapter no necesita modificarse para que esto funcione.
Las únicas piezas que la extensión necesita son:

- El bundle `cortex-pi/` con `cortex-net.ts` adentro (lo entrego en
  esta carpeta).
- El archivo `.cortex/session.lock` escrito por `cortex-sync` al abrir
  Session (asumido como existente; si no existe, se agrega).

---

## 5. Otras observaciones del adapter

### 5.1 El uninstall es agresivo

`uninstall()` borra `.pi/` entero. Si un usuario customizó
`.pi/themes/mi-tema.json` o agregó skills propios, los pierde. **No es
mi problema arreglarlo en este patch** — solo lo señalo para que sepas
que existe.

### 5.2 El nombre del repo de Cortex en tu disco

El `.pyc` reveló el filepath:

```
D:\DevSecDocOps\DevSecDocOps-3erCortex\cortex-repo\cortex\cortex\ide\adapters\pi.py
```

Confirmando que estás en Windows y que el bundle debe ir en
`D:\DevSecDocOps\DevSecDocOps-3erCortex\cortex-repo\cortex-pi\`.

### 5.3 `claude_desktop.py` está vacío (0 bytes)

No es relevante para Pi pero te lo señalo por las dudas — probablemente
sea un placeholder de un adapter futuro que nunca se implementó.

---

## 6. Checklist para vos para terminar de adoptar 2.5+net

- [ ] Confirmar que los 3 archivos en `.cortex/subagents/` (explorer,
      implementer, documenter) están alineados con mi entrega. Si no,
      hay que actualizarlos en ese path también.
- [ ] Reemplazar el contenido de `D:\...\cortex-repo\cortex-pi\` con
      el contenido de `/mnt/user-data/outputs/cortex-pi/`.
- [ ] (Opcional) Agregar `cortex-code-designer.md` a `_SHARED_AGENTS` en
      `pi.py` y crear `.cortex/subagents/cortex-code-designer.md`.
- [ ] (Opcional) Agregar la escritura de `.pi/.bundle-version` al
      `inject_profiles`.
- [ ] Actualizar el `justfile` para setear `CORTEX_SESSION_ID` desde
      `.cortex/session.lock`.
- [ ] Smoke test: borrar `.pi/` de un proyecto de prueba, correr
      `cortex inject pi`, abrir Pi, verificar que `/cortex-net` muestra
      el rol asignado.

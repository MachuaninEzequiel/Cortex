#!/usr/bin/env python3
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "apps" / "brain-ui" / "dist"
SHOTS = ROOT / "assets" / "shots"
SHOTS.mkdir(parents=True, exist_ok=True)

# Buscar CSS compilado
css_files = list((DIST / "assets").glob("*.css"))
if not css_files:
    print("Error: No se encontró CSS en dist/assets")
    exit(1)
css_path = css_files[0].resolve()
css_rel = f"file://{css_path}"

# 1. Main UI Showcase
MAIN_HTML = f"""<!DOCTYPE html>
<html lang="es" class="dark">
<head>
  <meta charset="UTF-8">
  <link rel="stylesheet" href="{css_rel}">
  <style>
    body {{ margin: 0; padding: 0; background: #11111b; font-family: 'JetBrains Mono', ui-sans-serif, system-ui, sans-serif; }}
    .window-frame {{ width: 1100px; height: 720px; background: #1e1e2e; display: flex; flex-direction: column; overflow: hidden; border: 1px solid #313244; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.7); }}
  </style>
</head>
<body>
  <div class="window-frame">
    <!-- TopBar -->
    <header class="h-12 border-b border-[#313244] bg-[#181825] px-4 flex items-center justify-between select-none">
      <div class="flex items-center gap-3">
        <div class="flex gap-1.5 mr-2">
          <div class="w-3 h-3 rounded-full bg-[#f38ba8]/80"></div>
          <div class="w-3 h-3 rounded-full bg-[#f9e2af]/80"></div>
          <div class="w-3 h-3 rounded-full bg-[#a6e3a1]/80"></div>
        </div>
        <span class="text-sm font-bold tracking-wider text-[#cba6f7] font-mono">CORTEX BRAIN</span>
        <span class="text-[10px] bg-[#313244] text-[#bac2de] px-2 py-0.5 rounded font-mono">v2.0.0 (Rust)</span>
      </div>
      <div class="flex items-center gap-3 font-mono text-xs">
        <div class="flex items-center gap-1.5 bg-[#313244]/40 px-2.5 py-1 rounded border border-[#313244]">
          <span class="w-2 h-2 rounded-full bg-[#a6e3a1] animate-pulse"></span>
          <span class="text-[#a6adc8]">modelo:</span>
          <span class="text-[#cba6f7] font-semibold">Liquid LFM2.5 1.2B (Q4_K_M)</span>
        </div>
        <button class="flex items-center gap-1.5 bg-[#313244]/60 hover:bg-[#313244] text-[#cdd6f4] px-2.5 py-1 rounded border border-[#45475a] transition">
          <span>⚙️</span> Ajustes
        </button>
      </div>
    </header>

    <!-- Governance Bar -->
    <div class="h-9 border-b border-[#313244] bg-[#11111b]/90 px-4 flex items-center justify-between font-mono text-xs select-none">
      <div class="flex items-center gap-2">
        <div class="flex items-center gap-1.5 px-2 py-0.5 rounded bg-[#a6e3a1]/15 text-[#a6e3a1] border border-[#a6e3a1]/30">
          <span class="w-1.5 h-1.5 rounded-full bg-[#a6e3a1]"></span>
          <span class="font-medium">Sesión activa (46 checkpoints)</span>
        </div>
        <button class="flex items-center gap-1 px-2 py-0.5 rounded bg-[#313244] hover:bg-[#45475a] text-[#cdd6f4] border border-[#45475a]">
          <span>📍</span> Checkpoint
        </button>
        <button class="flex items-center gap-1 px-2 py-0.5 rounded bg-[#89b4fa]/20 hover:bg-[#89b4fa]/30 text-[#89b4fa] border border-[#89b4fa]/40 font-semibold">
          <span>🕸️</span> WebGraph (5 nodos)
        </button>
      </div>
      <div class="flex items-center gap-2">
        <button class="flex items-center gap-1.5 px-2 py-0.5 rounded bg-[#a6e3a1]/15 text-[#a6e3a1] border border-[#a6e3a1]/30">
          <span>🛡️</span> Doctor: 100% Sano
        </button>
        <span class="text-[#585b70]">|</span>
        <span class="text-[#6c7086] text-[11px]">Memoria Híbrida: 384d ONNX + BM25</span>
      </div>
    </div>

    <!-- Main Content: Sidebar + Chat -->
    <div class="flex-1 flex overflow-hidden">
      <!-- Sidebar -->
      <aside class="w-64 border-r border-[#313244] bg-[#181825] flex flex-col p-3 gap-2 select-none">
        <div class="flex items-center justify-between text-xs text-[#a6adc8] font-mono px-1 font-semibold">
          <span>PROYECTOS DETECTADOS</span>
          <span class="text-[10px] text-[#585b70]">Auto-scan</span>
        </div>
        <div class="space-y-1">
          <div class="p-2.5 rounded-lg bg-[#313244] border border-[#cba6f7]/40 flex flex-col gap-1 cursor-pointer">
            <div class="flex items-center justify-between">
              <span class="text-xs font-bold text-[#cdd6f4] font-mono">cortex-demo</span>
              <span class="text-[10px] bg-[#a6e3a1]/20 text-[#a6e3a1] px-1.5 py-0.2 rounded font-mono">activo</span>
            </div>
            <span class="text-[10px] text-[#6c7086] truncate">~/pruebas/cortex-demo</span>
            <div class="flex items-center gap-2 text-[10px] text-[#a6adc8] mt-1">
              <span>🌿 feature/transformacion</span>
              <span>•</span>
              <span class="text-[#cba6f7]">46 ckpts</span>
            </div>
          </div>
          <div class="p-2.5 rounded-lg bg-[#181825] hover:bg-[#313244]/40 border border-transparent flex flex-col gap-1 cursor-pointer transition">
            <div class="flex items-center justify-between">
              <span class="text-xs font-medium text-[#bac2de] font-mono">Cortex</span>
              <span class="text-[10px] text-[#585b70] font-mono">master</span>
            </div>
            <span class="text-[10px] text-[#585b70] truncate">~/Cortex</span>
          </div>
        </div>
        <div class="mt-auto p-2 rounded bg-[#11111b] border border-[#313244] text-[11px] font-mono text-[#6c7086]">
          <div class="text-[#a6adc8] font-semibold mb-1">⚡ Estado de RAM</div>
          <div class="flex justify-between"><span>LFM2.5 en memoria:</span><span class="text-[#a6e3a1]">712 MB</span></div>
          <div class="flex justify-between"><span>Auto-unload:</span><span class="text-[#fab387]">en 82s</span></div>
        </div>
      </aside>

      <!-- Chat Area -->
      <main class="flex-1 flex flex-col bg-[#1e1e2e]">
        <div class="flex-1 p-4 overflow-y-auto space-y-4">
          <!-- User Msg -->
          <div class="flex gap-3 max-w-3xl">
            <div class="w-7 h-7 rounded-full bg-[#cba6f7]/20 border border-[#cba6f7]/40 flex items-center justify-center text-xs font-bold text-[#cba6f7]">U</div>
            <div class="flex-1 bg-[#181825] border border-[#313244] rounded-xl p-3 text-xs text-[#cdd6f4] font-mono leading-relaxed">
              ¿Cuál es la arquitectura actual del subsistema de embeddings y cuántas notas tenemos en el vault?
            </div>
          </div>

          <!-- Assistant Msg with Tool Execution -->
          <div class="flex gap-3 max-w-3xl">
            <div class="w-7 h-7 rounded-full bg-[#89b4fa]/20 border border-[#89b4fa]/40 flex items-center justify-center text-xs font-bold text-[#89b4fa]">CB</div>
            <div class="flex-1 space-y-2.5">
              <!-- Tool Call Badge -->
              <div class="flex items-center gap-2 p-2 rounded-lg bg-[#11111b] border border-[#313244] font-mono text-[11px] text-[#bac2de]">
                <span class="text-[#a6e3a1]">✓</span>
                <span>Herramienta ejecutada:</span>
                <code class="bg-[#313244] text-[#fab387] px-1.5 py-0.5 rounded">vault.stats</code>
                <span class="text-[#6c7086]">→ 12 notas (5 ADRs, 4 Specs, 3 Modules)</span>
              </div>

              <div class="bg-[#181825] border border-[#313244] rounded-xl p-4 text-xs text-[#cdd6f4] font-sans leading-relaxed space-y-2">
                <p>El proyecto <strong>cortex-demo</strong> cuenta actualmente con <strong>12 notas indexadas</strong> en el vault local y una sesión activa con 46 checkpoints.</p>
                <div class="p-3 bg-[#11111b] rounded-lg border border-[#313244] font-mono text-[11px] text-[#89b4fa]">
                  <div>• Motor de Embeddings: <strong>ONNX Runtime nativo (ort)</strong></div>
                  <div>• Idioma Español: <code>intfloat/multilingual-e5-large</code> (1024d)</div>
                  <div>• Búsqueda Híbrida: BM25 + Coseno con fusión RRF</div>
                </div>
                <p class="text-[#a6adc8] text-[11px]">Podés inspeccionar la topología completa haciendo click en el botón <strong>WebGraph</strong> en la barra superior.</p>
              </div>
            </div>
          </div>
        </div>

        <!-- Input Box -->
        <div class="p-3 border-t border-[#313244] bg-[#181825]">
          <div class="flex items-center gap-2 bg-[#1e1e2e] border border-[#45475a] rounded-xl px-3 py-2">
            <input type="text" placeholder="Consultar a Cortex Brain sobre este proyecto... (Enter para enviar)" class="flex-1 bg-transparent text-xs font-mono text-[#cdd6f4] outline-none" value="">
            <span class="text-[11px] font-mono text-[#585b70] bg-[#181825] px-1.5 py-0.5 rounded">Ctrl+Shift+B</span>
            <button class="bg-[#cba6f7] hover:bg-[#b4befe] text-[#11111b] px-3 py-1 rounded-lg text-xs font-semibold font-mono">Enviar</button>
          </div>
        </div>
      </main>
    </div>
  </div>
</body>
</html>
"""

# 2. WebGraph Modal Showcase
WEBGRAPH_HTML = f"""<!DOCTYPE html>
<html lang="es" class="dark">
<head>
  <meta charset="UTF-8">
  <link rel="stylesheet" href="{css_rel}">
  <style>
    body {{ margin: 0; padding: 0; background: #11111b; font-family: 'JetBrains Mono', ui-sans-serif, system-ui, sans-serif; }}
    .window-frame {{ width: 1100px; height: 720px; background: #11111b; display: flex; align-items: center; justify-content: center; }}
    .modal-box {{ width: 1000px; height: 640px; background: #1e1e2e; border: 1px solid #313244; border-radius: 12px; display: flex; flex-direction: column; overflow: hidden; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.9); }}
  </style>
</head>
<body>
  <div class="window-frame">
    <div class="modal-box">
      <!-- Modal Header -->
      <div class="h-12 border-b border-[#313244] bg-[#181825] px-5 flex items-center justify-between select-none">
        <div class="flex items-center gap-2">
          <span class="text-base">🕸️</span>
          <h3 class="font-bold text-[#cdd6f4] font-mono text-sm">Grafo de Conocimiento del Proyecto (WebGraph)</h3>
          <span class="text-[10px] bg-[#89b4fa]/20 text-[#89b4fa] px-2 py-0.5 rounded font-mono font-semibold">5 nodos • 4 aristas</span>
        </div>
        <div class="flex items-center gap-2">
          <button class="text-xs bg-[#89b4fa]/20 hover:bg-[#89b4fa]/30 text-[#89b4fa] px-2.5 py-1 rounded border border-[#89b4fa]/40 font-mono font-semibold">
            🌐 Servidor Web Externo
          </button>
          <button class="text-xs bg-[#313244] text-[#a6adc8] px-2.5 py-1 rounded hover:bg-[#45475a]">✕</button>
        </div>
      </div>

      <!-- Modal Body -->
      <div class="flex-1 flex overflow-hidden">
        <!-- Node Directory List -->
        <div class="w-64 border-r border-[#313244] bg-[#181825] flex flex-col p-3 gap-2 font-mono text-xs">
          <input type="text" placeholder="Buscar nodo..." class="w-full bg-[#11111b] border border-[#313244] rounded px-2.5 py-1.5 text-xs text-[#cdd6f4] outline-none" value="">
          <div class="text-[10px] font-bold text-[#6c7086] mt-1">DIRECTORIO DE NODOS</div>
          <div class="space-y-1 overflow-y-auto">
            <div class="p-2 rounded bg-[#cba6f7]/15 border border-[#cba6f7]/40 text-[#cdd6f4] flex items-center justify-between cursor-pointer">
              <div class="flex items-center gap-1.5"><span class="w-2 h-2 rounded-full bg-[#cba6f7]"></span><span>cortex-demo</span></div>
              <span class="text-[9px] text-[#cba6f7]">module</span>
            </div>
            <div class="p-2 rounded hover:bg-[#313244] text-[#bac2de] flex items-center justify-between cursor-pointer">
              <div class="flex items-center gap-1.5"><span class="w-2 h-2 rounded-full bg-[#fab387]"></span><span>ADR-004-embeddings</span></div>
              <span class="text-[9px] text-[#fab387]">adr</span>
            </div>
            <div class="p-2 rounded hover:bg-[#313244] text-[#bac2de] flex items-center justify-between cursor-pointer">
              <div class="flex items-center gap-1.5"><span class="w-2 h-2 rounded-full bg-[#a6e3a1]"></span><span>2026-08-24_migracion</span></div>
              <span class="text-[9px] text-[#a6e3a1]">spec</span>
            </div>
            <div class="p-2 rounded hover:bg-[#313244] text-[#bac2de] flex items-center justify-between cursor-pointer">
              <div class="flex items-center gap-1.5"><span class="w-2 h-2 rounded-full bg-[#89b4fa]"></span><span>src/lib.rs</span></div>
              <span class="text-[9px] text-[#89b4fa]">file</span>
            </div>
            <div class="p-2 rounded hover:bg-[#313244] text-[#bac2de] flex items-center justify-between cursor-pointer">
              <div class="flex items-center gap-1.5"><span class="w-2 h-2 rounded-full bg-[#89b4fa]"></span><span>src/graph.rs</span></div>
              <span class="text-[9px] text-[#89b4fa]">file</span>
            </div>
          </div>
        </div>

        <!-- Interactive SVG Canvas -->
        <div class="flex-1 bg-[#11111b] relative flex items-center justify-center">
          <svg width="680" height="520" viewBox="0 0 680 520">
            <!-- Edges -->
            <line x1="340" y1="260" x2="160" y2="150" stroke="#45475a" stroke-width="2" stroke-dasharray="4" />
            <line x1="340" y1="260" x2="520" y2="150" stroke="#45475a" stroke-width="2" />
            <line x1="340" y1="260" x2="200" y2="390" stroke="#45475a" stroke-width="2" />
            <line x1="340" y1="260" x2="480" y2="390" stroke="#45475a" stroke-width="2" />

            <!-- Orbit Circle -->
            <circle cx="340" cy="260" r="180" fill="none" stroke="#313244" stroke-width="1" stroke-dasharray="2" opacity="0.6" />

            <!-- Center Node (Module) -->
            <g transform="translate(340, 260)" class="cursor-pointer">
              <circle r="36" fill="#181825" stroke="#cba6f7" stroke-width="3" />
              <text text-anchor="middle" y="4" fill="#cdd6f4" font-size="11" font-weight="bold" font-family="monospace">cortex-demo</text>
              <text text-anchor="middle" y="18" fill="#cba6f7" font-size="9" font-family="monospace">MODULE</text>
            </g>

            <!-- Node 1 (ADR) -->
            <g transform="translate(160, 150)" class="cursor-pointer">
              <circle r="28" fill="#181825" stroke="#fab387" stroke-width="2" />
              <text text-anchor="middle" y="3" fill="#cdd6f4" font-size="9" font-weight="bold" font-family="monospace">ADR-004</text>
              <text text-anchor="middle" y="14" fill="#fab387" font-size="7" font-family="monospace">ADR</text>
            </g>

            <!-- Node 2 (Spec) -->
            <g transform="translate(520, 150)" class="cursor-pointer">
              <circle r="28" fill="#181825" stroke="#a6e3a1" stroke-width="2" />
              <text text-anchor="middle" y="3" fill="#cdd6f4" font-size="9" font-weight="bold" font-family="monospace">Spec-2026</text>
              <text text-anchor="middle" y="14" fill="#a6e3a1" font-size="7" font-family="monospace">SPEC</text>
            </g>

            <!-- Node 3 (file lib.rs) -->
            <g transform="translate(200, 390)" class="cursor-pointer">
              <circle r="26" fill="#181825" stroke="#89b4fa" stroke-width="2" />
              <text text-anchor="middle" y="3" fill="#cdd6f4" font-size="9" font-weight="bold" font-family="monospace">lib.rs</text>
              <text text-anchor="middle" y="13" fill="#89b4fa" font-size="7" font-family="monospace">FILE</text>
            </g>

            <!-- Node 4 (file graph.rs) -->
            <g transform="translate(480, 390)" class="cursor-pointer">
              <circle r="26" fill="#181825" stroke="#89b4fa" stroke-width="2" />
              <text text-anchor="middle" y="3" fill="#cdd6f4" font-size="9" font-weight="bold" font-family="monospace">graph.rs</text>
              <text text-anchor="middle" y="13" fill="#89b4fa" font-size="7" font-family="monospace">FILE</text>
            </g>
          </svg>

          <!-- Legend -->
          <div class="absolute bottom-4 left-4 bg-[#181825]/90 border border-[#313244] px-3 py-2 rounded-lg flex gap-4 font-mono text-[10px]">
            <div class="flex items-center gap-1.5"><span class="w-2 h-2 rounded-full bg-[#cba6f7]"></span><span>Módulo</span></div>
            <div class="flex items-center gap-1.5"><span class="w-2 h-2 rounded-full bg-[#fab387]"></span><span>ADR</span></div>
            <div class="flex items-center gap-1.5"><span class="w-2 h-2 rounded-full bg-[#a6e3a1]"></span><span>Spec</span></div>
            <div class="flex items-center gap-1.5"><span class="w-2 h-2 rounded-full bg-[#89b4fa]"></span><span>Archivo</span></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</body>
</html>
"""

# Renderizar con Firefox Headless
for name, html in [("cortex-brain-main", MAIN_HTML), ("cortex-brain-webgraph", WEBGRAPH_HTML)]:
    tmp_html = Path(f"/tmp/{name}.html")
    tmp_html.write_text(html, encoding="utf-8")
    out_png = SHOTS / f"{name}.png"
    cmd = [
        "firefox", "--headless",
        "--profile", tempfile.mkdtemp(prefix="ff-shot-"),
        "--screenshot", str(out_png),
        "--window-size=1100,720",
        f"file://{tmp_html.resolve()}"
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"Generado con éxito: {out_png} ({out_png.stat().st_size // 1024} KB)")


DOCTOR_HTML = f"""<!DOCTYPE html>
<html lang="es" class="dark">
<head>
  <meta charset="UTF-8">
  <link rel="stylesheet" href="{css_rel}">
  <style>
    body {{ margin: 0; padding: 0; background: #11111b; font-family: 'JetBrains Mono', ui-sans-serif, system-ui, sans-serif; }}
    .window-frame {{ width: 1100px; height: 720px; background: #11111b; display: flex; align-items: center; justify-content: center; }}
    .modal-box {{ width: 620px; height: 500px; background: #1e1e2e; border: 1px solid #313244; border-radius: 12px; display: flex; flex-direction: column; overflow: hidden; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.9); }}
  </style>
</head>
<body>
  <div class="window-frame">
    <div class="modal-box">
      <!-- Modal Header -->
      <div class="h-12 border-b border-[#313244] bg-[#181825] px-5 flex items-center justify-between select-none">
        <div class="flex items-center gap-2">
          <span class="text-base">🛡️</span>
          <h3 class="font-bold text-[#cdd6f4] font-mono text-sm">Auditoría de Salud (Cortex Doctor)</h3>
        </div>
        <button class="text-xs bg-[#313244] text-[#a6adc8] px-2.5 py-1 rounded hover:bg-[#45475a]">✕</button>
      </div>

      <!-- Health Status Banner -->
      <div class="p-4 border-b border-[#313244] bg-[#a6e3a1]/10 flex items-center gap-3">
        <div class="w-8 h-8 rounded-full bg-[#a6e3a1]/20 border border-[#a6e3a1]/40 flex items-center justify-center text-[#a6e3a1] font-bold">✓</div>
        <div>
          <div class="text-xs font-bold text-[#a6e3a1] font-mono">100% SANO — GOBERNANZA PERFECTA</div>
          <div class="text-[11px] text-[#a6adc8]">Estructura de proyecto, sesiones y configuración válidas.</div>
        </div>
      </div>

      <!-- Checklist -->
      <div class="flex-1 p-5 space-y-3 font-mono text-xs overflow-y-auto">
        <div class="p-3 rounded-lg bg-[#181825] border border-[#313244] flex items-center justify-between">
          <div class="flex items-center gap-2.5">
            <span class="text-[#a6e3a1]">●</span>
            <div>
              <div class="font-bold text-[#cdd6f4]">Layout de Workspace (.cortex)</div>
              <div class="text-[10px] text-[#6c7086]">Estructura .cortex/ y vault/ descubierta correctamente</div>
            </div>
          </div>
          <span class="text-[10px] bg-[#a6e3a1]/20 text-[#a6e3a1] px-2 py-0.5 rounded">OK</span>
        </div>

        <div class="p-3 rounded-lg bg-[#181825] border border-[#313244] flex items-center justify-between">
          <div class="flex items-center gap-2.5">
            <span class="text-[#a6e3a1]">●</span>
            <div>
              <div class="font-bold text-[#cdd6f4]">Sesión Activa & Checkpoints</div>
              <div class="text-[10px] text-[#6c7086]">Sesión activa con 46 checkpoints registrados y verificables</div>
            </div>
          </div>
          <span class="text-[10px] bg-[#a6e3a1]/20 text-[#a6e3a1] px-2 py-0.5 rounded">OK</span>
        </div>

        <div class="p-3 rounded-lg bg-[#181825] border border-[#313244] flex items-center justify-between">
          <div class="flex items-center gap-2.5">
            <span class="text-[#a6e3a1]">●</span>
            <div>
              <div class="font-bold text-[#cdd6f4]">Motor de Inferencia LLM</div>
              <div class="text-[10px] text-[#6c7086]">Liquid LFM2.5 1.2B cargado en memoria RAM (712 MB)</div>
            </div>
          </div>
          <span class="text-[10px] bg-[#a6e3a1]/20 text-[#a6e3a1] px-2 py-0.5 rounded">OK</span>
        </div>

        <div class="p-3 rounded-lg bg-[#181825] border border-[#313244] flex items-center justify-between">
          <div class="flex items-center gap-2.5">
            <span class="text-[#a6e3a1]">●</span>
            <div>
              <div class="font-bold text-[#cdd6f4]">Índice Vectorial ONNX</div>
              <div class="text-[10px] text-[#6c7086]">VectorCache sincronizado con fingerprint salado de modelo</div>
            </div>
          </div>
          <span class="text-[10px] bg-[#a6e3a1]/20 text-[#a6e3a1] px-2 py-0.5 rounded">OK</span>
        </div>
      </div>
    </div>
  </div>
</body>
</html>
"""

tmp_html = Path("/tmp/cortex-brain-doctor.html")
tmp_html.write_text(DOCTOR_HTML, encoding="utf-8")
out_png = SHOTS / "cortex-brain-doctor.png"
cmd = [
    "firefox", "--headless",
    "--profile", tempfile.mkdtemp(prefix="ff-shot-"),
    "--screenshot", str(out_png),
    "--window-size=1100,720",
    f"file://{tmp_html.resolve()}"
]
subprocess.run(cmd, check=True, capture_output=True)
print(f"Generado con éxito: {out_png} ({out_png.stat().st_size // 1024} KB)")


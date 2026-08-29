# HUD v1 — grilla canónica (contrato visual)

Fuente de verdad para implementar en ratatui. El mock
`assets/hud-v1/index.html` pinta **esta** grilla. Si el HTML y este
archivo divergen, gana este archivo.

Pane de referencia: **100 columnas × 10 filas** (≈ 25% de un terminal
40 filas). Si el pane es más ancho, las regiones de texto se estiran
hacia la derecha; los botones se anclan a la derecha. Si es más angosto
de 80, el mark pasa a 1 fila y el prompt a 1 línea.

## Paleta (tokens de `cortex-branding`)

| Token | Hex | Uso en el HUD |
|---|---|---|
| `BG` | `#071310` | fondo del pane |
| `ICE` | `#EAFDF5` | texto de prompt, mark despierto (caras altas) |
| `LIGHT` | `#A7F3D0` | hover / mark mid |
| `CYAN` | `#34D399` | acento, botones, cursor de consulta |
| `BLUE` | `#10B981` | mark cuerpo |
| `DEEP` | `#064E3B` | mark dormido, bordes |
| `SHADOW` | `#043328` | sombra mark |
| `MUTED` | `#6E968B` | labels, meta |
| `TEXT` | `#EAFDF5` | texto principal |
| `BORDER_IDLE` | `#204138` | reglas horizontales `─` |
| `SURFACE_SUBTLE` | `#0E241E` | hover de botón |

## Rects (x, y, w, h) — origen esquina superior izquierda del HUD

```
MARK        ( 0, 0, 14, 3)   isotipo Mark recortado a 3 filas half-block
BRAND       (15, 0, 12, 1)   "CORTEX"
AGENT       (28, 0, 72, 1)   "pi idle" alineado a la derecha
META        (15, 1, 85, 1)   proyecto · rama · sesión · fase
RULE_1      ( 0, 3,100, 1)   línea menta muy oscura
PROMPT      ( 0, 4, 82, 2)   instrucción para el agente que codea
COPY        (84, 4, 16, 2)   [ Copiar ]
RULE_2      ( 0, 6,100, 1)
ACTION      ( 0, 7, 62, 1)   higiene propuesta
APPROVE     (64, 7, 17, 1)   [ Aprobar ]
SKIP        (82, 7, 18, 1)   [ Saltar ]
RULE_3      ( 0, 8,100, 1)
ASK         ( 0, 9,100, 1)   › preguntale a Cortex
```

## Estados del mark (logo = RAM)

| Estado | Look | Significa |
|---|---|---|
| `idle` | DEEP/BLUE, glow ICE al 40%, respiración 3.2s | Liquid **no** está en RAM |
| `awake` | ICE/LIGHT/CYAN a plena, glow CYAN | Liquid **cargado** (consulta) |
| `no_color` | silueta plana, sin animar | `NO_COLOR` / reduced-motion |

Idle: ciclo `opacity` 0.62 ↔ 0.92 sobre las caras ICE/LIGHT, 3.2s ease-in-out, loop. Awake: sin atenuar; +1px glow CYAN.

## Copy del mock (no cambiar en v1 salvo el dueño)

Prompt idle:

```
descomponé el plan en tickets según la spec de auth;
no toques fuera de src/auth.
```

Higiene idle: `Validar documentos del vault`

Ask placeholder: `preguntale a Cortex`

Consulta (estado awake), pregunta: `hay una decisión de jwt?`

Respuesta (reemplaza PROMPT+ACTION; COPY sigue, ASK queda):

```
sí — vault/decisions/2026-04-jwt-hs256.md
HS256 local, no RS256. el spec de auth lo cita.
```

Prompt copiable en consulta (COPY toma esto):

```
implementá auth según vault/decisions/2026-04-jwt-hs256.md
(HS256). no cambies el algoritmo. no toques fuera de src/auth.
```

## Qué no va en esta grilla

Botones Sesiones / Menú / Brain / Doctor OK / conteos de memoria.
Cajas `Borders::ALL`. Emoji. Wordmark CORTEX 5 filas. Inyectar.
Finish / cerrar sesión.

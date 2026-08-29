# HUD v1 — grilla canónica (contrato visual)

Fuente de verdad para ratatui: **este archivo**. El HTML pinta esta
partición. Logo = recortes de `assets/nueva-estetica/nuevo-logo-cortex.png`
(`logo-mark.png` + `logo-word.png`), no una máscara 13×10.

## Partición

El HUD es **dos columnas**. El logo no comparte filas con el texto.

```
┌──────────────────┬─────────────────────────────────────────────┐
│ BRAND            │ DIALOGS                                     │
│ mismo fondo HUD  │ meta / prompt / higiene / ask               │
│ cubos en celdas  │                                             │
│ wordmark en celdas│                                            │
└──────────────────┴─────────────────────────────────────────────┘
```

El HTML de preview todavía muestra un recorte PNG sobre placa clara
para validar **tamaño y composición**. Eso **no** es la TUI. En ratatui
no hay placa, no hay `<img>`: isotipo y wordmark se pintan con
half-blocks (`▀`/`▄`/`█`) sobre el fondo del HUD (`BG` / `Color::Reset`),
cubo a cubo, paleta bosque/menta del PNG. El damero del archivo
original no existe en terminal.

Pane de referencia: **~100 columnas × 12 filas** de terminal, de las
cuales **28 columnas** son BRAND y el resto DIALOGS. Si el pane es más
angosto de 90, BRAND baja a 22 cols y el wordmark se recorta a “mark
solo”.

## Paleta (del PNG, no neón)

| Rol | Hex | Nota |
|---|---|---|
| paper | `#F6F7F5` | fondo de la placa (el PNG nació sobre claro) |
| forest | `#03522E` | extrusión 3D del voxel |
| forest-deep | `#06331C` | sombra |
| mint | `#8FDCB0` | estantes inferiores |
| mint-soft | `#AEE8C6` | acento suave |
| mint-pale | `#C8F0DC` | highlight |
| text | `#E4EDE7` | texto de diálogos |
| muted | `#8A9E93` | labels |
| bg | `#0C1410` | fondo de diálogos |
| border | `#2A4A3A` | reglas |
| accent | `#3D6B54` | borde de botón |

Prohibido en v1: `#34D399`, `#10B981` y cualquier glow cian eléctrico.

## Rects relativos al HUD (cols × filas, origen arriba-izq)

```
BRAND       ( 0, 0, 28, 12)   mismo BG que DIALOGS; sin placa
MARK        ( 1, 0, 26,  9)   isotipo en half-blocks (PixelMap)
WORD        ( 1, 9, 26,  3)   wordmark en half-blocks
DIVIDER     (28, 0,  1, 12)   línea forest sutil o nada
DIALOGS     (30, 0, 70, 12)   todo lo demás

dentro de DIALOGS (x relativo a col 30):
  EYEBROW   ( 0, 0, 40, 1)   "COMPANION"
  AGENT     (50, 0, 20, 1)   "pi idle" a la derecha
  META      ( 0, 1, 70, 1)
  RULE_1    ( 0, 2, 70, 1)
  PROMPT    ( 0, 3, 52, 3)
  COPY      (54, 3, 16, 2)
  RULE_2    ( 0, 6, 70, 1)
  ACTION    ( 0, 7, 38, 1)
  APPROVE   (39, 7, 15, 1)
  SKIP      (55, 7, 15, 1)
  RULE_3    ( 0, 8, 70, 1)
  ASK       ( 0, 9, 70, 2)
```

## Estados del logo (RAM)

La placa **no cambia de paleta**. Idle = paper dusk + respiración suave
de brillo 0.92–1.0. Awake = paper pleno, sin atenuar. El PNG se muestra
siempre con sus colores reales.

## Copy (igual que v1 de producto)

Prompt idle:

```
descomponé el plan en tickets según la spec de auth;
no toques fuera de src/auth.
```

Higiene: `Validar documentos del vault`

Ask: `preguntale a Cortex`

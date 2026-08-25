# Implementación definitiva del logo de Cortex en Rust

## Contexto

Tenemos definida y aprobada la nueva identidad visual de **Cortex**.

A partir de este momento **no debes rediseñar, reinterpretar conceptualmente ni proponer otro logo**.

El logo visual aprobado es la imagen de referencia adjunta/proporcionada junto con esta tarea.

La tarea consiste exclusivamente en:

> **Traducir el logo aprobado de Cortex a una representación terminal-native de alta calidad, implementada en Rust, pensada específicamente para las TUI de Cortex.**

La referencia estética para la forma en la que debe verse dentro de una terminal es **Gentleman.Dots**:

* arte grande y reconocible;
* centrado;
* limpio;
* pocos colores;
* excelente uso del espacio negativo;
* sensación de producto diseñado específicamente para terminal;
* no un PNG pegado dentro de una terminal;
* no ASCII art tradicional.

La referencia Gentleman.Dots es solamente una referencia de **calidad de presentación y filosofía visual**.

No debes copiar su logo.

---

# 1. IDENTIDAD VISUAL DEFINITIVA

El logo de Cortex aprobado está formado por dos elementos:

1. **Isotipo**
2. **Wordmark `Cortex`**

El isotipo tiene una forma específica que debe conservarse.

## Isotipo

Visualmente consiste en:

* una gran forma exterior similar a una `C`;
* geometría angular, no circular;
* aspecto hexagonal/tecnológico;
* abertura hacia la derecha;
* una `X` grande integrada en el centro;
* varias capas paralelas en el lateral izquierdo;
* esas capas deben sugerir:

  * memoria;
  * múltiples capas;
  * historial;
  * contexto acumulado;
  * persistencia.

La lectura conceptual es aproximadamente:

```text
C = Cortex / Context
X = punto de encuentro / intersección / contexto
capas = memoria acumulativa
```

Pero esto es solamente significado conceptual.

**No agregues literalmente estos elementos como texto o símbolos.**

La silueta existente del logo ya los representa.

---

# 2. NO CAMBIAR LA GEOMETRÍA

La imagen proporcionada es la referencia canónica.

Debes conservar:

* proporciones generales;
* forma de la C;
* X central;
* orientación;
* abertura;
* ángulos;
* capas izquierdas;
* relación de tamaño entre C y X.

No agregues:

* cerebro;
* circuitos;
* nodos;
* flechas;
* ojos;
* hexágonos adicionales;
* íconos;
* adornos;
* partículas;
* elementos decorativos.

El logo ya está cerrado.

---

# 3. PALETA DEFINITIVA

La identidad de Cortex pasa a ser **monocromática azul/cyan fría**.

Eliminar completamente cualquier:

* magenta;
* rosa;
* rojo;
* violeta dominante;
* naranja;
* verde.

Utilizar esta paleta como referencia oficial.

```text
CORTEX_ICE       #D9F4FF
CORTEX_LIGHT     #A9E3FF
CORTEX_CYAN      #55CAF7
CORTEX_BLUE      #209CEB
CORTEX_DEEP      #1167C4
CORTEX_SHADOW    #0B3158
```

Texto principal:

```text
CORTEX_TEXT      #D9F4FF
```

Texto secundario:

```text
CORTEX_MUTED     #6E899B
```

Background de referencia:

```text
CORTEX_BG        #050A10
```

Pero atención:

**no debes obligatoriamente pintar toda la terminal con `CORTEX_BG`.**

Cuando Cortex corre sobre una terminal normal, debe respetarse preferentemente el background del usuario.

El negro/azul oscuro se utilizará en demos, previews o cuando una screen específica de Cortex decida usar fondo propio.

---

# 4. GRADIENTE DEL LOGO

La versión aprobada tiene una sensación de:

```text
hielo / blanco azulado
        ↓
cyan
        ↓
azul eléctrico
```

No quiero un gradiente arcoíris.

No quiero múltiples tonos llamativos.

Debe sentirse como una sola familia cromática.

La distribución aproximada puede ser:

```text
          ICE / LIGHT
             ↓
       ┌──────────┐
      /            \
     /              \     CYAN
    │
    │
    │     X → LIGHT/CYAN
    │
     \
      \____________ BLUE
```

Las capas izquierdas pueden utilizar tonos ligeramente más profundos para reforzar profundidad:

```text
capa superior    LIGHT
capa 2           CYAN
capa 3           BLUE
capa inferior    DEEP
```

No exagerar esta diferencia.

---

# 5. ESTÉTICA TERMINAL

La implementación NO debe intentar reproducir:

* metal;
* reflejos 3D;
* glossy;
* bevels;
* texturas raster;
* sombras complejas.

La terminal debe presentar una versión más limpia del logo.

Pensar en:

> **el mismo logo convertido en pixel art premium para terminal.**

El acabado debe ser:

* limpio;
* plano;
* ligeramente luminoso;
* muy legible;
* geométrico;
* preciso.

---

# 6. PROHIBIDO ASCII ART TRADICIONAL

No debes construir el logo utilizando principalmente:

```text
/
\
_
-
(
)
|
.
,
```

No quiero algo parecido a:

```text
        ______
      /        \
     /   \  /   \
    |     \/     |
```

Eso está explícitamente descartado.

---

# 7. TÉCNICA DE RENDER DEFINITIVA

La implementación preferida es **half-block pixel rendering**.

Utilizar principalmente el carácter Unicode:

```text
▀
```

Una celda de terminal debe representar dos píxeles verticales.

Conceptualmente:

```text
┌─────────────┐
│ pixel TOP   │ ← foreground
├─────────────┤
│ pixel BOTTOM│ ← background
└─────────────┘
```

mediante:

```text
▀
```

Esto permite duplicar aproximadamente la resolución vertical disponible.

---

# 8. REPRESENTACIÓN INTERNA

No almacenar el logo como un `String` ASCII gigante.

Implementar una representación lógica de pixels.

Por ejemplo:

```rust
#[derive(Clone, Copy)]
pub enum LogoPixel {
    Transparent,
    Ice,
    Light,
    Cyan,
    Blue,
    Deep,
    Shadow,
}
```

O una estructura equivalente.

También puede utilizarse:

```rust
#[derive(Clone, Copy)]
pub struct LogoPixel {
    pub color: Option<Rgb>,
}
```

Pero prefiero separar:

```text
forma
```

de:

```text
color
```

si eso simplifica mantener el branding.

---

# 9. ALTERNATIVA RECOMENDADA: MASK + GRADIENT

Una implementación especialmente buena sería guardar principalmente una **máscara del logo**.

Por ejemplo:

```rust
enum PixelKind {
    Transparent,
    Mark,
    Layer,
    Highlight,
    Shadow,
}
```

y calcular el color según:

```text
posición X
posición Y
región
```

Esto permite cambiar el gradiente sin volver a dibujar todo el logo.

Ejemplo conceptual:

```rust
fn logo_color(
    kind: PixelKind,
    x: usize,
    y: usize,
    width: usize,
    height: usize,
) -> Color
```

No es obligatorio usar exactamente esta API, pero sí separar razonablemente:

```text
GEOMETRY
   ↓
COLOR
   ↓
TERMINAL RENDER
```

---

# 10. HALF-BLOCK RENDERER

La lógica debe contemplar correctamente las cuatro posibilidades.

## Ambos pixels transparentes

```text
TOP    transparent
BOTTOM transparent
```

No pintar nada.

---

## Sólo superior

```text
TOP    cyan
BOTTOM transparent
```

Renderizar:

```text
▀
```

con:

```text
foreground = cyan
background = Reset
```

---

## Sólo inferior

```text
TOP    transparent
BOTTOM cyan
```

Renderizar:

```text
▄
```

con:

```text
foreground = cyan
background = Reset
```

---

## Ambos ocupados

```text
TOP    light_blue
BOTTOM blue
```

Renderizar:

```text
▀
```

con:

```text
foreground = light_blue
background = blue
```

---

## Ambos del mismo color

Opcionalmente puede optimizarse usando:

```text
█
```

aunque no es obligatorio.

---

# 11. RATATUI

La implementación debe integrarse directamente con:

```text
ratatui
+
crossterm
```

No quiero un renderer externo que imprima ANSI sin integrarse con el resto de la aplicación.

Debe poder renderizar directamente sobre:

```rust
Frame
```

o:

```rust
Buffer
```

de Ratatui.

---

# 12. API DESEADA

Quiero terminar pudiendo hacer algo conceptualmente parecido a:

```rust
render_cortex_logo(
    frame,
    area,
    LogoVariant::Full,
);
```

o:

```rust
let logo = CortexLogo::new(LogoVariant::Full);

frame.render_widget(logo, area);
```

Preferencia:

**hacerlo como Widget reutilizable de Ratatui**.

Por ejemplo:

```rust
pub struct CortexLogo {
    variant: LogoVariant,
}
```

y:

```rust
impl Widget for CortexLogo
```

si arquitectónicamente resulta limpio.

---

# 13. VARIANTES

Deben existir mínimo tres variantes.

```rust
pub enum LogoVariant {
    Full,
    Compact,
    Mark,
}
```

---

# 14. FULL

La variante `Full` será utilizada principalmente en:

* splash;
* onboarding;
* setup;
* empty states grandes;
* README screenshots.

Debe mostrar:

```text
          ISOTIPO GRANDE


            Cortex
```

Opcionalmente:

```text
Memory · Governance · Context
```

cuando la screen lo solicite.

La tagline **no forma parte del logo**.

Debe ser un componente separado.

---

# 15. TAMAÑO FULL

Objetivo aproximado del isotipo:

```text
44–54 columnas
```

por:

```text
16–22 filas terminales
```

Recordar que gracias al half-block renderer eso representa aproximadamente:

```text
44–54 pixels horizontales
32–44 pixels verticales
```

de información visual.

No utilizar automáticamente el máximo.

Debe mantener espacio negativo alrededor.

---

# 16. COMPACT

Utilizada cuando la pantalla tiene menos espacio.

Objetivo:

```text
26–34 columnas
```

por:

```text
10–14 filas
```

Debe conservar:

* C;
* X;
* capas.

Puede eliminar:

* pequeños highlights;
* glow;
* detalles secundarios.

---

# 17. MARK

Es el isotipo utilizado dentro de headers.

Debe ser extremadamente pequeño.

Aproximadamente:

```text
8–14 columnas
```

por:

```text
4–7 filas
```

No intentar conservar cada detalle.

Debe conservar principalmente:

```text
C
+
X
+
una pequeña insinuación de layers
```

Si las capas dejan de leerse correctamente, utilizar solamente una.

---

# 18. BREAKPOINTS

Implementar una función centralizada.

Por ejemplo:

```rust
pub enum BrandingMode {
    Full,
    Compact,
    Minimal,
}
```

con:

```rust
pub fn branding_mode(area: Rect) -> BrandingMode
```

Referencia inicial:

```text
width >= 90 && height >= 28
    → Full

width >= 55 && height >= 18
    → Compact

else
    → Minimal
```

No hardcodear estas decisiones por toda la aplicación.

---

# 19. CENTRADO

Al igual que la referencia Gentleman.Dots, el branding debe tener excelente composición.

El logo debe poder centrarse:

```text
horizontalmente
+
verticalmente
```

dentro del área disponible.

Nunca asumir:

```text
x = 0
y = 0
```

El widget debe recibir un `Rect`.

---

# 20. WORDMARK

El wordmark:

```text
Cortex
```

debe conservar una estética:

* monoespaciada;
* geométrica;
* técnica;
* ligeramente espaciada;
* sobria.

No utilizar una fuente externa.

No depender de la fuente gráfica original.

Hay dos opciones aceptables.

## Opción A — recomendable

Crear un pequeño wordmark pixel-art propio:

```text
C O R T E X
```

basado en una grilla controlada por nosotros.

Ejemplo de resolución lógica:

```text
5x7
```

o:

```text
6x8
```

por letra.

Después renderizarlo usando el mismo renderer del logo.

Esto garantiza que el branding se vea igual independientemente de la terminal.

---

## Opción B

Para `Compact` y `Minimal`, utilizar texto normal:

```text
CORTEX
```

con:

```rust
Style::default()
    .fg(CORTEX_LIGHT)
    .add_modifier(Modifier::BOLD)
```

---

# 21. PREFERENCIA PARA FULL

Para `Full`, prefiero que el wordmark también tenga una representación controlada, no simplemente:

```rust
Paragraph::new("Cortex")
```

Debe sentirse parte de la composición.

---

# 22. GLOW

La referencia visual tiene glow.

Pero una terminal no soporta blur real.

No intentar simular un bloom complejo.

Utilizar como máximo:

* una pequeña capa periférica;
* pixels `Shadow`;
* azul oscuro;
* baja intensidad.

Por ejemplo:

```text
     shadow
       ↓
    ░█████░
   █████████
```

Pero no llenar todo de sombras.

El logo debe seguir viéndose bien incluso sin glow.

---

# 23. NO USAR `░▒▓` COMO BASE DEL LOGO

Estos caracteres pueden utilizarse puntualmente si realmente aportan.

Pero el renderer principal debe ser:

```text
▀
▄
█
```

con colores.

Eso nos da un resultado más limpio y cercano a auténtico pixel art.

---

# 24. TRUECOLOR

Cortex debe aprovechar TrueColor.

Utilizar:

```rust
Color::Rgb(r, g, b)
```

cuando corresponda.

La implementación debe asumir TrueColor como experiencia ideal.

---

# 25. FALLBACK

No debe romperse en terminales limitadas.

Si existe infraestructura para detectar capacidades, proporcionar fallback a una paleta reducida.

Por ejemplo:

```text
Ice   → Cyan
Light → LightCyan
Cyan  → Cyan
Blue  → Blue
Deep  → DarkGray
```

No es necesario sacrificar toda la arquitectura para esto, pero el renderer debe permitirlo.

---

# 26. FONDO

Extremadamente importante:

**NO pintar automáticamente todo el fondo de negro.**

El isotipo debe poder renderizarse con:

```rust
Color::Reset
```

como fondo.

Esto permite que se vea correctamente en:

* Ghostty;
* Kitty;
* WezTerm;
* Alacritty;
* Windows Terminal;
* terminales con transparencia;
* terminales con wallpapers;
* temas personalizados.

El splash puede decidir utilizar un background oscuro.

El logo no.

---

# 27. ESTRUCTURA DE ARCHIVOS

La arquitectura recomendada es:

```text
src/
└── ui/
    ├── mod.rs
    ├── theme.rs
    │
    ├── branding/
    │   ├── mod.rs
    │   ├── logo.rs
    │   ├── pixels.rs
    │   ├── renderer.rs
    │   ├── palette.rs
    │   └── wordmark.rs
    │
    └── screens/
        └── splash.rs
```

---

# 28. `palette.rs`

Debe concentrar toda la identidad de color.

Por ejemplo:

```rust
pub const ICE: Color =
    Color::Rgb(217, 244, 255);

pub const LIGHT: Color =
    Color::Rgb(169, 227, 255);

pub const CYAN: Color =
    Color::Rgb(85, 202, 247);

pub const BLUE: Color =
    Color::Rgb(32, 156, 235);

pub const DEEP: Color =
    Color::Rgb(17, 103, 196);

pub const SHADOW: Color =
    Color::Rgb(11, 49, 88);
```

No repetir colores hardcodeados en otros archivos.

---

# 29. `pixels.rs`

Responsable de:

```text
PixelKind
PixelMap
logical dimensions
pixel access
```

Ejemplo conceptual:

```rust
#[derive(Clone, Copy, PartialEq, Eq)]
pub enum PixelKind {
    Transparent,
    Mark,
    Layer,
    Highlight,
    Shadow,
}
```

---

# 30. `logo.rs`

Debe contener:

```text
FULL_MASK
COMPACT_MASK
MARK_MASK
```

o estructuras equivalentes.

La geometría pertenece aquí.

No mezclarla con:

* terminal;
* eventos;
* layout general;
* lógica de aplicación.

---

# 31. `renderer.rs`

Responsable únicamente de convertir:

```text
logical pixels
```

en:

```text
Ratatui cells
```

usando:

```text
▀
▄
█
```

---

# 32. `wordmark.rs`

Responsable del:

```text
Cortex
```

visual.

Debe ser completamente independiente del isotipo.

---

# 33. `branding/mod.rs`

Debe exponer una API simple.

Por ejemplo:

```rust
pub use logo::{
    CortexLogo,
    LogoVariant,
};

pub use palette::CortexPalette;

pub use wordmark::CortexWordmark;
```

---

# 34. NO DUPLICAR EL LOGO

No quiero encontrar:

```text
splash_logo
header_logo
doctor_logo
setup_logo
```

como cuatro implementaciones diferentes.

Debe existir:

```text
UNA identidad
```

con:

```text
VARIANTES
```

---

# 35. FUENTE DE VERDAD

La imagen aprobada proporcionada junto a esta tarea es la referencia visual.

Una vez implementada la geometría terminal:

```text
Rust source
```

debe convertirse en la fuente de verdad del branding TUI.

No cargar el PNG en runtime.

---

# 36. OPCIONAL: GENERADOR DE DESARROLLO

Si considerás útil automatizar parte del proceso, puede existir:

```text
tools/
    logo_codegen/
```

o:

```text
xtask/
```

que tome la imagen aprobada y produzca una representación inicial.

En ese caso:

* `image` puede ser dependencia de desarrollo;
* NO debe quedar como dependencia del binario final;
* NO debe cargarse ninguna imagen cuando Cortex se ejecuta.

Esto es opcional.

---

# 37. IMPORTANTE SOBRE LA CONVERSIÓN AUTOMÁTICA

Si generás automáticamente una versión a partir del PNG:

**NO aceptes ciegamente el resultado.**

Debes limpiar manualmente:

* bordes;
* ruido;
* antialiasing;
* pequeñas manchas;
* irregularidades;
* detalles imposibles de leer.

El resultado terminal debe ser una reinterpretación deliberada.

No una captura pixelada.

---

# 38. SILUETA

Esta es una de las condiciones más importantes.

Si renderizo el logo en un solo color:

```text
████████
```

la forma debe seguir siendo identificable como Cortex.

La identidad no puede depender del gradiente.

El gradiente es secundario.

---

# 39. JERARQUÍA VISUAL

La importancia debe ser:

```text
1. silueta C
2. X
3. layers
4. gradiente
5. highlights
6. glow
```

Si tenés que eliminar algo por falta de espacio, eliminar desde abajo hacia arriba.

---

# 40. LAYERS

Las capas izquierdas son especialmente importantes porque diferencian el símbolo de un simple:

```text
CX
```

Deben sentirse como una continuación de la estructura.

No convertirlas en:

```text
tres líneas aleatorias
```

La capa más inferior conecta visualmente con el segmento inferior de la C.

---

# 41. X

La X debe:

* estar centrada;
* ser grande;
* tener bastante espacio negativo alrededor;
* no tocar la C;
* tener grosor similar a la estructura principal;
* sentirse integrada pero independiente.

No transformarla en:

```text
x
```

tipográfica.

Es una forma geométrica.

---

# 42. ESPACIO NEGATIVO

Parte de por qué Gentleman.Dots funciona visualmente es el aire alrededor del logo.

No llenar la pantalla.

Por ejemplo:

```text



                   [ CORTEX LOGO ]



                      CORTEX


```

es mejor que:

```text
████████████████████████████████
████████████LOGO████████████████
████████████████████████████████
```

La composición debe respirar.

---

# 43. SPLASH SCREEN

Crear una demo funcional.

Visualmente debe tender hacia:

```text


                 [ ISOTIPO ]


                   CORTEX

          Memory · Governance · Context


```

Nada más.

Opcionalmente abajo:

```text
vX.Y.Z
```

o:

```text
Press Enter to continue
```

pero debe pertenecer a la screen, no al logo.

---

# 44. RESPONSIVE

La demo debe poder redimensionarse en tiempo real.

Al cambiar las dimensiones de terminal:

```text
Full
   ↓
Compact
   ↓
Minimal
```

sin romper el layout.

---

# 45. TESTS

Utilizar:

```rust
ratatui::backend::TestBackend
```

para comprobar mínimo:

### Full

```text
terminal grande
```

### Compact

```text
terminal mediana
```

### Minimal

```text
terminal pequeña
```

Comprobar:

* no panic;
* no escritura fuera del área;
* dimensiones correctas;
* variante correcta.

---

# 46. TEST DE GEOMETRÍA

Agregar tests independientes para comprobar:

```text
FULL_WIDTH
FULL_HEIGHT
COMPACT_WIDTH
COMPACT_HEIGHT
MARK_WIDTH
MARK_HEIGHT
```

y consistencia de los arrays/masks.

---

# 47. RENDIMIENTO

El logo es estático.

No recalcular:

* geometría;
* máscaras;
* palettes;
* gradientes complejos;

innecesariamente en cada frame.

Todo lo posible debe ser:

```rust
const
```

o computarse una sola vez.

---

# 48. NO ANIMAR POR AHORA

No agregar:

* pulsos;
* breathing;
* blinking;
* partículas;
* scanlines;
* glitch;
* movimiento del gradiente.

La primera versión debe ser completamente estática.

Si algún día agregamos animación, será una tarea independiente.

---

# 49. NO SOBREINGENIERIZAR

Quiero una implementación robusta.

No quiero una mini-engine gráfica.

No introducir:

* shaders;
* OpenGL;
* wgpu;
* image protocols;
* sixel;
* kitty graphics protocol.

Esta es una TUI.

La gracia es conseguir una identidad visual fuerte utilizando las capacidades normales de una terminal.

---

# 50. CRITERIO FINAL

Cuando termine la implementación, quiero que al abrir Cortex exista la misma sensación que produce Gentleman.Dots:

> “Esto no parece una CLI a la que después le pusieron colores. Parece un producto diseñado específicamente para vivir en una terminal.”

Pero debe tener identidad completamente propia.

Esa identidad es:

```text
CORTEX
```

con:

```text
C angular
+
X central
+
memory layers
+
ice/cyan/blue
+
dark terminal
+
minimalismo
```

---

# 51. ENTREGABLE

Implementá el código.

Al finalizar quiero que informes únicamente:

1. archivos creados;
2. archivos modificados;
3. arquitectura elegida;
4. dimensiones finales de `Full`, `Compact` y `Mark`;
5. paleta final;
6. cómo probar el splash;
7. cualquier diferencia que haya sido necesaria respecto de la imagen original.

No vuelvas a discutir qué logo elegir.

**El diseño ya está aprobado.**

Tu tarea es convertirlo en una identidad TUI de Cortex en Rust con la máxima fidelidad y calidad posible.

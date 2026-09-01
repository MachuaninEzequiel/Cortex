//! Representación lógica de píxeles del branding (prompt §8-9).
//!
//! Separa GEOMETRÍA (máscaras en `logo.rs`) de COLOR (`gradient.rs`): la
//! máscara dice qué clase de píxel hay en cada celda; el gradiente decide el
//! color según posición y clase. El render (`ansi.rs` o el widget de
//! `cortex-tui`) convierte eso a terminal.

/// Clase lógica de un píxel del isotipo.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum PixelKind {
    /// Fuera del logo (fondo del usuario, jamás se pinta).
    Transparent,
    /// Estructura principal de la C (cuñas, pared, garras).
    Mark,
    /// La X central (color propio: LIGHT→CYAN).
    Cross,
    /// Capas de memoria del lateral izquierdo.
    Layer,
    /// Puntos de brillo (borde superior, puntas de las garras).
    Highlight,
    /// Glow periférico calculado (solo Full, borde exterior).
    Shadow,
}

/// Grilla lógica de píxeles con dimensiones y acceso O(1).
#[derive(Clone, PartialEq, Eq, Debug)]
pub struct PixelMap {
    w: usize,
    h: usize,
    cells: Vec<PixelKind>,
}

impl PixelMap {
    pub fn new(w: usize, h: usize) -> Self {
        Self {
            w,
            h,
            cells: vec![PixelKind::Transparent; w * h],
        }
    }

    /// Parsea filas de texto donde cada char es un píxel:
    /// `' '`|`'.'` transparente · `'#'` mark · `'X'` cross · `'L'` layer ·
    /// `'H'` highlight · `'S'` shadow. El ancho es el de la fila más larga;
    /// las filas cortas se paddean con transparente (permite máscaras embebidas
    /// sin espacios finales). Panic ruidoso ante chars desconocidos: es un bug
    /// de la máscara, no dato de entrada.
    pub fn parse(rows: &[&str]) -> Self {
        let h = rows.len();
        assert!(h > 0, "máscara vacía");
        let w = rows.iter().map(|r| r.chars().count()).max().unwrap_or(0);
        let mut map = Self::new(w, h);
        for (y, row) in rows.iter().enumerate() {
            for (x, ch) in row.chars().enumerate() {
                *map.get_mut(x, y) = PixelKind::from_char(ch);
            }
        }
        map
    }

    pub fn w(&self) -> usize {
        self.w
    }

    pub fn h(&self) -> usize {
        self.h
    }

    pub fn get(&self, x: usize, y: usize) -> PixelKind {
        self.cells[y * self.w + x]
    }

    pub fn get_mut(&mut self, x: usize, y: usize) -> &mut PixelKind {
        &mut self.cells[y * self.w + x]
    }

    pub fn count(&self, kind: PixelKind) -> usize {
        self.cells.iter().filter(|k| **k == kind).count()
    }

    /// Copia los píxeles no transparentes de `other` sobre `self` en el
    /// offset dado (para componer logo + wordmark, banners, etc.).
    pub fn blit(&mut self, other: &PixelMap, ox: usize, oy: usize) {
        for y in 0..other.h() {
            for x in 0..other.w() {
                let kind = other.get(x, y);
                if kind != PixelKind::Transparent {
                    let (tx, ty) = (ox + x, oy + y);
                    if tx < self.w() && ty < self.h() {
                        *self.get_mut(tx, ty) = kind;
                    }
                }
            }
        }
    }

    /// Agrega glow periférico (prompt §22): celdas transparentes del EXTERIOR
    /// adyacentes (8-vecindad) al CUERPO PRINCIPAL (Mark/Cross/Highlight)
    /// pasan a `Shadow`. Las capas no emanan glow (los huecos entre slabs se
    /// llenarían) y el interior de la C queda limpio: el glow es periférico.
    pub fn dilate_exterior_shadow(&mut self) {
        let (w, h) = (self.w, self.h);
        let exterior = self.exterior_transparent();
        let emanates =
            |k: PixelKind| matches!(k, PixelKind::Mark | PixelKind::Cross | PixelKind::Highlight);
        let mut shadows = Vec::new();
        for y in 0..h {
            for x in 0..w {
                if self.get(x, y) != PixelKind::Transparent || !exterior[y * w + x] {
                    continue;
                }
                let touches = (-1i32..=1).any(|dy| {
                    (-1i32..=1).any(|dx| {
                        let nx = x as i32 + dx;
                        let ny = y as i32 + dy;
                        if nx < 0 || ny < 0 || nx >= w as i32 || ny >= h as i32 {
                            return false;
                        }
                        emanates(self.get(nx as usize, ny as usize))
                    })
                });
                if touches {
                    shadows.push((x, y));
                }
            }
        }
        for (x, y) in shadows {
            *self.get_mut(x, y) = PixelKind::Shadow;
        }
    }

    /// Flood fill desde los bordes: marca las celdas transparentes alcanzables
    /// desde afuera (para no pintar glow dentro de la cavidad de la C).
    fn exterior_transparent(&self) -> Vec<bool> {
        let (w, h) = (self.w, self.h);
        let mut seen = vec![false; w * h];
        let mut stack: Vec<(usize, usize)> = Vec::new();
        for x in 0..w {
            for y in [0, h - 1] {
                if self.get(x, y) == PixelKind::Transparent && !seen[y * w + x] {
                    seen[y * w + x] = true;
                    stack.push((x, y));
                }
            }
        }
        for y in 0..h {
            for x in [0, w - 1] {
                if self.get(x, y) == PixelKind::Transparent && !seen[y * w + x] {
                    seen[y * w + x] = true;
                    stack.push((x, y));
                }
            }
        }
        while let Some((x, y)) = stack.pop() {
            for (dx, dy) in [(-1i32, 0i32), (1, 0), (0, -1), (0, 1)] {
                let nx = x as i32 + dx;
                let ny = y as i32 + dy;
                if nx < 0 || ny < 0 || nx >= w as i32 || ny >= h as i32 {
                    continue;
                }
                let (nx, ny) = (nx as usize, ny as usize);
                if self.get(nx, ny) == PixelKind::Transparent && !seen[ny * w + nx] {
                    seen[ny * w + nx] = true;
                    stack.push((nx, ny));
                }
            }
        }
        seen
    }
}

impl PixelKind {
    pub fn from_char(ch: char) -> Self {
        match ch {
            ' ' | '.' => PixelKind::Transparent,
            '#' => PixelKind::Mark,
            'X' => PixelKind::Cross,
            'L' => PixelKind::Layer,
            'H' => PixelKind::Highlight,
            'S' => PixelKind::Shadow,
            other => panic!("char de máscara desconocido: {other:?}"),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parse_roundtrip() {
        let map = PixelMap::parse(&[" #X", "LHS"]);
        assert_eq!(map.w(), 3);
        assert_eq!(map.h(), 2);
        assert_eq!(map.get(0, 0), PixelKind::Transparent);
        assert_eq!(map.get(1, 0), PixelKind::Mark);
        assert_eq!(map.get(2, 0), PixelKind::Cross);
        assert_eq!(map.get(0, 1), PixelKind::Layer);
        assert_eq!(map.get(1, 1), PixelKind::Highlight);
        assert_eq!(map.get(2, 1), PixelKind::Shadow);
    }

    #[test]
    fn shadow_solo_exterior() {
        // La cavidad (celda rodeada por dentro) NO recibe glow; solo el
        // perímetro exterior adyacente a la forma.
        let mut map = PixelMap::parse(&[
            "          ",
            " ######   ",
            " #....#   ",
            " #....#   ",
            " ######   ",
            "          ",
        ]);
        map.dilate_exterior_shadow();
        // Interior: transparente limpio.
        assert_eq!(map.get(3, 2), PixelKind::Transparent);
        assert_eq!(map.get(4, 3), PixelKind::Transparent);
        // Exterior adyacente (incluida diagonal): shadow.
        assert_eq!(map.get(0, 0), PixelKind::Shadow);
        assert_eq!(map.get(7, 2), PixelKind::Shadow);
        // Exterior lejano: transparente.
        assert_eq!(map.get(9, 0), PixelKind::Transparent);
    }

    #[test]
    fn filas_cortas_se_paddean() {
        let map = PixelMap::parse(&["###", "#"]);
        assert_eq!(map.w(), 3);
        assert_eq!(map.get(2, 1), PixelKind::Transparent);
    }

    #[test]
    fn blit_copia_solo_lo_opaco() {
        let mut base = PixelMap::parse(&["....", "...."]);
        // Patch 3-wide: fila inferior con hueco transparente que NO debe
        // pisar lo ya existente (base(2,1) queda Transparent) y un Mark
        // final que cae en base(3,1).
        let patch = PixelMap::parse(&["##", "# #"]);
        base.blit(&patch, 1, 0);
        assert_eq!(base.get(1, 0), PixelKind::Mark);
        assert_eq!(base.get(2, 0), PixelKind::Mark);
        assert_eq!(base.get(2, 1), PixelKind::Transparent); // transparente no pisa
        assert_eq!(base.get(3, 1), PixelKind::Mark);
    }
}

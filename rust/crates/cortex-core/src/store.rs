//! Store vectorial binario propio (Gate G2) — reemplazo de chunks.bin/index.json.
//!
//! Problemas del esquema Python previo (03-MIGRACION-RUST §2.2):
//! - `_read_vector_at`: open/seek/read/close POR vector → O(N) syscalls por carga.
//! - `_save_index`: re-serializa el índice JSON COMPLETO en cada put/invalidate
//!   → O(N) por operación, **O(N²)** acumulado sobre ingesta masiva.
//!
//! Diseño nuevo — log append-only de UN solo archivo (`vectors.v3.bin`):
//!
//! ```text
//! header:  magic[8] = b"CCTXV3\0\0" · model_len u32LE · model_name utf8
//! records (hasta EOF):
//!   PUT:       tag=u8(1) · klen u32LE · fingerprint · clen u32LE ·
//!              chunk_id utf8 · vlen u32LE · dim × f32 LE
//!   TOMBSTONE: tag=u8(2) · klen u32LE · fingerprint
//! ```
//!
//! - Carga: UNA lectura secuencial del archivo → índice en memoria.
//! - Ingesta: append puro por lote → amortizado O(1) por vector, sin reescrituras.
//! - Invalidación: tombstone appended; espacio se recupera con `compact()`
//!   (mismas semánticas de leak-hasta-compact que el cache Python).
//! - Cola truncada por crash: prefijo válido conservado con WARNING en el
//!   binding — jamás servir datos dudosos como frescos (riesgo R8).
//! - dim SIEMPRE paramétrica: inferida del primer vector y validada después
//!   (lección vector_cache.py:41 / Fix A1). Mismatch = falla ruidosa.
//!
//! Los fingerprints los calcula Python (`cache_fingerprint`): acá son claves
//! opacas → paridad de fingerprints por construcción.

use std::collections::HashMap;
use std::fmt;
use std::fs::{File, OpenOptions};
use std::io::{BufWriter, Read, Write};
use std::path::{Path, PathBuf};

/// Marca + versión de formato (schema v3 del programa de transformación).
const MAGIC: [u8; 8] = *b"CCTXV3\0\0";
const TAG_PUT: u8 = 1;
const TAG_TOMBSTONE: u8 = 2;
pub const STORE_FILENAME: &str = "vectors.v3.bin";

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum StoreError {
    Io(String),
    Corrupted(String),
    DimMismatch { expected: usize, got: usize },
    LengthMismatch { detail: String },
}

impl fmt::Display for StoreError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Io(m) => write!(f, "IO del store vectorial: {m}"),
            Self::Corrupted(m) => write!(f, "store corrupto/truncado: {m}"),
            Self::DimMismatch { expected, got } => {
                write!(
                    f,
                    "vector dim={got} != dim del store={expected} (falla ruidosa)"
                )
            }
            Self::LengthMismatch { detail } => write!(f, "{detail}"),
        }
    }
}

impl std::error::Error for StoreError {}

fn io_err<E: std::fmt::Display>(e: E) -> StoreError {
    StoreError::Io(e.to_string())
}

fn truncado() -> StoreError {
    StoreError::Io("truncado".into())
}

/// Entrada viva del índice en memoria.
struct Entry {
    row: usize, // fila dentro del arena
}

/// Store vectorial persistente append-only.
///
/// Estado en memoria: arena contigua de filas f32 + índice fp→fila + chunk_ids
/// alineados. Los fps re-puteados dejan la fila vieja como basura hasta
/// `compact()` (igual que el cache Python original).
pub struct VectorStore {
    file_path: PathBuf,
    model_name: String,
    dim: Option<usize>,
    arena: Vec<f32>,
    chunk_ids: Vec<String>, // alineado con filas vivas del arena
    index: HashMap<String, Entry>,
    /// True si la carga encontró cola truncada/corrupta y conservó el prefijo válido.
    pub truncated_tail: bool,
}

impl VectorStore {
    /// Abre (o crea) el store en ``dir`` para el modelo dado.
    ///
    /// Si el archivo existe con OTRO model_name se resetea: vectores de otro
    /// modelo jamás se reutilizan (paridad con Fix A3 del cache Python).
    pub fn open(dir: &Path, model_name: &str) -> Result<Self, StoreError> {
        std::fs::create_dir_all(dir).map_err(io_err)?;
        let file_path = dir.join(STORE_FILENAME);
        let mut store = Self {
            file_path,
            model_name: model_name.to_string(),
            dim: None,
            arena: Vec::new(),
            chunk_ids: Vec::new(),
            index: HashMap::new(),
            truncated_tail: false,
        };
        if store.file_path.exists() {
            store.load_existing()?;
        } else {
            store.init_file()?;
        }
        Ok(store)
    }

    fn init_file(&self) -> Result<(), StoreError> {
        let f = File::create(&self.file_path).map_err(io_err)?;
        let mut w = BufWriter::new(f);
        write_header(&mut w, &self.model_name)?;
        w.flush().map_err(io_err)?;
        Ok(())
    }

    fn load_existing(&mut self) -> Result<(), StoreError> {
        let mut buf = Vec::new();
        File::open(&self.file_path)
            .map_err(io_err)?
            .read_to_end(&mut buf)
            .map_err(io_err)?;

        if buf.len() < 12 || buf[..8] != MAGIC {
            // Header roto: reset total (paridad con _reset_corrupt del cache Python).
            self.init_file()?;
            return Ok(());
        }
        let mut hpos = 0;
        let model = read_str(&buf[8..], &mut hpos)
            .ok_or_else(|| StoreError::Corrupted("header incompleto".into()))?;
        if model != self.model_name {
            self.init_file()?;
            return Ok(());
        }
        let mut pos = 8 + 4 + model.len();

        while pos < buf.len() {
            match parse_record(&buf, &mut pos, self.dim, &mut self.arena) {
                Ok(ParsedRecord::Put {
                    key,
                    chunk_id,
                    row_dim,
                }) => {
                    let dim = self.dim.get_or_insert(row_dim);
                    if *dim != row_dim {
                        return Err(StoreError::DimMismatch {
                            expected: *dim,
                            got: row_dim,
                        });
                    }
                    let row = self.arena.len() / row_dim - 1; // parse ya hizo push
                    self.chunk_ids.push(chunk_id);
                    self.index.insert(key, Entry { row });
                }
                Ok(ParsedRecord::Tombstone { key }) => {
                    if let Some(e) = self.index.remove(&key) {
                        self.chunk_ids[e.row] = String::new(); // hueco hasta compact()
                    }
                }
                Err(e) => {
                    // Cualquier error de parse en el log = cola inválida (crash
                    // durante append). Se conserva el prefijo válido y se marca
                    // la degradación para que el binding emita WARNING (R8):
                    // jamás silencioso, jamás servir la cola dudosa.
                    self.truncated_tail = true;
                    let _ = e;
                    break;
                }
            }
        }
        Ok(())
    }

    // ------------------------------------------------------------------
    // Consultas batch
    // ------------------------------------------------------------------

    pub fn dim(&self) -> Option<usize> {
        self.dim
    }

    pub fn len(&self) -> usize {
        self.index.len()
    }

    pub fn is_empty(&self) -> bool {
        self.index.is_empty()
    }

    /// Resuelve un lote de fingerprints contra el índice en memoria.
    ///
    /// Escribe en ``out_matrix`` (fila-major, `n × dim`) los vectores hallados
    /// y marca ``out_present[i]``. Ausentes → fila en cero + false.
    /// Store aún sin dim (vacío) ⇒ todo miss (paridad con cache Python vacío).
    /// API GRUESA: una llamada para TODO el lote.
    pub fn get_many(
        &self,
        fingerprints: &[String],
        out_matrix: &mut [f32],
        out_present: &mut [bool],
    ) -> Result<usize, StoreError> {
        if fingerprints.len() != out_present.len() {
            return Err(StoreError::LengthMismatch {
                detail: "get_many: out_present no alineado con fingerprints".into(),
            });
        }
        let Some(dim) = self.dim else {
            out_present.fill(false);
            out_matrix.fill(0.0);
            return Ok(0);
        };
        if out_matrix.len() != fingerprints.len() * dim {
            return Err(StoreError::LengthMismatch {
                detail: format!(
                    "get_many: out_matrix len={} != n={} × dim={}",
                    out_matrix.len(),
                    fingerprints.len(),
                    dim
                ),
            });
        }
        let mut hits = 0;
        for (i, fp) in fingerprints.iter().enumerate() {
            let dst = &mut out_matrix[i * dim..(i + 1) * dim];
            match self.index.get(fp) {
                Some(entry) => {
                    dst.copy_from_slice(&self.arena[entry.row * dim..(entry.row + 1) * dim]);
                    out_present[i] = true;
                    hits += 1;
                }
                None => {
                    dst.fill(0.0);
                    out_present[i] = false;
                }
            }
        }
        Ok(hits)
    }

    /// fps vivos cuyo chunk_id está EXACTAMENTE en el conjunto dado (batch).
    pub fn fps_for_chunk_ids(&self, chunk_ids: &[String]) -> Vec<String> {
        let targets: std::collections::HashSet<&String> = chunk_ids.iter().collect();
        self.index
            .iter()
            .filter(|(_, e)| targets.contains(&self.chunk_ids[e.row]))
            .map(|(fp, _)| fp.clone())
            .collect()
    }

    /// fps vivos cuyo chunk_id empieza con ``prefix`` (invalidación granular).
    pub fn fps_with_chunk_prefix(&self, prefix: &str) -> Vec<String> {
        self.index
            .iter()
            .filter(|(_, e)| self.chunk_ids[e.row].starts_with(prefix))
            .map(|(fp, _)| fp.clone())
            .collect()
    }

    /// Export batch de metadatos: (fps, chunk_ids) de entradas VIVAS.
    pub fn entries_export(&self) -> (Vec<String>, Vec<String>) {
        let mut fps = Vec::with_capacity(self.index.len());
        let mut cids = Vec::with_capacity(self.index.len());
        for (fp, e) in &self.index {
            fps.push(fp.clone());
            cids.push(self.chunk_ids[e.row].clone());
        }
        (fps, cids)
    }

    // ------------------------------------------------------------------
    // Escritura batch
    // ------------------------------------------------------------------

    /// Inserta un lote completo. Validación transaccional previa (todo-o-nada,
    /// paridad con Fix A2 del cache Python): si algo falla, nada se escribe.
    pub fn put_many(
        &mut self,
        fingerprints: &[String],
        chunk_ids: &[String],
        vectors: &[f32],
        dim: usize,
    ) -> Result<(), StoreError> {
        if dim == 0 {
            return Err(StoreError::DimMismatch {
                expected: 0,
                got: 0,
            });
        }
        if fingerprints.len() != chunk_ids.len() || fingerprints.len() * dim != vectors.len() {
            return Err(StoreError::LengthMismatch {
                detail: format!(
                    "put_many: fps={} chunk_ids={} valores={} no forman (n, {dim})",
                    fingerprints.len(),
                    chunk_ids.len(),
                    vectors.len()
                ),
            });
        }
        match self.dim {
            None => self.dim = Some(dim),
            Some(d) if d != dim => {
                return Err(StoreError::DimMismatch {
                    expected: d,
                    got: dim,
                });
            }
            _ => {}
        }

        // Append a disco: UNA apertura por lote (no una por vector).
        let mut file = OpenOptions::new()
            .append(true)
            .open(&self.file_path)
            .map_err(io_err)?;
        let mut w = BufWriter::new(&mut file);

        for (i, fp) in fingerprints.iter().enumerate() {
            let row_vec = &vectors[i * dim..(i + 1) * dim];
            write_record_put(&mut w, fp, &chunk_ids[i], row_vec)?;

            let row = self.arena.len() / dim;
            self.arena.extend_from_slice(row_vec);
            self.chunk_ids.push(chunk_ids[i].clone());
            self.index.insert(fp.clone(), Entry { row });
        }
        w.flush().map_err(io_err)?;
        Ok(())
    }

    /// Marca fps como inválidos (tombstones). Devuelve cuántos fueron nuevos.
    pub fn invalidate_many(&mut self, fingerprints: &[String]) -> Result<usize, StoreError> {
        let nuevos: Vec<&String> = fingerprints
            .iter()
            .filter(|fp| self.index.contains_key(*fp))
            .collect();
        if nuevos.is_empty() {
            return Ok(0);
        }
        let mut file = OpenOptions::new()
            .append(true)
            .open(&self.file_path)
            .map_err(io_err)?;
        let mut w = BufWriter::new(&mut file);
        for fp in &nuevos {
            write_record_tombstone(&mut w, fp)?;
        }
        w.flush().map_err(io_err)?;
        for fp in &nuevos {
            if let Some(e) = self.index.remove(*fp) {
                self.chunk_ids[e.row] = String::new();
            }
        }
        Ok(nuevos.len())
    }

    /// Reescribe el archivo solo con entradas vivas (tmp + rename atómico)
    /// y compacta el arena eliminando filas muertas. Devuelve entradas finales.
    pub fn compact(&mut self) -> Result<usize, StoreError> {
        let Some(dim) = self.dim else { return Ok(0) };
        let tmp_path = self.file_path.with_extension("tmp");
        {
            let f = File::create(&tmp_path).map_err(io_err)?;
            let mut w = BufWriter::new(f);
            write_header(&mut w, &self.model_name)?;

            let mut new_arena = Vec::with_capacity(self.index.len() * dim);
            let mut new_cids = Vec::with_capacity(self.index.len());
            let mut remap: HashMap<String, Entry> = HashMap::with_capacity(self.index.len());
            for (fp, e) in &self.index {
                let slice = &self.arena[e.row * dim..(e.row + 1) * dim];
                write_record_put(&mut w, fp, &self.chunk_ids[e.row], slice)?;
                let new_row = new_arena.len() / dim;
                new_arena.extend_from_slice(slice);
                new_cids.push(self.chunk_ids[e.row].clone());
                remap.insert(fp.clone(), Entry { row: new_row });
            }
            w.flush().map_err(io_err)?;

            self.arena = new_arena;
            self.chunk_ids = new_cids;
            self.index = remap;
        }
        std::fs::rename(&tmp_path, &self.file_path).map_err(io_err)?;
        Ok(self.index.len())
    }
}

// ----------------------------------------------------------------------
// Codificación binaria
// ----------------------------------------------------------------------

fn write_header<W: Write>(w: &mut W, model_name: &str) -> Result<(), StoreError> {
    w.write_all(&MAGIC).map_err(io_err)?;
    w.write_all(&(model_name.len() as u32).to_le_bytes())
        .map_err(io_err)?;
    w.write_all(model_name.as_bytes()).map_err(io_err)?;
    Ok(())
}

fn write_record_put<W: Write>(
    w: &mut W,
    fp: &str,
    chunk_id: &str,
    vec_row: &[f32],
) -> Result<(), StoreError> {
    w.write_all(&[TAG_PUT]).map_err(io_err)?;
    w.write_all(&(fp.len() as u32).to_le_bytes())
        .map_err(io_err)?;
    w.write_all(fp.as_bytes()).map_err(io_err)?;
    w.write_all(&(chunk_id.len() as u32).to_le_bytes())
        .map_err(io_err)?;
    w.write_all(chunk_id.as_bytes()).map_err(io_err)?;
    w.write_all(&((vec_row.len() * 4) as u32).to_le_bytes())
        .map_err(io_err)?;
    for v in vec_row {
        w.write_all(&v.to_le_bytes()).map_err(io_err)?;
    }
    Ok(())
}

fn write_record_tombstone<W: Write>(w: &mut W, fp: &str) -> Result<(), StoreError> {
    w.write_all(&[TAG_TOMBSTONE]).map_err(io_err)?;
    w.write_all(&(fp.len() as u32).to_le_bytes())
        .map_err(io_err)?;
    w.write_all(fp.as_bytes()).map_err(io_err)?;
    Ok(())
}

// ----------------------------------------------------------------------
// Tests
// ----------------------------------------------------------------------

enum ParsedRecord {
    Put {
        key: String,
        chunk_id: String,
        row_dim: usize,
    },
    Tombstone {
        key: String,
    },
}

/// Lee string largo-prefijado desde buf[pos..]; None si no alcanzan bytes.
fn read_str(buf: &[u8], pos: &mut usize) -> Option<String> {
    if *pos + 4 > buf.len() {
        return None;
    }
    let len = u32::from_le_bytes(buf[*pos..*pos + 4].try_into().unwrap()) as usize;
    *pos += 4;
    if *pos + len > buf.len() {
        return None;
    }
    let s = String::from_utf8_lossy(&buf[*pos..*pos + len]).into_owned();
    *pos += len;
    Some(s)
}

/// Parsea UN registro avanzando *pos; hace push del vector al arena.
/// Valida la dim esperada ANTES de tocar el arena (transaccional).
fn parse_record(
    buf: &[u8],
    pos: &mut usize,
    expected_dim: Option<usize>,
    arena: &mut Vec<f32>,
) -> Result<ParsedRecord, StoreError> {
    let tag = buf[*pos];
    match tag {
        TAG_TOMBSTONE => {
            *pos += 1;
            match read_str(buf, pos) {
                Some(key) => Ok(ParsedRecord::Tombstone { key }),
                None => Err(truncado()),
            }
        }
        TAG_PUT => {
            *pos += 1;
            let key = read_str(buf, pos).ok_or_else(truncado)?;
            let chunk_id = read_str(buf, pos).ok_or_else(truncado)?;
            if *pos + 4 > buf.len() {
                return Err(truncado());
            }
            let vlen = u32::from_le_bytes(buf[*pos..*pos + 4].try_into().unwrap()) as usize;
            *pos += 4;
            if !vlen.is_multiple_of(4) || *pos + vlen > buf.len() {
                return Err(StoreError::Corrupted(format!(
                    "registro PUT con vlen={vlen} inválido o cola corta"
                )));
            }
            let row_dim = vlen / 4;
            if let Some(d) = expected_dim {
                if d != row_dim {
                    return Err(StoreError::DimMismatch {
                        expected: d,
                        got: row_dim,
                    });
                }
            }
            for j in 0..row_dim {
                let b: [u8; 4] = buf[*pos + j * 4..*pos + j * 4 + 4].try_into().unwrap();
                arena.push(f32::from_le_bytes(b));
            }
            *pos += vlen;
            Ok(ParsedRecord::Put {
                key,
                chunk_id,
                row_dim,
            })
        }
        other => Err(StoreError::Corrupted(format!(
            "tag desconocido {} en offset {}",
            other,
            *pos - 1
        ))),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn temp_dir(tag: &str) -> PathBuf {
        let d =
            std::env::temp_dir().join(format!("cortex-store-test-{tag}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&d);
        d
    }

    fn fps(n: usize, salt: &str) -> Vec<String> {
        (0..n).map(|i| format!("{salt}{i:064}")).collect()
    }

    #[test]
    fn put_get_roundtrip_dim_parametrica() {
        // La dim JAMÁS es constante: mismo store sirve para 3, 384 o 1024.
        for (dim, n) in [(3usize, 5usize), (384, 50), (1024, 7)] {
            let dir = temp_dir(&format!("roundtrip-{dim}"));
            let keys = fps(n, "fp");
            let cids: Vec<String> = (0..n).map(|i| format!("doc.md#{i}")).collect();
            let vecs: Vec<f32> = (0..n * dim).map(|j| j as f32 * 0.25).collect();

            {
                let mut st = VectorStore::open(&dir, "modelo-test").unwrap();
                assert!(st.is_empty());
                st.put_many(&keys, &cids, &vecs, dim).unwrap();
                assert_eq!(st.len(), n);
                assert_eq!(st.dim(), Some(dim));
            }
            // Reapertura = cold load: todo debe estar.
            let st = VectorStore::open(&dir, "modelo-test").unwrap();
            assert_eq!(st.len(), n);
            let mut out = vec![0f32; n * dim];
            let mut present = vec![false; n];
            let hits = st.get_many(&keys, &mut out, &mut present).unwrap();
            assert_eq!(hits, n);
            assert!(out == vecs, "vectores deben volver bit-idénticos");
            let _ = std::fs::remove_dir_all(&dir);
        }
    }

    #[test]
    fn misses_y_store_vacio_son_silenciosos() {
        let dir = temp_dir("misses");
        let mut st = VectorStore::open(&dir, "m").unwrap();
        // Store vacío: get_many sobre dim desconocida => todo miss, sin error.
        let mut out = vec![0f32; 2 * 4];
        let mut present = vec![true; 2];
        let hits = st.get_many(&fps(2, "x"), &mut out, &mut present).unwrap();
        assert_eq!(hits, 0);
        assert!(!present.iter().any(|p| *p));

        st.put_many(&fps(1, "k"), &["a.md".into()], &[1.0, 2.0, 3.0, 4.0], 4)
            .unwrap();
        let clave = fps(1, "k").remove(0);
        let mut present = vec![false; 2];
        let hits = st
            .get_many(&["no-existe".into(), clave], &mut out, &mut present)
            .unwrap();
        assert_eq!(hits, 1);
        assert!(present[1] && !present[0]);
        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn tombstone_invalidez_y_compact() {
        let dir = temp_dir("tombstone");
        let mut st = VectorStore::open(&dir, "m").unwrap();
        let keys = fps(4, "fp");
        let cids: Vec<String> = ["a.md", "b.md", "c.md", "d.md"]
            .iter()
            .map(|s| s.to_string())
            .collect();
        let vecs: Vec<f32> = (0..16).map(|j| j as f32).collect();
        st.put_many(&keys, &cids, &vecs, 4).unwrap();

        let borrados = st
            .invalidate_many(&[keys[1].clone(), keys[3].clone()])
            .unwrap();
        assert_eq!(borrados, 2);
        // Re-invalidate es no-op idempotente.
        assert_eq!(st.invalidate_many(&[keys[1].clone()]).unwrap(), 0);
        assert_eq!(st.len(), 2);

        st.compact().unwrap();
        assert_eq!(st.len(), 2);
        // Tras compact + reopen, los vivos siguen y los muertos no vuelven.
        let st2 = VectorStore::open(&dir, "m").unwrap();
        assert_eq!(st2.len(), 2);
        let mut out = vec![0f32; 8];
        let mut present = vec![false; 2];
        assert_eq!(
            st2.get_many(&[keys[0].clone(), keys[2].clone()], &mut out, &mut present)
                .unwrap(),
            2
        );
        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn reput_mismo_fp_reemplaza_y_falla_por_dim_ruidosa() {
        let dir = temp_dir("reput");
        let mut st = VectorStore::open(&dir, "m").unwrap();
        let k = vec!["f".repeat(64)];
        st.put_many(&k, &["a.md".into()], &[1.0, 2.0], 2).unwrap();
        st.put_many(&k, &["a.md".into()], &[9.0, 9.0], 2).unwrap();
        assert_eq!(st.len(), 1); // reemplazo lógico
        let mut out = vec![0f32; 2];
        let mut present = vec![false; 1];
        st.get_many(&k, &mut out, &mut present).unwrap();
        assert_eq!(out, vec![9.0, 9.0]);

        // Dim distinta en el MISMO store = falla ruidosa (jamás mezclar).
        assert!(st
            .put_many(&["g".repeat(64)], &["b.md".into()], &[1.0], 1)
            .is_err());
        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn modelo_distinto_resetea_el_store() {
        let dir = temp_dir("modelo");
        {
            let mut st = VectorStore::open(&dir, "modelo-A").unwrap();
            st.put_many(
                &fps(2, "fp"),
                &["a".into(), "b".into()],
                &[1.0, 2.0, 3.0, 4.0],
                2,
            )
            .unwrap();
        }
        let st = VectorStore::open(&dir, "modelo-B").unwrap();
        assert_eq!(st.len(), 0, "vectores de otro modelo jamás se reutilizan");
        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn cola_truncada_conserva_prefijo_valido() {
        let dir = temp_dir("truncado");
        {
            let mut st = VectorStore::open(&dir, "m").unwrap();
            st.put_many(
                &fps(10, "fp"),
                (0..10)
                    .map(|i| format!("d{i}"))
                    .collect::<Vec<_>>()
                    .as_slice(),
                &(0..40).map(|j| j as f32).collect::<Vec<_>>(),
                4,
            )
            .unwrap();
        }
        // Simular crash: cortar el archivo a mitad del último registro.
        let path = dir.join(STORE_FILENAME);
        let data = std::fs::read(&path).unwrap();
        std::fs::write(&path, &data[..data.len() - 6]).unwrap();

        let st = VectorStore::open(&dir, "m").unwrap();
        assert!(st.truncated_tail, "debe marcar la degradación");
        assert_eq!(st.len(), 9, "prefijo válido conservado");
        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn consultas_batch_por_chunk_id() {
        let dir = temp_dir("chunkids");
        let mut st = VectorStore::open(&dir, "m").unwrap();
        let cids: Vec<String> = ["docs/a#0", "docs/a#1", "otros/b"]
            .iter()
            .map(|s| s.to_string())
            .collect();
        st.put_many(&fps(3, "fp"), &cids, &[0.0; 12], 4).unwrap();

        let exactos = st.fps_for_chunk_ids(&["docs/a#1".to_string(), "zz".to_string()]);
        assert_eq!(exactos.len(), 1);
        let prefijo = st.fps_with_chunk_prefix("docs/a#");
        assert_eq!(prefijo.len(), 2);
        let (fps_out, cids_out) = st.entries_export();
        assert_eq!(fps_out.len(), 3);
        assert_eq!(cids_out.len(), 3);
        let _ = std::fs::remove_dir_all(&dir);
    }
}

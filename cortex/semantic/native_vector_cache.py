"""NativeVectorCache — store vectorial Rust (schema v3) con la API de VectorCache.

Reemplazo drop-in del ``VectorCache`` Python para el flag ``CORTEX_NATIVE=1``
(Obra 03, Gate G2). Delega el almacenamiento en ``cortex_core._native
.NativeVectorStore``: log append-only de UN archivo (``vectors.v3.bin``) que
elimina las dos patologías del esquema anterior:

- carga O(N) syscalls → UNA lectura secuencial;
- re-serialización JSON del índice por put/invalidate (O(N²) de ingesta)
  → append puro amortizado O(1).

Paridad garantizada:
- fingerprints: mismos que el cache Python (``cache_fingerprint`` no cambia);
- dim paramétrica: inferida del primer vector, validada después, mismatch
  ruidoso (lección vector_cache.py:41 / Fix A1);
- modelo distinto ⇒ reset del store (Fix A3);
- batch_put transaccional todo-o-nada (Fix A2);
- invalidaciones idempotentes + leak hasta compact() (mismas semánticas);
- store vacío ⇒ todo miss sin error.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path

import numpy as np

from cortex.semantic.vector_cache import CacheStats, VECTOR_DTYPE

logger = logging.getLogger(__name__)


class NativeVectorCache:
    """Cache persistente de embeddings respaldado por el store binario Rust.

    Args/semántica idénticos a :class:`~cortex.semantic.vector_cache.VectorCache`
    salvo ``dim``: aceptado por compatibilidad, la dimensión efectiva es la del
    propio store (paramétrica; jamás constante).
    """

    def __init__(
        self,
        cache_dir: Path,
        *,
        model_name: str = "all-MiniLM-L6-v2",
        dim: int | None = None,
        **_compat: object,
    ) -> None:
        if dim is not None and dim <= 0:
            raise ValueError(f"dim must be a positive int, got {dim!r}")
        # _compat absorbe auto_compact* (la política de compactación vive en
        # compact(); el store nativo no re-serializa nada por operación).
        from cortex_core import _native

        self.cache_dir = Path(cache_dir)
        self.model_name = model_name
        self._store = _native.NativeVectorStore(str(self.cache_dir), model_name)
        if self._store.truncated_tail:
            logger.warning(
                "Store vectorial nativo con cola truncada/corrupta; se conservó "
                "el prefijo válido (%s entradas). Compactá para estabilizar.",
                len(self._store),
            )
        self._lock = threading.RLock()
        self._hit_count = 0
        self._miss_count = 0

    # ------------------------------------------------------------------
    # Lectura
    # ------------------------------------------------------------------

    def get(self, fingerprint: str) -> np.ndarray | None:
        """Vector para ``fingerprint`` o ``None`` en miss/invalidado."""
        hits = self.batch_get([fingerprint])
        return hits.get(fingerprint)

    def batch_get(self, fingerprints: list[str]) -> dict[str, np.ndarray]:
        """Bulk get (UNA llamada FFI). Devuelve solo hits."""
        if not fingerprints:
            return {}
        with self._lock:
            matrix, present = self._store.get_many(list(fingerprints))
            out: dict[str, np.ndarray] = {}
            for fp, ok in zip(fingerprints, present):
                if ok:
                    self._hit_count += 1
                else:
                    self._miss_count += 1
            idx_ok = [i for i, ok in enumerate(present) if ok]
            for i in idx_ok:
                out[fingerprints[i]] = matrix[i]
            return out

    # ------------------------------------------------------------------
    # Escritura
    # ------------------------------------------------------------------

    def put(self, fingerprint: str, chunk_id: str, vector: np.ndarray) -> None:
        self.batch_put([(fingerprint, chunk_id, vector)])

    def batch_put(self, items: list[tuple[str, str, np.ndarray]]) -> None:
        """Bulk put transaccional: validación previa, todo-o-nada (Fix A2)."""
        if not items:
            return
        fps = [fp for fp, _, _ in items]
        cids = [cid for _, cid, _ in items]
        vecs = [
            v.astype(VECTOR_DTYPE) if v.dtype != VECTOR_DTYPE else v
            for _, _, v in items
        ]
        with self._lock:
            try:
                self._store.put_many(fps, cids, np.asarray(vecs, dtype=VECTOR_DTYPE))
            except Exception as exc:
                logger.warning("put_many nativo falló: %s", exc)
                raise

    # ------------------------------------------------------------------
    # Invalidación granular
    # ------------------------------------------------------------------

    def invalidate(self, fingerprint: str) -> bool:
        """Marca una entrada inválida. True si existía (idempotente)."""
        with self._lock:
            existia = fingerprint in self._all_fps()
            if not existia:
                return False
            self._store.invalidate_many([fingerprint])
            return True

    def invalidate_chunks(self, chunk_ids: list[str]) -> int:
        """Invalida por chunk_id exacto. Devuelve cuántas fueron nuevas."""
        if not chunk_ids:
            return 0
        with self._lock:
            fps = self._store.fps_for_chunk_ids(list(chunk_ids))
            return self._store.invalidate_many(fps) if fps else 0

    def invalidate_by_chunk_id(self, chunk_id_prefix: str) -> int:
        """Invalida cada entrada cuyo chunk_id empieza con el prefijo."""
        with self._lock:
            fps = self._store.fps_with_chunk_prefix(chunk_id_prefix)
            return self._store.invalidate_many(fps) if fps else 0

    def get_chunk_fingerprints(self, parent_path: str) -> dict[str, str]:
        """{chunk_id: fp} de chunks vivos bajo ``parent_path`` (prefijo '#')."""
        prefix_sep = parent_path + "#"
        with self._lock:
            fps, cids = self._store.entries_export()
            return {
                cid: fp for fp, cid in zip(fps, cids)
                if cid == parent_path or cid.startswith(prefix_sep)
            }

    # ------------------------------------------------------------------
    # Mantenimiento y stats
    # ------------------------------------------------------------------

    def compact(self) -> None:
        """Reescribe el archivo solo con entradas vivas (atómico)."""
        with self._lock:
            self._store.compact()

    def clear(self) -> None:
        """Elimina todas las entradas (borra el archivo del log)."""
        with self._lock:
            path = self.cache_dir / "vectors.v3.bin"
            path.unlink(missing_ok=True)
            from cortex_core import _native

            self._store = _native.NativeVectorStore(str(self.cache_dir), self.model_name)

    def stats(self) -> CacheStats:
        with self._lock:
            path = self.cache_dir / "vectors.v3.bin"
            size = path.stat().st_size if path.exists() else 0
            return CacheStats(
                total_entries=len(self._store),
                valid_entries=len(self._store),
                invalidated_entries=0,
                size_bytes=size,
                hit_count=self._hit_count,
                miss_count=self._miss_count,
            )

    def __len__(self) -> int:
        with self._lock:
            return len(self._store)

    def __contains__(self, fingerprint: object) -> bool:
        if not isinstance(fingerprint, str):
            return False
        with self._lock:
            return fingerprint in self._all_fps()

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------

    def _all_fps(self) -> set[str]:
        fps, _ = self._store.entries_export()
        return set(fps)


__all__ = ["NativeVectorCache"]

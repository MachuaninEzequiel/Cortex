"""B5 (review cli): polling O(n) por tick anula la optimización del sidebar.

``_detect_changes`` hacía ``service.list()`` completo EN CADA tick
(~4/s). Ahora el snapshot de mtimes solo corre en ticks "deep" (los
mismos que refrescan el sidebar); entre ticks solo se hace un stat del
puntero activo.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from cortex.cli.session_tui import _detect_changes


def _service_con_list(contador: list[int]) -> MagicMock:
    service = MagicMock()
    def _list():
        contador.append(1)
        return []
    service.list.side_effect = _list
    service.active_pointer_path.return_value.write_text = lambda *_: None
    service.active_pointer_path.return_value.exists.return_value = False
    return service


class TestThrottling:
    def test_tick_no_deep_no_escanea_sesiones(self, tmp_path) -> None:
        llamadas: list[int] = []
        service = _service_con_list(llamadas)

        _, active_mtime, session_mtimes = _detect_changes(
            service,
            prev_active_mtime=None,
            prev_session_mtimes={"2026-01-01_a": 1.0},
            deep=False,
        )

        assert llamadas == [], "tick intermedio NO debe hacer list() O(n)"
        # conserva el snapshot previo sin cambios
        assert session_mtimes == {"2026-01-01_a": 1.0}

    def test_tick_deep_si_escanea(self, tmp_path) -> None:
        llamadas: list[int] = []
        service = _service_con_list(llamadas)

        _, _, session_mtimes = _detect_changes(
            service,
            prev_active_mtime=None,
            prev_session_mtimes={},
            deep=True,
        )

        assert len(llamadas) == 1
        assert session_mtimes == {}

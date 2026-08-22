"""federation.build_snapshot honra use_cache (review 9 #6, auditoría H-2)."""

from __future__ import annotations

from unittest.mock import MagicMock

from cortex.webgraph.federation import FederatedWebGraphService as WebGraphFederation


def _fed_con_servicios() -> tuple[WebGraphFederation, MagicMock]:
    fed = WebGraphFederation.__new__(WebGraphFederation)
    servicio = MagicMock()
    snapshot = MagicMock()
    snapshot.nodes = []
    snapshot.edges = []
    snapshot.fingerprint = "fp"
    servicio.build_snapshot.return_value = snapshot
    fed._services = {"p1": servicio}
    return fed, servicio


def test_use_cache_true_se_propaga() -> None:
    fed, servicio = _fed_con_servicios()
    fed.build_snapshot("hybrid", use_cache=True, scope="local")
    assert servicio.build_snapshot.call_args.kwargs["use_cache"] is True


def test_use_cache_false_se_propaga() -> None:
    fed, servicio = _fed_con_servicios()
    fed.build_snapshot("hybrid", use_cache=False)
    assert servicio.build_snapshot.call_args.kwargs["use_cache"] is False

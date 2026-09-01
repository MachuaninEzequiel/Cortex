"""i18n ES/EN del ActionEngine y Home (Obra 05 Fase E).

Resolución del idioma: clave ``ui.language`` en config.yaml
(``es`` | ``en``); fallback ``es`` (idioma del dueño). Los títulos de
acciones y etiquetas del Home se resuelven con :func:`t`.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import yaml

DEFAULT_LANG = "es"


@lru_cache(maxsize=8)
def _leer_ui_language(config_path: str) -> str:
    ruta = Path(config_path)
    if not ruta.exists():
        return DEFAULT_LANG
    try:
        if ruta.suffix in (".yaml", ".yml"):
            data = yaml.safe_load(ruta.read_text(encoding="utf-8")) or {}
        else:
            data = json.loads(ruta.read_text(encoding="utf-8"))
        lang = str((data.get("ui") or {}).get("language", DEFAULT_LANG)).lower()
        return lang if lang in ("es", "en") else DEFAULT_LANG
    except Exception:  # noqa: BLE001 — config rota no rompe la UI
        return DEFAULT_LANG


def idioma_de(config_path: Path | None) -> str:
    if config_path is None:
        return DEFAULT_LANG
    return _leer_ui_language(str(config_path))


def t(lang: str, es: str, en: str) -> str:
    """Devuelve el texto en el idioma resuelto."""
    return en if lang == "en" else es


# Etiquetas del Home (plan §4.2)
ETIQUETAS = {
    "es": {
        "sesion": "SESIÓN",
        "pendiente": "PENDIENTE",
        "vault": "VAULT",
        "salud": "SALUD",
        "sin_pendiente": "nada pendiente ✓",
        "acciones_sugeridas": "acción(es) sugeridas",
        "notas": "notas",
        "ninguna": "ninguna activa",
        "titulo_acciones": "Acciones sugeridas",
    },
    "en": {
        "sesion": "SESSION",
        "pendiente": "PENDING",
        "vault": "VAULT",
        "salud": "HEALTH",
        "sin_pendiente": "nothing pending ✓",
        "acciones_sugeridas": "suggested action(s)",
        "notas": "notes",
        "ninguna": "none active",
        "titulo_acciones": "Suggested actions",
    },
}


def etiquetas(lang: str) -> dict[str, str]:
    return ETIQUETAS.get(lang, ETIQUETAS[DEFAULT_LANG])

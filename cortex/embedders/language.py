"""cortex.embedders.language
----------------------------
Heuristic ES/EN language detection — pure functions, zero dependencies.

Used by Obra 04 Fase C (per-language embedding config). Priority order for
resolving the language of a document/query is ALWAYS:

1. Explicit ``lang:`` frontmatter (or explicit argument) — wins over anything.
2. Heuristic detection here (only when ``language_detection: heuristic``).
3. Default model (detection returns ``None`` on doubt).

Heuristic signals
-----------------
- Diacritics ratio: ``á é í ó ú ü ñ ¿ ¡`` over total letters. Spanish-only
  characters are a strong positive signal; English has none.
- Stopword frequency: common ES vs EN function words over tokens.

A text is only classified when it is long enough (default >= 20 words, per
spec: "never guess on short text") and one language clearly outscores the
other. Mixed or ambiguous text returns ``None``.
"""

from __future__ import annotations

import re
from typing import Literal

Language = Literal["es", "en"]

# Characters that (almost) only appear in Spanish text. ¿ ¡ ñ á etc.
_ES_DIACRITICS = set("áéíóúüñ¿¡")

# Top function words (no accents needed to match — de/el/que cover a lot).
_ES_STOPWORDS = frozenset(
    """de la que el en y a los se del las un por con no una su para es al lo
    como más pero sus le ya o este sí porque esta entre cuando muy sin sobre
    también me hasta hay donde quien desde todo nos durante todos uno les ni
    contra otros ese eso ante ellos e esto mí antes algunos qué unos yo otro
    otras otra él tanto esa estos mucho quienes nada muchos cual poco ella
    estar estas algunas algo nosotros mi mis tú te ti tu tus ellas nosotras
    vosotros vosotras os mío mía""".split()
)

_EN_STOPWORDS = frozenset(
    """the of and to in is that for it as was with be by on not he this are
    or his from at which but have an they you one had were their there been
    we who will would can could should may might must do does did done its
    our your my me him she them her us all any each if into no than then
    when where why how what so such only own same too very just also more
    most other some these those i am has""".split()
)

_WORD_RE = re.compile(r"[a-záéíóúüñ]+", re.IGNORECASE)
_LETTER_RE = re.compile(r"[a-zA-Záéíóúüñ]")


def detect_language(text: str, *, min_words: int = 20) -> Language | None:
    """Classify *text* as ``"es"`` / ``"en"``, or ``None`` when unsure.

    Args:
        text:      Raw input text (any length).
        min_words: Minimum word count required to attempt classification.
                   Texts shorter than this return ``None`` (never guess).
                   Override in tests or for query-length inputs.

    Returns:
        ``"es"`` | ``"en"`` | ``None`` (empty, too short, mixed/ambiguous).
    """
    if not text or not text.strip():
        return None

    words = _WORD_RE.findall(text.lower())
    if len(words) < min_words:
        return None

    letters = [c for c in text.lower() if _LETTER_RE.match(c)]
    diacritics = sum(1 for c in text.lower() if c in _ES_DIACRITICS)

    # Diacritics are near-conclusive for Spanish; English never uses them.
    # Threshold is deliberately low (0.5% of letters) to catch normal prose.
    if letters and diacritics / len(letters) > 0.005:
        return "es"

    es_hits = sum(1 for w in words if w in _ES_STOPWORDS)
    en_hits = sum(1 for w in words if w in _EN_STOPWORDS)

    if es_hits == 0 and en_hits == 0:
        return None  # no signal at all

    # Require a clear margin (>= 25% relative) to avoid guessing on mixed text.
    if en_hits > 0 and es_hits > 0:
        hi, lo = max(es_hits, en_hits), min(es_hits, en_hits)
        if lo / hi > 0.75:
            return None
        return "es" if es_hits > en_hits else "en"

    if en_hits == 0 and es_hits > 0:
        # Pure stopword hits with zero EN hits AND no diacritics → still
        # require a decent fraction of stopwords to trust the signal.
        return "es" if es_hits / len(words) >= 0.15 else None
    return "en" if en_hits / len(words) >= 0.15 else None


def resolve_language(
    frontmatter_lang: str | None,
    text: str,
    *,
    min_words: int = 20,
) -> Language | None:
    """Resolve the effective language: frontmatter ALWAYS beats detection.

    Args:
        frontmatter_lang: Value of a document's ``lang:`` frontmatter key
            (``"es"`` / ``"en"``, case-insensitive). Any other value is
            ignored and detection runs instead.
        text:  Text used for heuristic fallback.
        min_words: Passed through to :func:`detect_language`.

    Returns:
        The resolved language, or ``None`` → caller must use the default
        model.
    """
    if frontmatter_lang:
        lang = frontmatter_lang.strip().lower()
        if lang in ("es", "en"):
            return lang  # type: ignore[return-value]
    return detect_language(text, min_words=min_words)

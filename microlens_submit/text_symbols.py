"""Console-friendly symbols with graceful fallbacks.

Some Windows terminals still use legacy code pages (e.g., CP1252) that cannot
encode emoji-style glyphs. Attempting to print those characters raises
``UnicodeEncodeError``.  This module exposes a :func:`symbol` helper that
returns the Unicode glyph when the current output stream supports it and
otherwise falls back to a readable ASCII alternative.
"""

from __future__ import annotations

import locale
import os
import sys
from typing import Dict, Tuple

_SYMBOL_MAP: Dict[str, Tuple[str, str]] = {
    "check": ("✅", "[OK]"),
    "warning": ("⚠️", "[WARN]"),
    "error": ("❌", "[ERROR]"),
    "save": ("💾", "[SAVE]"),
    "progress": ("📊", "[STATUS]"),
    "folder": ("📁", "[EVENT]"),
    "pending": ("⏳", "[PENDING]"),
    "clipboard": ("📋", "[ALIASES]"),
    "hint": ("💡", "[HINT]"),
    "note": ("💡", "[NOTE]"),
    "trash": ("🗑️", "[REMOVE]"),
    "search": ("🔍", "[DRY RUN]"),
    "arrow": ("→", "->"),
}


def _can_encode(text: str) -> bool:
    """Return ``True`` if ``text`` can be encoded using the current stdout/stderr."""

    def _stream_supports(stream) -> bool | None:
        if stream is None:
            return None
        encoding = getattr(stream, "encoding", None)
        if not encoding:
            return None
        try:
            text.encode(encoding)
        except UnicodeEncodeError:
            return False
        else:
            return True

    # Prefer the actively used stdout/stderr streams.
    for attr in ("stdout", "stderr"):
        result = _stream_supports(getattr(sys, attr, None))
        if result is not None:
            return result

    # Fall back to the original streams if the active ones are unavailable.
    for attr in ("__stdout__", "__stderr__"):
        result = _stream_supports(getattr(sys, attr, None))
        if result:
            return True
    return False


def symbol(name: str) -> str:
    """Return a console-friendly symbol for ``name``.

    Args:
        name: Symbol identifier such as ``"check"`` or ``"warning"``.

    Returns:
        The preferred Unicode glyph when supported, otherwise a readable ASCII
        fallback.
    """
    unicode_char, fallback = _SYMBOL_MAP.get(name, ("", ""))

    if not unicode_char:
        return fallback

    # On Windows runners the locale is frequently a legacy code page (e.g. cp1252)
    # even when rich/click report UTF-8.  Prefer ASCII fallbacks unless we can
    # confidently detect a UTF-capable encoding.
    if os.name == "nt":
        candidate_encodings = [
            os.environ.get("PYTHONIOENCODING"),
            getattr(sys.stdout, "encoding", None),
            getattr(sys.stderr, "encoding", None),
            getattr(sys.__stdout__, "encoding", None),
            getattr(sys.__stderr__, "encoding", None),
            locale.getpreferredencoding(False),
        ]
        if not any(enc and "utf" in enc.lower() for enc in candidate_encodings if enc):
            return fallback or unicode_char

    if _can_encode(unicode_char):
        return unicode_char
    return fallback or unicode_char

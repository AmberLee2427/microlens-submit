"""Helper utilities that provide console-friendly status symbols.

Many commands display small status icons (check marks, warnings, etc.).
Windows terminals that use legacy code pages cannot encode these glyphs,
which previously caused ``UnicodeEncodeError`` exceptions.  This module
provides a thin compatibility layer that falls back to ASCII text when
Unicode output is not supported.
"""

from __future__ import annotations

import sys
from typing import Dict, Tuple


def _supports_unicode_output() -> bool:
    """Return True if the current stdout encoding can handle Unicode glyphs."""
    encoding = getattr(sys.stdout, "encoding", None)
    if not encoding:
        return False
    try:
        "✅".encode(encoding)
    except UnicodeEncodeError:
        return False
    return True


_SUPPORTS_UNICODE = _supports_unicode_output()

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
}


def symbol(name: str) -> str:
    """Return a console-friendly symbol for ``name``.

    Args:
        name: Symbol identifier such as ``"check"`` or ``"warning"``.

    Returns:
        The preferred Unicode glyph when supported, otherwise a readable ASCII
        fallback.
    """
    unicode_char, fallback = _SYMBOL_MAP.get(name, ("", ""))
    return unicode_char if _SUPPORTS_UNICODE else fallback

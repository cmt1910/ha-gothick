from __future__ import annotations

from functools import cache
from importlib import import_module


@cache
def load_fontforge_modules() -> tuple[object, object]:
    fontforge_module = import_module("fontforge")
    ps_mat_module = import_module("psMat")
    return fontforge_module, ps_mat_module


def glyph_exists(font, codepoint: int) -> bool:
    try:
        glyph = font[codepoint]
    except (TypeError, ValueError):
        return False
    return glyph is not None and glyph.isWorthOutputting()


def copy_glyph(source_font, destination_font, codepoint: int) -> bool:
    try:
        glyph = source_font[codepoint]
    except (TypeError, ValueError):
        return False
    if glyph is None or not glyph.isWorthOutputting():
        return False
    source_font.selection.none()
    destination_font.selection.none()
    source_font.selection.select(("unicode",), codepoint)
    source_font.copy()
    destination_font.selection.select(("unicode",), codepoint)
    destination_font.paste()
    return True

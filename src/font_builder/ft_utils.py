from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fontTools.ttLib import TTFont


def compute_x_avg_char_width(font: TTFont) -> int:
    widths = [width for width, _ in font["hmtx"].metrics.values() if width > 0]
    if not widths:
        raise ValueError("No non-zero glyph widths available for xAvgCharWidth")
    return round(sum(widths) / len(widths))


def collect_ligature_components(font: TTFont) -> dict[str, tuple[str, ...]]:
    if "GSUB" not in font:
        return {}
    ligatures: dict[str, tuple[str, ...]] = {}
    for lookup in font["GSUB"].table.LookupList.Lookup:
        if lookup.LookupType != 4:
            continue
        for subtable in lookup.SubTable:
            for first_component, entries in getattr(subtable, "ligatures", {}).items():
                for ligature in entries:
                    components = (first_component, *ligature.Component)
                    ligatures.setdefault(ligature.LigGlyph, components)
    return ligatures

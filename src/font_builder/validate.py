from __future__ import annotations

import argparse
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont

from font_builder.config import BuildConfig, load_config


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate HA-Gothick artifacts.")
    parser.add_argument("font", help="Font file to validate")
    parser.add_argument("--config", default="config/config.yaml", help="Path to config.yaml")
    args = parser.parse_args()

    config = load_config(args.config)
    font = TTFont(args.font)
    errors = validate_font(font, config)
    if errors:
        for error in errors:
            print(f"[FAIL] {error}")
        raise SystemExit(1)
    print(f"[OK] {Path(args.font).name}")


def validate_font(font: TTFont, config: BuildConfig) -> list[str]:
    errors: list[str] = []
    metrics = config.metrics
    cmap = font.getBestCmap()
    glyph_set = font.getGlyphSet()

    if font["post"].isFixedPitch != 1:
        errors.append("post.isFixedPitch must be 1")
    if font["post"].formatType != 2.0:
        errors.append("post.formatType must be 2.0")
    if font["OS/2"].panose.bProportion != 9:
        errors.append("OS/2.panose.bProportion must be 9")
    expected_xavg = _compute_x_avg_char_width(font)
    if font["OS/2"].xAvgCharWidth != expected_xavg:
        errors.append(f"OS/2.xAvgCharWidth must be {expected_xavg}")
    if font["head"].unitsPerEm != metrics.upm:
        errors.append(f"head.unitsPerEm must be {metrics.upm}")
    if font["OS/2"].sTypoAscender != metrics.typo_ascender:
        errors.append(f"OS/2.sTypoAscender must be {metrics.typo_ascender}")
    if font["OS/2"].sTypoDescender != metrics.typo_descender:
        errors.append(f"OS/2.sTypoDescender must be {metrics.typo_descender}")
    if font["OS/2"].sTypoLineGap != 0:
        errors.append("OS/2.sTypoLineGap must be 0")
    if font["hhea"].ascent != metrics.win_ascent:
        errors.append(f"hhea.ascent must be {metrics.win_ascent}")
    if font["hhea"].descent != -metrics.win_descent:
        errors.append(f"hhea.descent must be {-metrics.win_descent}")
    if font["hhea"].lineGap != 0:
        errors.append("hhea.lineGap must be 0")
    if 0xE0A0 not in cmap:
        errors.append("Powerline glyph U+E0A0 is missing")
    if 0xE000 in cmap:
        errors.append("Pomicons glyph U+E000 must not be present")
    if 0x00AD in cmap:
        errors.append("Soft Hyphen U+00AD must not be present")
    formats = {table.format for table in font["cmap"].tables}
    if 4 not in formats:
        errors.append("cmap format 4 is missing")
    if 12 not in formats:
        errors.append("cmap format 12 is missing")
    errors.extend(_check_typo_ascender(font))
    errors.extend(_check_ligature_carets(font, metrics.half_width))

    errors.extend(_check_widths(font, glyph_set, cmap, range(0x20, 0x7F), metrics.half_width, "ASCII"))
    errors.extend(_check_widths(font, glyph_set, cmap, range(0x3041, 0x3097), metrics.full_width, "Hiragana"))
    errors.extend(_check_widths(font, glyph_set, cmap, range(0x30A1, 0x30FB), metrics.full_width, "Katakana"))
    errors.extend(_check_widths(font, glyph_set, cmap, range(0x4E00, 0x4E50), metrics.full_width, "CJK sample"))
    errors.extend(_check_widths(font, glyph_set, cmap, range(0xE0A0, 0xE0D5), metrics.half_width, "Powerline"))
    return errors


def _check_widths(
    font: TTFont,
    glyph_set,
    cmap: dict[int, str],
    codepoints: range,
    expected_width: int,
    label: str,
) -> list[str]:
    errors: list[str] = []
    hmtx = font["hmtx"].metrics
    present = 0
    for codepoint in codepoints:
        glyph_name = cmap.get(codepoint)
        if glyph_name is None:
            continue
        present += 1
        width, _ = hmtx[glyph_name]
        if width != expected_width:
            errors.append(f"{label} width mismatch for U+{codepoint:04X}: {width} != {expected_width}")
    if present == 0:
        errors.append(f"{label} glyphs are missing")
    return errors


def _compute_x_avg_char_width(font: TTFont) -> int:
    widths = [width for width, _ in font["hmtx"].metrics.values() if width > 0]
    if not widths:
        raise ValueError("No non-zero glyph widths available for xAvgCharWidth")
    return int(round(sum(widths) / len(widths)))


def _check_typo_ascender(font: TTFont) -> list[str]:
    glyph_name = font.getBestCmap().get(0x00C0)
    if glyph_name is None:
        return ["Agrave glyph is missing"]

    pen = BoundsPen(font.getGlyphSet())
    font.getGlyphSet()[glyph_name].draw(pen)
    if pen.bounds is None:
        return ["/Agrave bounds could not be calculated"]

    _, _, _, y_max = pen.bounds
    if font["OS/2"].sTypoAscender <= y_max:
        return [f"OS/2.sTypoAscender must be greater than /Agrave yMax {int(y_max)}"]
    return []


def _check_ligature_carets(font: TTFont, half_width: int) -> list[str]:
    ligatures = _collect_ligatures(font)
    if not ligatures:
        return []
    if "GDEF" not in font or getattr(font["GDEF"].table, "LigCaretList", None) is None:
        return ["GDEF LigCaretList must exist for GSUB ligatures"]

    lig_caret_list = font["GDEF"].table.LigCaretList
    coverage = getattr(getattr(lig_caret_list, "Coverage", None), "glyphs", []) or []
    errors: list[str] = []
    for glyph_name, component_count in ligatures.items():
        if glyph_name not in coverage:
            errors.append(f"Ligature caret missing for {glyph_name}")
            continue
        coverage_index = coverage.index(glyph_name)
        lig_glyph = lig_caret_list.LigGlyph[coverage_index]
        if lig_glyph.CaretCount != component_count - 1:
            errors.append(f"Ligature caret count mismatch for {glyph_name}")
            continue
        expected_positions = [half_width * index for index in range(1, component_count)]
        actual_positions = [caret.Coordinate for caret in lig_glyph.CaretValue]
        if actual_positions != expected_positions:
            errors.append(f"Ligature caret positions mismatch for {glyph_name}: {actual_positions} != {expected_positions}")
    return errors


def _collect_ligatures(font: TTFont) -> dict[str, int]:
    if "GSUB" not in font:
        return {}
    ligatures: dict[str, int] = {}
    for lookup in font["GSUB"].table.LookupList.Lookup:
        if lookup.LookupType != 4:
            continue
        for subtable in lookup.SubTable:
            for first_component, entries in getattr(subtable, "ligatures", {}).items():
                for ligature in entries:
                    component_count = 1 + len(ligature.Component)
                    ligatures.setdefault(ligature.LigGlyph, component_count)
    return ligatures


if __name__ == "__main__":
    main()

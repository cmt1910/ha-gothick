from __future__ import annotations

import argparse
from pathlib import Path
import re

from fontTools import subset
from fontTools.ttLib import TTFont, newTable
from fontTools.ttLib.tables import otTables

from font_builder.common import stage_path
from font_builder.config import BuildConfig, load_config


def main() -> None:
    parser = argparse.ArgumentParser(description="Patch font metadata tables.")
    parser.add_argument("--weight", required=True, help="Target weight")
    parser.add_argument("--config", default="config/config.yaml", help="Path to config.yaml")
    parser.add_argument("--input", help="Override input font path")
    parser.add_argument("--output", help="Override output font path")
    args = parser.parse_args()

    config = load_config(args.config)
    input_path = Path(args.input) if args.input else stage_path(config, "nerd_patched", args.weight, ".ttf")
    output_path = Path(args.output) if args.output else stage_path(config, "patched", args.weight, ".ttf")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    font = TTFont(str(input_path))
    patch_tables(font, config, args.weight)
    _validate_cmap(font)
    font.save(str(output_path))


def patch_tables(font: TTFont, config: BuildConfig, weight: str) -> None:
    metrics = config.metrics
    family = config.font.family_name
    subfamily = weight
    full_name = f"{family} {subfamily}"
    postscript_name = f"{family.replace(' ', '-')}-{subfamily}"
    opentype_version = _format_opentype_version(config.font.version)

    _patch_name_table(font, config, subfamily, full_name, postscript_name, opentype_version)

    os2 = font["OS/2"]
    os2.sTypoAscender = metrics.typo_ascender
    os2.sTypoDescender = metrics.typo_descender
    os2.sTypoLineGap = metrics.typo_line_gap
    os2.usWinAscent = metrics.win_ascent
    os2.usWinDescent = metrics.win_descent
    os2.sxHeight = metrics.x_height
    os2.sCapHeight = metrics.cap_height
    os2.panose.bProportion = 9
    os2.fsSelection |= 1 << 7
    if weight.lower() == "bold":
        os2.usWeightClass = 700
        os2.fsSelection |= 1 << 5
        os2.fsSelection &= ~(1 << 6)
    else:
        os2.usWeightClass = 400
        os2.fsSelection &= ~(1 << 5)
        os2.fsSelection |= 1 << 6

    hhea = font["hhea"]
    hhea.ascent = metrics.win_ascent
    hhea.descent = -metrics.win_descent
    hhea.lineGap = metrics.line_gap

    head = font["head"]
    if head.unitsPerEm != metrics.upm:
        raise ValueError(f"Unexpected unitsPerEm: {head.unitsPerEm} != {metrics.upm}")
    head.macStyle = 1 if weight.lower() == "bold" else 0
    head.fontRevision = float(opentype_version)

    _subset_font(font)
    post = font["post"]
    post.isFixedPitch = 1 if metrics.is_fixed_pitch else 0
    post.formatType = 2.0
    post.extraNames = []
    post.mapping = {}
    _ensure_ligature_carets(font, metrics.half_width)
    os2.xAvgCharWidth = _compute_x_avg_char_width(font)


def _patch_name_table(
    font: TTFont,
    config: BuildConfig,
    subfamily: str,
    full_name: str,
    postscript_name: str,
    opentype_version: str,
) -> None:
    name_table = font["name"]
    target_ids = {0, 1, 2, 4, 5, 6, 8, 9, 11, 12, 13, 14}
    name_table.names = [
        record
        for record in name_table.names
        if record.platformID != 1 and record.nameID not in target_ids
    ]

    entries = {
        0: config.font.copyright,
        1: config.font.family_name,
        2: subfamily,
        4: full_name,
        5: f"Version {opentype_version}",
        6: postscript_name,
        8: config.font.family_name,
        9: config.font.vendor_url,
        11: config.font.vendor_url,
        12: config.font.vendor_url,
        13: config.font.license,
        14: config.font.license_url,
    }
    for name_id, value in entries.items():
        name_table.setName(value, name_id, 3, 1, 0x0409)


def _format_opentype_version(version: str) -> str:
    parts = [int(part) for part in re.findall(r"\d+", version)]
    if not parts:
        raise ValueError(f"Invalid font version: {version}")
    major = parts[0]
    minor = parts[1] if len(parts) > 1 else 0
    patch = parts[2] if len(parts) > 2 else 0
    return f"{major}.{(minor * 100 + patch):03d}"


def _subset_font(font: TTFont) -> None:
    cmap = font.getBestCmap()
    keep_codepoints = sorted((set(cmap) - _case_mismatch_codepoints(cmap)) - {0x00AD})

    options = subset.Options()
    options.name_IDs = ["*"]
    options.name_languages = ["*"]
    options.name_legacy = False
    options.layout_features = ["*"]
    options.hinting = True
    options.notdef_glyph = True
    options.notdef_outline = True
    options.recommended_glyphs = True

    subsetter = subset.Subsetter(options=options)
    subsetter.populate(unicodes=keep_codepoints)
    subsetter.subset(font)


def _case_mismatch_codepoints(cmap: dict[int, str]) -> set[int]:
    codepoints = set(cmap)
    removable: set[int] = set()
    for codepoint in codepoints:
        for mapped in _case_counterparts(codepoint):
            if mapped not in codepoints:
                removable.add(codepoint)
                break
    return removable


def _case_counterparts(codepoint: int) -> set[int]:
    char = chr(codepoint)
    candidates = {
        _single_codepoint(char.upper()),
        _single_codepoint(char.lower()),
        _single_codepoint(char.title()),
        _single_codepoint(char.casefold()),
    }
    return {candidate for candidate in candidates if candidate is not None and candidate != codepoint}


def _single_codepoint(text: str) -> int | None:
    return ord(text) if len(text) == 1 else None


def _validate_cmap(font: TTFont) -> None:
    cmap = font["cmap"]
    formats = {table.format for table in cmap.tables}
    if 4 not in formats:
        raise ValueError("cmap format 4 is missing")
    if 12 not in formats:
        raise ValueError("cmap format 12 is missing")

    best_map = cmap.getBestCmap()
    if 0xE0A0 not in best_map:
        raise ValueError("Powerline glyph U+E0A0 is missing")
    if not any(codepoint > 0xFFFF for codepoint in best_map):
        raise ValueError("Supplementary Unicode mappings are missing from cmap")


def _compute_x_avg_char_width(font: TTFont) -> int:
    widths = [width for width, _ in font["hmtx"].metrics.values() if width > 0]
    if not widths:
        raise ValueError("No non-zero glyph widths available for xAvgCharWidth")
    return int(round(sum(widths) / len(widths)))


def _ensure_ligature_carets(font: TTFont, half_width: int) -> None:
    ligatures = _collect_ligature_components(font)
    if not ligatures:
        return

    gdef = _ensure_gdef_table(font)
    class_defs = _ensure_glyph_class_def(gdef)

    coverage = otTables.Coverage()
    coverage.glyphs = sorted(ligatures)

    lig_glyphs: list[otTables.LigGlyph] = []
    for glyph_name in coverage.glyphs:
        components = ligatures[glyph_name]
        class_defs[glyph_name] = 2

        lig_glyph = otTables.LigGlyph()
        caret_values: list[otTables.CaretValue] = []
        for index in range(1, len(components)):
            caret = otTables.CaretValue()
            caret.Format = 1
            caret.Coordinate = half_width * index
            caret_values.append(caret)

        lig_glyph.CaretValue = caret_values
        lig_glyph.CaretCount = len(caret_values)
        lig_glyphs.append(lig_glyph)

    lig_caret_list = otTables.LigCaretList()
    lig_caret_list.Coverage = coverage
    lig_caret_list.LigGlyph = lig_glyphs
    lig_caret_list.LigGlyphCount = len(lig_glyphs)
    gdef.LigCaretList = lig_caret_list


def _collect_ligature_components(font: TTFont) -> dict[str, tuple[str, ...]]:
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


def _ensure_gdef_table(font: TTFont) -> otTables.GDEF:
    if "GDEF" not in font:
        table = newTable("GDEF")
        table.table = otTables.GDEF()
        table.table.Version = 0x00010000
        font["GDEF"] = table
    gdef = font["GDEF"].table
    if getattr(gdef, "Version", None) is None:
        gdef.Version = 0x00010000
    return gdef


def _ensure_glyph_class_def(gdef: otTables.GDEF) -> dict[str, int]:
    glyph_class_def = getattr(gdef, "GlyphClassDef", None)
    if glyph_class_def is None:
        glyph_class_def = otTables.ClassDef()
        glyph_class_def.classDefs = {}
        gdef.GlyphClassDef = glyph_class_def
    elif glyph_class_def.classDefs is None:
        glyph_class_def.classDefs = {}
    return glyph_class_def.classDefs


if __name__ == "__main__":
    main()

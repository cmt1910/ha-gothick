from __future__ import annotations

import argparse
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.ttLib.tables.ttProgram import Program

JAPANESE_RANGES: tuple[tuple[int, int], ...] = (
    (0x3000, 0x303F),  # CJK Symbols and Punctuation
    (0x3040, 0x309F),  # Hiragana
    (0x30A0, 0x30FF),  # Katakana
    (0x31F0, 0x31FF),  # Katakana Phonetic Extensions
    (0x3400, 0x4DBF),  # CJK Unified Ideographs Extension A
    (0x4E00, 0x9FFF),  # CJK Unified Ideographs
    (0xF900, 0xFAFF),  # CJK Compatibility Ideographs
    (0xFF00, 0xFFEF),  # Halfwidth and Fullwidth Forms
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Strip hinting from Japanese glyphs.")
    parser.add_argument("--input", required=True, help="Input TTF path")
    parser.add_argument("--output", required=True, help="Output TTF path")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    font = TTFont(str(input_path))
    strip_japanese_hinting(font)
    font.save(str(output_path))


def strip_japanese_hinting(font: TTFont) -> None:
    if "glyf" not in font or "cmap" not in font or "maxp" not in font:
        return

    glyph_order = set(font.getGlyphOrder())
    target_glyphs = _collect_target_glyphs(font)
    if not target_glyphs:
        return

    glyf_table = font["glyf"]
    for glyph_name in target_glyphs:
        if glyph_name not in glyph_order:
            continue
        glyph = glyf_table[glyph_name]
        if hasattr(glyph, "program"):
            glyph.program = Program()

    font["maxp"].maxSizeOfInstructions = _max_instruction_size(font)


def _collect_target_glyphs(font: TTFont) -> set[str]:
    cmap = font.getBestCmap() or {}
    initial = {
        glyph_name for codepoint, glyph_name in cmap.items() if _is_japanese_codepoint(codepoint)
    }
    return _expand_components(font, initial)


def _expand_components(font: TTFont, glyph_names: set[str]) -> set[str]:
    expanded = set(glyph_names)
    glyf_table = font["glyf"]
    stack = list(glyph_names)

    while stack:
        glyph_name = stack.pop()
        glyph = glyf_table[glyph_name]
        if not glyph.isComposite():
            continue

        for component in glyph.components:
            if component.glyphName in expanded:
                continue
            expanded.add(component.glyphName)
            stack.append(component.glyphName)

    return expanded


def _is_japanese_codepoint(codepoint: int) -> bool:
    return any(start <= codepoint <= end for start, end in JAPANESE_RANGES)


def _max_instruction_size(font: TTFont) -> int:
    maximum = 0
    for glyph_name in font.getGlyphOrder():
        glyph = font["glyf"][glyph_name]
        program = getattr(glyph, "program", None)
        if program is None:
            continue
        maximum = max(maximum, len(program.getBytecode()))
    return maximum


if __name__ == "__main__":
    main()

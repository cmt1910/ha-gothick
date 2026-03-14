from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

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
    if font["OS/2"].panose.bProportion != 9:
        errors.append("OS/2.panose.bProportion must be 9")
    if font["OS/2"].xAvgCharWidth != metrics.half_width:
        errors.append(f"OS/2.xAvgCharWidth must be {metrics.half_width}")
    if font["head"].unitsPerEm != metrics.upm:
        errors.append(f"head.unitsPerEm must be {metrics.upm}")
    if font["hhea"].ascent != metrics.win_ascent:
        errors.append(f"hhea.ascent must be {metrics.win_ascent}")
    if font["hhea"].descent != -metrics.win_descent:
        errors.append(f"hhea.descent must be {-metrics.win_descent}")
    if 0xE0A0 not in cmap:
        errors.append("Powerline glyph U+E0A0 is missing")
    if 0xE000 in cmap:
        errors.append("Pomicons glyph U+E000 must not be present")
    formats = {table.format for table in font["cmap"].tables}
    if 4 not in formats:
        errors.append("cmap format 4 is missing")
    if 12 not in formats:
        errors.append("cmap format 12 is missing")

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


if __name__ == "__main__":
    main()

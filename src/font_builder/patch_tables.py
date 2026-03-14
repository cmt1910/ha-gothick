from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from fontTools.ttLib import TTFont

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

    _patch_name_table(font, config, subfamily, full_name, postscript_name)

    os2 = font["OS/2"]
    os2.sTypoAscender = metrics.typo_ascender
    os2.sTypoDescender = metrics.typo_descender
    os2.sTypoLineGap = metrics.typo_line_gap
    os2.usWinAscent = metrics.win_ascent
    os2.usWinDescent = metrics.win_descent
    os2.sxHeight = metrics.x_height
    os2.sCapHeight = metrics.cap_height
    os2.xAvgCharWidth = metrics.half_width
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

    post = font["post"]
    post.isFixedPitch = 1 if metrics.is_fixed_pitch else 0


def _patch_name_table(
    font: TTFont,
    config: BuildConfig,
    subfamily: str,
    full_name: str,
    postscript_name: str,
) -> None:
    name_table = font["name"]
    target_ids = {0, 1, 2, 4, 5, 6, 11, 13, 14}
    name_table.names = [record for record in name_table.names if record.nameID not in target_ids]

    entries = {
        0: config.font.copyright,
        1: config.font.family_name,
        2: subfamily,
        4: full_name,
        5: f"Version {config.font.version}",
        6: postscript_name,
        11: config.font.vendor_url,
        13: config.font.license,
        14: config.font.license_url,
    }
    for name_id, value in entries.items():
        name_table.setName(value, name_id, 3, 1, 0x0409)
        name_table.setName(value, name_id, 1, 0, 0)


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


if __name__ == "__main__":
    main()

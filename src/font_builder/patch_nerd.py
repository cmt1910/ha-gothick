#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

try:
    import fontforge  # type: ignore
    import psMat  # type: ignore
except ImportError:
    raise

from font_builder.config import BuildConfig, load_config


NERD_SET_RANGES = {
    "powerline": ((0xE0A0, 0xE0A3), (0xE0B0, 0xE0D4)),
    "powerline_extra": ((0xE0A0, 0xE0A3), (0xE0B0, 0xE0D4)),
    "font_awesome": ((0xE200, 0xE2FF),),
    "weather": ((0xE300, 0xE3FF),),
    "devicons": ((0xE700, 0xE7FF),),
    "codicons": ((0xEA60, 0xEC00),),
    "font_logos": ((0xF300, 0xF3FF),),
    "octicons": ((0xF400, 0xF4FF),),
    "material_design": ((0xF0001, 0xF1AF0),),
    "pomicons": ((0xE000, 0xE00A),),
}
POWERLINE_RANGES = NERD_SET_RANGES["powerline"]


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Patch Nerd Fonts glyphs.")
    parser.add_argument("--weight", required=True, choices=("Regular", "Bold"))
    parser.add_argument("--config", required=True)
    return parser.parse_args(argv)


def in_ranges(codepoint: int, ranges: tuple[tuple[int, int], ...]) -> bool:
    return any(start <= codepoint <= end for start, end in ranges)


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


def normalize_width(glyph, target_width: int) -> None:
    if glyph.width > 0:
        scale = target_width / glyph.width
        glyph.transform(psMat.scale(scale, scale))
    left, _, right, _ = glyph.boundingBox()
    outline_width = right - left
    offset_x = (target_width - outline_width) / 2.0 - left
    glyph.transform(psMat.translate(offset_x, 0))
    glyph.width = target_width


def iter_target_codepoints(config: BuildConfig) -> list[int]:
    include_sets = config.nerd_fonts.include_sets
    exclude_sets = set(config.nerd_fonts.exclude_sets)
    codepoints: set[int] = set()
    for set_name in include_sets:
        if set_name in exclude_sets:
            continue
        for start, end in NERD_SET_RANGES.get(set_name, ()):
            codepoints.update(range(start, end + 1))
    for start, end in NERD_SET_RANGES["pomicons"]:
        codepoints.difference_update(range(start, end + 1))
    return sorted(codepoints)


def output_path(config: BuildConfig, weight: str) -> Path:
    return config.build_dir / f"nerd_patched-{weight}.ttf"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    config = load_config(args.config)

    metrics = config.metrics
    build_dir = config.build_dir
    merged_path = build_dir / f"merged-{args.weight}.ttf"
    nerd_path = config.nerd_source_path()
    output = output_path(config, args.weight)
    output.parent.mkdir(parents=True, exist_ok=True)

    merged = fontforge.open(str(merged_path))
    nerd = fontforge.open(str(nerd_path))
    target_width = metrics.half_width

    patched = 0
    skipped = 0
    for codepoint in iter_target_codepoints(config):
        if not glyph_exists(nerd, codepoint):
            continue
        should_replace = in_ranges(codepoint, POWERLINE_RANGES)
        if not should_replace and glyph_exists(merged, codepoint):
            skipped += 1
            continue
        if not copy_glyph(nerd, merged, codepoint):
            continue
        normalize_width(merged[codepoint], target_width)
        patched += 1

    merged.generate(str(output))
    print(f"[patch_nerd] merged={merged_path}")
    print(f"[patch_nerd] nerd={nerd_path}")
    print(f"[patch_nerd] output={output}")
    print(f"[patch_nerd] patched={patched}")
    print(f"[patch_nerd] skipped_existing={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

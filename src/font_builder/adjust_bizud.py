#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Iterable

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


KEEP_LATIN_CODEPOINTS = {0x00A5, 0x203E}
FULL_WIDTH_RANGES = (
    (0x3000, 0x303F),
    (0x3040, 0x309F),
    (0x30A0, 0x30FF),
    (0x4E00, 0x9FFF),
    (0xF900, 0xFAFF),
    (0xFF01, 0xFF60),
    (0xFFE0, 0xFFE6),
)
HALF_WIDTH_RANGES = (
    (0xFF65, 0xFF9F),
    (0xFFE8, 0xFFEE),
)
LATIN_REMOVE_RANGES = (
    (0x0000, 0x00FF),
    (0x0100, 0x024F),
)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Adjust BIZ UDGothic metrics.")
    parser.add_argument("--weight", required=True, choices=("Regular", "Bold"))
    parser.add_argument("--config", required=True)
    return parser.parse_args(argv)


def output_path(config: BuildConfig, weight: str) -> Path:
    return config.build_dir / f"bizud_adjusted-{weight}.sfd"


def iter_range_list(ranges: tuple[tuple[int, int], ...]) -> Iterable[int]:
    for start, end in ranges:
        yield from range(start, end + 1)


def glyph_exists(font, codepoint: int) -> bool:
    try:
        glyph = font[codepoint]
    except (TypeError, ValueError):
        return False
    return glyph is not None and glyph.isWorthOutputting()


def translate_and_width(glyph, target_width: int, y_offset: float) -> None:
    bbox = glyph.boundingBox()
    left, _, right, _ = bbox
    outline_width = right - left
    offset_x = (target_width - outline_width) / 2.0 - left
    glyph.transform(psMat.translate(offset_x, y_offset))
    glyph.width = target_width


def fit_glyph(glyph, target_width: int, y_offset: float) -> None:
    current_width = glyph.width
    if current_width > 0:
        scale = target_width / current_width
        glyph.transform(psMat.scale(scale, scale))
    translate_and_width(glyph, target_width, y_offset)


def aggregate_bbox(font, codepoints: Iterable[int]) -> tuple[float, float, float, float] | None:
    boxes: list[tuple[float, float, float, float]] = []
    for codepoint in codepoints:
        if glyph_exists(font, codepoint):
            boxes.append(font[codepoint].boundingBox())
    if not boxes:
        return None
    xs0, ys0, xs1, ys1 = zip(*boxes)
    return min(xs0), min(ys0), max(xs1), max(ys1)


def compute_y_offset(font, config: BuildConfig) -> int:
    override = config.metrics.y_offset
    if override is not None:
        return int(override)
    bbox = aggregate_bbox(font, range(0x3040, 0x30FF + 1))
    if bbox is None:
        return 0
    _, ymin, _, ymax = bbox
    source_center = (ymin + ymax) / 2.0
    target_center = config.metrics.x_height / 2.0
    return round(target_center - source_center)


def scale_upm(font, target_upm: int) -> None:
    current_upm = int(font.em)
    if current_upm == target_upm:
        return
    scale = target_upm / current_upm
    font.selection.all()
    font.transform(psMat.scale(scale, scale))
    font.selection.none()
    font.em = target_upm


def clear_glyph(font, codepoint: int) -> bool:
    if not glyph_exists(font, codepoint):
        return False
    font[codepoint].clear()
    return True


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    config = load_config(args.config)
    target_upm = config.metrics.upm
    full_width = config.metrics.full_width
    half_width = config.metrics.half_width
    source_path = config.bizud_source_path(args.weight)
    output = output_path(config, args.weight)
    output.parent.mkdir(parents=True, exist_ok=True)

    font = fontforge.open(str(source_path))
    scale_upm(font, target_upm)
    y_offset = compute_y_offset(font, config)

    adjusted_full = 0
    for codepoint in iter_range_list(FULL_WIDTH_RANGES):
        if not glyph_exists(font, codepoint):
            continue
        fit_glyph(font[codepoint], full_width, y_offset)
        adjusted_full += 1

    adjusted_half = 0
    for codepoint in iter_range_list(HALF_WIDTH_RANGES):
        if not glyph_exists(font, codepoint):
            continue
        fit_glyph(font[codepoint], half_width, y_offset)
        adjusted_half += 1

    removed = 0
    for codepoint in iter_range_list(LATIN_REMOVE_RANGES):
        if codepoint in KEEP_LATIN_CODEPOINTS:
            continue
        removed += int(clear_glyph(font, codepoint))

    font.save(str(output))
    print(f"[adjust_bizud] source={source_path}")
    print(f"[adjust_bizud] output={output}")
    print(f"[adjust_bizud] y_offset={y_offset}")
    print(f"[adjust_bizud] full_width_adjusted={adjusted_full}")
    print(f"[adjust_bizud] half_width_adjusted={adjusted_half}")
    print(f"[adjust_bizud] latin_removed={removed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

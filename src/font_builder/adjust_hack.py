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


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Adjust Hack font metrics.")
    parser.add_argument("--weight", required=True, choices=("Regular", "Bold"))
    parser.add_argument("--config", required=True)
    return parser.parse_args(argv)


def output_path(config: BuildConfig, weight: str) -> Path:
    return config.build_dir / f"hack_adjusted-{weight}.sfd"


def iter_target_codepoints() -> Iterable[int]:
    ranges = (
        (0x0020, 0x007E),
        (0x00A0, 0x00FF),
        (0x0100, 0x024F),
    )
    for start, end in ranges:
        yield from range(start, end + 1)


def glyph_exists(font, codepoint: int) -> bool:
    try:
        glyph = font[codepoint]
    except (TypeError, ValueError):
        return False
    return glyph is not None and glyph.isWorthOutputting()


def center_glyph_horizontally(glyph, target_width: int) -> None:
    bbox = glyph.boundingBox()
    left, _, right, _ = bbox
    outline_width = right - left
    offset = (target_width - outline_width) / 2.0 - left
    glyph.transform(psMat.translate(offset, 0))
    glyph.width = target_width


def normalize_width(glyph, target_width: int) -> bool:
    current_width = glyph.width
    if current_width <= 0:
        glyph.width = target_width
        return True
    if current_width == target_width:
        return False
    scale = target_width / current_width
    glyph.transform(psMat.scale(scale, scale))
    center_glyph_horizontally(glyph, target_width)
    return True


def find_vertical_overflows(font, win_ascent: int, win_descent: int) -> list[str]:
    overflows: list[str] = []
    lower_limit = -abs(win_descent)
    for glyph in font.glyphs():
        if not glyph.isWorthOutputting():
            continue
        _, ymin, _, ymax = glyph.boundingBox()
        if ymax > win_ascent or ymin < lower_limit:
            label = glyph.glyphname
            if glyph.unicode != -1:
                label = f"U+{glyph.unicode:04X} {label}"
            overflows.append(label)
    return overflows


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    config = load_config(args.config)
    source_path = config.hack_source_path(args.weight)
    target_width = config.metrics.half_width
    expected_upm = config.metrics.upm

    source_path.parent.mkdir(parents=True, exist_ok=True)
    output = output_path(config, args.weight)
    output.parent.mkdir(parents=True, exist_ok=True)

    font = fontforge.open(str(source_path))
    if int(font.em) != expected_upm:
        raise SystemExit(
            f"Hack UPM mismatch: expected {expected_upm}, got {font.em} ({source_path})"
        )

    changed: list[str] = []
    for codepoint in iter_target_codepoints():
        if not glyph_exists(font, codepoint):
            continue
        glyph = font[codepoint]
        if normalize_width(glyph, target_width):
            changed.append(f"U+{codepoint:04X}")

    overflows = find_vertical_overflows(
        font, config.metrics.win_ascent, config.metrics.win_descent
    )

    font.save(str(output))
    print(f"[adjust_hack] source={source_path}")
    print(f"[adjust_hack] output={output}")
    print(f"[adjust_hack] normalized={len(changed)} glyphs")
    if overflows:
        print(f"[adjust_hack] vertical overflow glyphs={len(overflows)}")
        for entry in overflows[:20]:
            print(f"[adjust_hack] overflow {entry}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import sys
from contextlib import suppress
from functools import cache
from importlib import import_module
from pathlib import Path

from font_builder.config import BuildConfig, load_config


@cache
def _load_fontforge_module() -> object:
    return import_module("fontforge")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Optimize glyph outlines.")
    parser.add_argument("--weight", required=True, choices=("Regular", "Bold"))
    parser.add_argument("--config", required=True)
    return parser.parse_args(argv)


def output_path(config: BuildConfig, weight: str) -> Path:
    return config.build_dir / f"optimized-{weight}.ttf"


def main(argv: list[str] | None = None) -> int:
    fontforge_module = _load_fontforge_module()
    args = parse_args(argv or sys.argv[1:])
    config = load_config(args.config)

    input_path = config.build_dir / f"patched-{args.weight}.ttf"
    output = output_path(config, args.weight)
    output.parent.mkdir(parents=True, exist_ok=True)

    font = fontforge_module.open(str(input_path))
    optimized = 0
    for glyph in font.glyphs():
        if not glyph.isWorthOutputting():
            continue
        with suppress(Exception):
            glyph.correctDirection()
        with suppress(Exception):
            glyph.canonicalContours()
        with suppress(Exception):
            glyph.canonicalStart()
        optimized += 1

    font.generate(str(output))
    print(f"[optimize] input={input_path}")
    print(f"[optimize] output={output}")
    print(f"[optimize] glyphs_processed={optimized}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from font_builder.config import BuildConfig, load_config
from font_builder.ff_utils import load_fontforge_modules


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Optimize glyph outlines.")
    parser.add_argument("--weight", required=True)
    parser.add_argument("--config", required=True)
    return parser.parse_args(argv)


def output_path(config: BuildConfig, weight: str) -> Path:
    return config.build_dir / f"optimized-{weight}.ttf"


def main(argv: list[str] | None = None) -> int:
    fontforge_module, _ = load_fontforge_modules()
    args = parse_args(argv or sys.argv[1:])
    config = load_config(args.config)

    input_path = config.build_dir / f"patched-{args.weight}.ttf"
    output = output_path(config, args.weight)
    output.parent.mkdir(parents=True, exist_ok=True)

    font = fontforge_module.open(str(input_path))
    optimized = 0
    warnings: list[str] = []
    for glyph in font.glyphs():
        if not glyph.isWorthOutputting():
            continue
        for op_name, op in (
            ("correctDirection", glyph.correctDirection),
            ("canonicalContours", glyph.canonicalContours),
            ("canonicalStart", glyph.canonicalStart),
        ):
            try:
                op()
            except Exception as exc:
                warnings.append(f"{glyph.glyphname}.{op_name}: {exc}")
        optimized += 1

    for warning in warnings:
        print(f"[optimize] warning: {warning}")

    font.generate(str(output))
    print(f"[optimize] input={input_path}")
    print(f"[optimize] output={output}")
    print(f"[optimize] glyphs_processed={optimized}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

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
except ImportError:
    raise

from font_builder.config import BuildConfig, load_config


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Optimize glyph outlines.")
    parser.add_argument("--weight", required=True, choices=("Regular", "Bold"))
    parser.add_argument("--config", required=True)
    return parser.parse_args(argv)


def output_path(config: BuildConfig, weight: str) -> Path:
    return config.build_dir / f"optimized-{weight}.ttf"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    config = load_config(args.config)

    input_path = config.build_dir / f"patched-{args.weight}.ttf"
    output = output_path(config, args.weight)
    output.parent.mkdir(parents=True, exist_ok=True)

    font = fontforge.open(str(input_path))
    optimized = 0
    for glyph in font.glyphs():
        if not glyph.isWorthOutputting():
            continue
        try:
            glyph.removeOverlap()
        except Exception:
            pass
        try:
            glyph.correctDirection()
        except Exception:
            pass
        try:
            glyph.canonicalContours()
        except Exception:
            pass
        try:
            glyph.canonicalStart()
        except Exception:
            pass
        try:
            glyph.addExtrema("all")
        except Exception:
            pass
        try:
            glyph.round()
        except Exception:
            pass
        try:
            glyph.simplify(0.1)
        except TypeError:
            try:
                glyph.simplify()
            except Exception:
                pass
        except Exception:
            pass
        optimized += 1

    font.generate(str(output))
    print(f"[optimize] input={input_path}")
    print(f"[optimize] output={output}")
    print(f"[optimize] glyphs_processed={optimized}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from font_builder.config import BuildConfig, load_config
from font_builder.ff_utils import copy_glyph, load_fontforge_modules

PREFERRED_BIZUD_CODEPOINTS = (0x00A5, 0x203E)
SPACE_WIDTHS = {
    0x0020: "half_width",
    0x00A0: "half_width",
    0x2002: "half_width",
    0x2003: "full_width",
    0x3000: "full_width",
}


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Merge adjusted Hack and BIZ UDGothic.")
    parser.add_argument("--weight", required=True)
    parser.add_argument("--config", required=True)
    return parser.parse_args(argv)


def output_path(config: BuildConfig, weight: str) -> Path:
    return config.build_dir / f"merged-{weight}.ttf"


def main(argv: list[str] | None = None) -> int:
    fontforge_module, _ = load_fontforge_modules()
    args = parse_args(argv or sys.argv[1:])
    config = load_config(args.config)

    metrics = config.metrics
    build_dir = config.build_dir
    hack_path = build_dir / f"hack_adjusted-{args.weight}.sfd"
    bizud_path = build_dir / f"bizud_adjusted-{args.weight}.sfd"
    output = output_path(config, args.weight)
    output.parent.mkdir(parents=True, exist_ok=True)

    base = fontforge_module.open(str(hack_path))
    bizud = fontforge_module.open(str(bizud_path))

    base.mergeFonts(str(bizud_path))

    replaced = 0
    for codepoint in PREFERRED_BIZUD_CODEPOINTS:
        if copy_glyph(bizud, base, codepoint):
            replaced += 1

    for codepoint, metric_name in SPACE_WIDTHS.items():
        width = getattr(metrics, metric_name)
        glyph = base.createChar(codepoint)
        glyph.width = width

    base.generate(str(output))
    print(f"[merge] hack={hack_path}")
    print(f"[merge] bizud={bizud_path}")
    print(f"[merge] output={output}")
    print(f"[merge] bizud_replaced={replaced}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

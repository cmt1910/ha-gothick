from __future__ import annotations

import argparse
from pathlib import Path
import shutil

from .common import check_commands, ensure_directories, final_font_path, run_command, stage_path
from .config import BuildConfig, load_config


def main() -> None:
    parser = argparse.ArgumentParser(description="HA-Gothick build orchestrator")
    parser.add_argument("--weight", help="Build only one weight")
    parser.add_argument(
        "--config",
        default=str(Path("config/config.yaml")),
        help="Path to config.yaml",
    )
    parser.add_argument("--skip-hinting", action="store_true", help="Skip ttfautohint")
    args = parser.parse_args()

    config = load_config(args.config)
    missing = check_commands(["fontforge", "uv"])
    if not args.skip_hinting:
        missing.extend(check_commands(["ttfautohint"]))
    if missing:
        raise SystemExit(f"Missing required commands: {', '.join(sorted(set(missing)))}")

    ensure_directories([config.build_dir, config.dist_dir])
    weights = [config.weight(args.weight)] if args.weight else list(config.weights)
    for weight in weights:
        build_weight(config, weight.name, skip_hinting=args.skip_hinting)


def build_weight(config: BuildConfig, weight: str, *, skip_hinting: bool) -> None:
    root = config.project_root
    config_arg = str(config.config_path)

    fontforge_scripts = [
        "adjust_hack.py",
        "adjust_bizud.py",
        "merge.py",
        "patch_nerd.py",
        "optimize.py",
    ]
    for script in fontforge_scripts:
        run_command(
            ["fontforge", "-script", f"src/font_builder/{script}", "--weight", weight, "--config", config_arg],
            cwd=root,
        )

    run_command(
        ["uv", "run", "python", "src/font_builder/patch_tables.py", "--weight", weight, "--config", config_arg],
        cwd=root,
    )

    optimized = stage_path(config, "optimized", weight, ".ttf")
    hinted = stage_path(config, "hinted", weight, ".ttf")
    final_input = hinted
    if skip_hinting:
        hinted.write_bytes(optimized.read_bytes())
    else:
        result = _run_hinting(optimized, hinted, root)
        if not result:
            hinted.write_bytes(optimized.read_bytes())
    final_path = final_font_path(config, weight)
    shutil.copyfile(final_input, final_path)


def _run_hinting(optimized: Path, hinted: Path, root: Path) -> bool:
    import subprocess

    command = [
        "ttfautohint",
        "--stem-width-mode=nnn",
        "--increase-x-height=14",
        "--no-info",
        "--fallback-script=latn",
        str(optimized),
        str(hinted),
    ]
    completed = subprocess.run(command, cwd=str(root), check=False)
    return completed.returncode == 0

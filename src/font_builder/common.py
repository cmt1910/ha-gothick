from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable

from .config import BuildConfig, load_config


def parse_common_args(description: str) -> tuple[argparse.Namespace, BuildConfig]:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--weight", required=True, help="Build target weight, e.g. Regular or Bold")
    parser.add_argument(
        "--config",
        default=str(Path("config/config.yaml")),
        help="Path to config.yaml",
    )
    args = parser.parse_args()
    config = load_config(args.config)
    return args, config


def ensure_directories(paths: Iterable[Path]) -> None:
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)


def stage_path(config: BuildConfig, stem: str, weight: str, suffix: str) -> Path:
    return config.build_dir / f"{stem}-{weight}{suffix}"


def final_font_path(config: BuildConfig, weight: str) -> Path:
    return config.dist_dir / f"{config.font.family_name}-{weight}.ttf"


def check_commands(commands: Iterable[str]) -> list[str]:
    return [command for command in commands if shutil.which(command) is None]


def run_command(command: list[str], cwd: Path, env: dict[str, str] | None = None) -> None:
    merged_env = os.environ.copy()
    if env is not None:
        merged_env.update(env)
    completed = subprocess.run(command, cwd=str(cwd), check=False, env=merged_env)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def python_command() -> list[str]:
    return [sys.executable]

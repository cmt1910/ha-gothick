from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import shutil
import subprocess
from typing import Any

try:
    import yaml
except ImportError:  # FontForge system Python may not have PyYAML.
    yaml = None


class ConfigError(RuntimeError):
    """Raised when the build configuration is invalid."""


@dataclass(frozen=True)
class FontConfig:
    family_name: str
    version: str
    copyright: str
    license: str
    license_url: str
    vendor_url: str


@dataclass(frozen=True)
class MetricsConfig:
    upm: int
    half_width: int
    full_width: int
    ascender: int
    descender: int
    line_gap: int
    typo_ascender: int
    typo_descender: int
    typo_line_gap: int
    win_ascent: int
    win_descent: int
    x_height: int
    cap_height: int
    is_fixed_pitch: bool
    y_offset: int | None = None
    bizud_visual_scale: float = 1.0


@dataclass(frozen=True)
class SourceConfig:
    dir: str
    original_upm: int | None = None
    file: str | None = None


@dataclass(frozen=True)
class WeightConfig:
    name: str
    hack: str
    bizud: str


@dataclass(frozen=True)
class NerdFontsConfig:
    include_sets: tuple[str, ...]
    exclude_sets: tuple[str, ...]


@dataclass(frozen=True)
class BuildConfig:
    project_root: Path
    config_path: Path
    font: FontConfig
    metrics: MetricsConfig
    sources: dict[str, SourceConfig]
    weights: tuple[WeightConfig, ...]
    nerd_fonts: NerdFontsConfig
    raw: dict[str, Any]

    @property
    def build_dir(self) -> Path:
        return self.project_root / "build"

    @property
    def dist_dir(self) -> Path:
        return self.project_root / "dist"

    def weight(self, name: str) -> WeightConfig:
        for weight in self.weights:
            if weight.name == name:
                return weight
        raise ConfigError(f"Unknown weight: {name}")

    def source_dir(self, key: str) -> Path:
        try:
            source = self.sources[key]
        except KeyError as error:
            raise ConfigError(f"Unknown source group: {key}") from error
        return self.project_root / source.dir

    def hack_source_path(self, weight_name: str) -> Path:
        weight = self.weight(weight_name)
        return self.source_dir("hack") / weight.hack

    def bizud_source_path(self, weight_name: str) -> Path:
        weight = self.weight(weight_name)
        return self.source_dir("bizud") / weight.bizud

    def nerd_source_path(self) -> Path:
        nerd = self.sources["nerd"]
        if not nerd.file:
            raise ConfigError("Missing sources.nerd.file")
        return self.source_dir("nerd") / nerd.file


def load_config(config_path: str | Path) -> BuildConfig:
    path = Path(config_path).expanduser().resolve()
    raw = _load_yaml_with_fallback(path)

    metrics_raw = _require_mapping(raw, "metrics")
    half_width = int(metrics_raw["half_width"])
    full_width = int(metrics_raw["full_width"])
    if full_width != half_width * 2:
        raise ConfigError(
            f"metrics.full_width must be exactly 2x half_width: {full_width} != {half_width * 2}"
        )

    project_root = path.parent.parent.resolve()
    font_raw = _require_mapping(raw, "font")
    sources_raw = _require_mapping(raw, "sources")
    weights_raw = raw.get("weights")
    nerd_raw = _require_mapping(raw, "nerd_fonts")

    weights: list[WeightConfig] = []
    if not isinstance(weights_raw, list) or not weights_raw:
        raise ConfigError("weights must be a non-empty list")
    for item in weights_raw:
        if not isinstance(item, dict):
            raise ConfigError("each weight must be a mapping")
        weights.append(
            WeightConfig(
                name=str(item["name"]),
                hack=str(item["hack"]),
                bizud=str(item["bizud"]),
            )
        )

    sources = {
        key: SourceConfig(
            dir=str(value["dir"]),
            original_upm=int(value["original_upm"]) if "original_upm" in value else None,
            file=str(value["file"]) if "file" in value else None,
        )
        for key, value in sources_raw.items()
    }

    return BuildConfig(
        project_root=project_root,
        config_path=path,
        font=FontConfig(
            family_name=str(font_raw["family_name"]),
            version=str(font_raw["version"]),
            copyright=str(font_raw["copyright"]),
            license=str(font_raw["license"]),
            license_url=str(font_raw["license_url"]),
            vendor_url=str(font_raw["vendor_url"]),
        ),
        metrics=MetricsConfig(
            upm=int(metrics_raw["upm"]),
            half_width=half_width,
            full_width=full_width,
            ascender=int(metrics_raw["ascender"]),
            descender=int(metrics_raw["descender"]),
            line_gap=int(metrics_raw["line_gap"]),
            typo_ascender=int(metrics_raw["typo_ascender"]),
            typo_descender=int(metrics_raw["typo_descender"]),
            typo_line_gap=int(metrics_raw["typo_line_gap"]),
            win_ascent=int(metrics_raw["win_ascent"]),
            win_descent=int(metrics_raw["win_descent"]),
            x_height=int(metrics_raw["x_height"]),
            cap_height=int(metrics_raw["cap_height"]),
            is_fixed_pitch=bool(metrics_raw["is_fixed_pitch"]),
            y_offset=(
                int(metrics_raw["y_offset"])
                if metrics_raw.get("y_offset") is not None
                else None
            ),
            bizud_visual_scale=float(metrics_raw.get("bizud_visual_scale", 1.0)),
        ),
        sources=sources,
        weights=tuple(weights),
        nerd_fonts=NerdFontsConfig(
            include_sets=tuple(str(item) for item in nerd_raw.get("include_sets", [])),
            exclude_sets=tuple(str(item) for item in nerd_raw.get("exclude_sets", [])),
        ),
        raw=raw,
    )


def _require_mapping(raw: dict[str, Any], key: str) -> dict[str, Any]:
    value = raw.get(key)
    if not isinstance(value, dict):
        raise ConfigError(f"{key} must be a mapping")
    return value


def _load_yaml_with_fallback(path: Path) -> dict[str, Any]:
    if yaml is not None:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    else:
        uv = shutil.which("uv")
        if uv is None:
            raise ConfigError("PyYAML is unavailable and uv was not found for config loading")
        command = [
            uv,
            "run",
            "python",
            "-c",
            (
                "import json, pathlib, yaml; "
                "print(json.dumps(yaml.safe_load(pathlib.Path(__import__('sys').argv[1]).read_text(encoding='utf-8'))))"
            ),
            str(path),
        ]
        try:
            completed = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as error:
            message = error.stderr.strip() or error.stdout.strip() or str(error)
            raise ConfigError(f"Failed to load config via uv: {message}") from error
        data = json.loads(completed.stdout)
    if not isinstance(data, dict):
        raise ConfigError("config root must be a mapping")
    return data

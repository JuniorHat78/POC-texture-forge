from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


_PRESETS_PATH = Path(__file__).resolve().parents[1] / "texture-presets.json"


@lru_cache(maxsize=1)
def load_presets() -> dict[str, Any]:
    with _PRESETS_PATH.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if "styles" not in data or "defaults" not in data or "presets" not in data:
        raise ValueError("texture-presets.json is missing required top-level keys")
    if "quality_profiles" not in data:
        raise ValueError("texture-presets.json is missing quality_profiles")
    return data


def style_names() -> list[str]:
    return sorted(load_presets()["styles"].keys())


def preset_names() -> list[str]:
    return sorted(load_presets()["presets"].keys())


def allowed_sizes() -> set[int]:
    return {int(size) for size in load_presets()["allowed_sizes"]}


def get_style(style_name: str) -> dict[str, Any]:
    styles = load_presets()["styles"]
    if style_name not in styles:
        raise ValueError(f"Unknown style '{style_name}'. Available: {', '.join(style_names())}")
    return styles[style_name]


def get_preset(preset_name: str) -> dict[str, Any]:
    presets = load_presets()["presets"]
    if preset_name not in presets:
        raise ValueError(f"Unknown preset '{preset_name}'. Available: {', '.join(preset_names())}")
    return presets[preset_name]


def defaults() -> dict[str, Any]:
    return dict(load_presets()["defaults"])


def quality_profile_names() -> list[str]:
    return sorted(load_presets()["quality_profiles"].keys())


def get_quality_profile(profile_name: str) -> dict[str, Any]:
    profiles = load_presets()["quality_profiles"]
    if profile_name not in profiles:
        raise ValueError(
            f"Unknown quality profile '{profile_name}'. Available: {', '.join(quality_profile_names())}"
        )
    return dict(profiles[profile_name])

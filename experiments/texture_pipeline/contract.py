from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping

from .presets import allowed_sizes, defaults, get_preset, style_names


_FILENAME_RE = re.compile(
    r"^(?P<style>[a-z0-9_-]+)-(?P<seed>\d+)-(?P<size>\d+)-h(?P<handcraft>\d+)$",
    flags=re.IGNORECASE,
)


def _require_int(name: str, value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be an integer")
    try:
        cast = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be an integer") from exc
    return cast


def _require_float(name: str, value: Any) -> float:
    try:
        cast = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a number") from exc
    return cast


@dataclass(frozen=True)
class TextureParams:
    style: str
    seed: int
    size: int
    scale: int
    octaves: int
    roughness: float
    contrast: float
    grain: float
    handcraft: float

    @classmethod
    def from_overrides(
        cls,
        overrides: Mapping[str, Any] | None = None,
        *,
        preset_name: str | None = None,
    ) -> "TextureParams":
        data: dict[str, Any] = defaults()
        if preset_name:
            data.update(get_preset(preset_name))
        if overrides:
            data.update({key: value for key, value in overrides.items() if value is not None})

        style = str(data["style"]).strip().lower()
        seed = _require_int("seed", data["seed"])
        size = _require_int("size", data["size"])
        scale = _require_int("scale", data["scale"])
        octaves = _require_int("octaves", data["octaves"])
        roughness = _require_float("roughness", data["roughness"])
        contrast = _require_float("contrast", data["contrast"])
        grain = _require_float("grain", data["grain"])
        handcraft = _require_float("handcraft", data["handcraft"])

        cls._validate(
            style=style,
            seed=seed,
            size=size,
            scale=scale,
            octaves=octaves,
            roughness=roughness,
            contrast=contrast,
            grain=grain,
            handcraft=handcraft,
        )

        return cls(
            style=style,
            seed=seed,
            size=size,
            scale=scale,
            octaves=octaves,
            roughness=roughness,
            contrast=contrast,
            grain=grain,
            handcraft=handcraft,
        )

    @classmethod
    def from_filename_stem(cls, stem: str) -> "TextureParams":
        match = _FILENAME_RE.match(stem)
        if not match:
            raise ValueError(f"Filename stem '{stem}' does not match expected pattern")

        groups = match.groupdict()
        return cls.from_overrides(
            {
                "style": groups["style"].lower(),
                "seed": int(groups["seed"]),
                "size": int(groups["size"]),
                "handcraft": int(groups["handcraft"]) / 100.0,
            }
        )

    @staticmethod
    def _validate(
        *,
        style: str,
        seed: int,
        size: int,
        scale: int,
        octaves: int,
        roughness: float,
        contrast: float,
        grain: float,
        handcraft: float,
    ) -> None:
        styles = set(style_names())
        if style not in styles:
            raise ValueError(f"Unknown style '{style}'. Available: {', '.join(sorted(styles))}")
        if seed < 0:
            raise ValueError("seed must be >= 0")
        if size not in allowed_sizes():
            valid = ", ".join(str(value) for value in sorted(allowed_sizes()))
            raise ValueError(f"size must be one of [{valid}]")
        if not 2 <= scale <= 32:
            raise ValueError("scale must be between 2 and 32")
        if not 1 <= octaves <= 8:
            raise ValueError("octaves must be between 1 and 8")
        if not 0.0 <= roughness <= 1.5:
            raise ValueError("roughness must be between 0.0 and 1.5")
        if not 0.4 <= contrast <= 3.0:
            raise ValueError("contrast must be between 0.4 and 3.0")
        if not 0.0 <= grain <= 0.6:
            raise ValueError("grain must be between 0.0 and 0.6")
        if not 0.0 <= handcraft <= 1.0:
            raise ValueError("handcraft must be between 0.0 and 1.0")

    def to_filename_stem(self) -> str:
        handcraft_pct = int(round(self.handcraft * 100))
        return f"{self.style}-{self.seed}-{self.size}-h{handcraft_pct:02d}"

    def as_dict(self) -> dict[str, Any]:
        return {
            "style": self.style,
            "seed": self.seed,
            "size": self.size,
            "scale": self.scale,
            "octaves": self.octaves,
            "roughness": self.roughness,
            "contrast": self.contrast,
            "grain": self.grain,
            "handcraft": self.handcraft,
        }

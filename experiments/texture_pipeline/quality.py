from __future__ import annotations

from dataclasses import dataclass
from statistics import mean, pstdev
from typing import Iterable

from .core import TextureImage


@dataclass(frozen=True)
class QualityThresholds:
    max_seam_score: float = 0.28
    min_luminance_spread: float = 0.14
    min_luminance_std: float = 0.06

    @classmethod
    def from_mapping(cls, mapping: dict[str, float] | None) -> "QualityThresholds":
        if mapping is None:
            return cls()
        return cls(
            max_seam_score=float(mapping["max_seam_score"]),
            min_luminance_spread=float(mapping["min_luminance_spread"]),
            min_luminance_std=float(mapping["min_luminance_std"]),
        )

    def as_dict(self) -> dict[str, float]:
        return {
            "max_seam_score": float(self.max_seam_score),
            "min_luminance_spread": float(self.min_luminance_spread),
            "min_luminance_std": float(self.min_luminance_std),
        }


def _pixel_rgb(image: TextureImage, x: int, y: int) -> tuple[int, int, int]:
    idx = (y * image.width + x) * 4
    pixels = image.pixels
    return pixels[idx], pixels[idx + 1], pixels[idx + 2]


def edge_mismatch_score(image: TextureImage) -> float:
    if image.width <= 1 or image.height <= 1:
        return 0.0

    total = 0.0
    count = 0

    for y in range(image.height):
        left = _pixel_rgb(image, 0, y)
        right = _pixel_rgb(image, image.width - 1, y)
        total += abs(left[0] - right[0]) + abs(left[1] - right[1]) + abs(left[2] - right[2])
        count += 3

    for x in range(image.width):
        top = _pixel_rgb(image, x, 0)
        bottom = _pixel_rgb(image, x, image.height - 1)
        total += abs(top[0] - bottom[0]) + abs(top[1] - bottom[1]) + abs(top[2] - bottom[2])
        count += 3

    if count == 0:
        return 0.0
    return total / (count * 255.0)


def luminance_values(image: TextureImage) -> list[float]:
    values: list[float] = []
    pixels = image.pixels
    for idx in range(0, len(pixels), 4):
        red = pixels[idx]
        green = pixels[idx + 1]
        blue = pixels[idx + 2]
        lum = (0.2126 * red + 0.7152 * green + 0.0722 * blue) / 255.0
        values.append(lum)
    return values


def luminance_summary(image: TextureImage) -> dict[str, float]:
    values = luminance_values(image)
    if not values:
        return {"min": 0.0, "max": 0.0, "mean": 0.0, "std": 0.0, "spread": 0.0}

    min_val = min(values)
    max_val = max(values)
    return {
        "min": min_val,
        "max": max_val,
        "mean": mean(values),
        "std": pstdev(values),
        "spread": max_val - min_val,
    }


def evaluate_quality(
    image: TextureImage,
    *,
    thresholds: QualityThresholds | None = None,
) -> dict[str, float | bool]:
    active = thresholds or QualityThresholds()
    seam_score = edge_mismatch_score(image)
    lum = luminance_summary(image)
    spread = lum["spread"]
    std = lum["std"]
    pass_seam = seam_score <= active.max_seam_score
    pass_spread = spread >= active.min_luminance_spread
    pass_std = std >= active.min_luminance_std
    return {
        "seam_score": seam_score,
        "luminance_min": lum["min"],
        "luminance_max": lum["max"],
        "luminance_mean": lum["mean"],
        "luminance_std": std,
        "luminance_spread": spread,
        "pass_seam": pass_seam,
        "pass_spread": pass_spread,
        "pass_std": pass_std,
        "pass_overall": pass_seam and pass_spread and pass_std,
    }


def contact_sheet(
    images: Iterable[TextureImage],
    *,
    columns: int = 4,
    padding: int = 2,
    background: tuple[int, int, int] = (14, 20, 30),
) -> TextureImage:
    items = list(images)
    if not items:
        raise ValueError("contact_sheet requires at least one image")
    if columns <= 0:
        raise ValueError("columns must be > 0")

    tile_w = items[0].width
    tile_h = items[0].height
    for image in items:
        if image.width != tile_w or image.height != tile_h:
            raise ValueError("All images in contact_sheet must have the same dimensions")

    rows = (len(items) + columns - 1) // columns
    width = columns * tile_w + (columns + 1) * padding
    height = rows * tile_h + (rows + 1) * padding
    pixels = bytearray(width * height * 4)

    bg_r, bg_g, bg_b = background
    for idx in range(0, len(pixels), 4):
        pixels[idx] = bg_r
        pixels[idx + 1] = bg_g
        pixels[idx + 2] = bg_b
        pixels[idx + 3] = 255

    for i, image in enumerate(items):
        row = i // columns
        col = i % columns
        dst_x = padding + col * (tile_w + padding)
        dst_y = padding + row * (tile_h + padding)

        for y in range(tile_h):
            dst_idx = ((dst_y + y) * width + dst_x) * 4
            src_idx = y * tile_w * 4
            pixels[dst_idx : dst_idx + tile_w * 4] = image.pixels[src_idx : src_idx + tile_w * 4]

    return TextureImage(width=width, height=height, pixels=bytes(pixels))

from __future__ import annotations

import math
from dataclasses import dataclass

from .contract import TextureParams
from .presets import get_style


@dataclass(frozen=True)
class TextureImage:
    width: int
    height: int
    pixels: bytes


def _clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(max_value, value))


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _smoothstep(t: float) -> float:
    return t * t * (3.0 - 2.0 * t)


def _mod(value: int, modulus: int) -> int:
    return ((value % modulus) + modulus) % modulus


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    clean = hex_color.lstrip("#")
    if len(clean) == 3:
        clean = "".join(ch + ch for ch in clean)
    value = int(clean, 16)
    return ((value >> 16) & 255, (value >> 8) & 255, value & 255)


def _hash2d(x: int, y: int, seed: int) -> float:
    value = (x * 374761393 + y * 668265263 + seed * 1442695041) & 0xFFFFFFFF
    value = (value ^ (value >> 13)) & 0xFFFFFFFF
    value = (value * 1274126177) & 0xFFFFFFFF
    value = (value ^ (value >> 16)) & 0xFFFFFFFF
    return value / 4294967295.0


def _value_noise_periodic(x: float, y: float, cells: int, seed: int) -> float:
    x0 = math.floor(x)
    y0 = math.floor(y)
    x1 = x0 + 1
    y1 = y0 + 1

    fx = _smoothstep(x - x0)
    fy = _smoothstep(y - y0)

    n00 = _hash2d(_mod(x0, cells), _mod(y0, cells), seed)
    n10 = _hash2d(_mod(x1, cells), _mod(y0, cells), seed)
    n01 = _hash2d(_mod(x0, cells), _mod(y1, cells), seed)
    n11 = _hash2d(_mod(x1, cells), _mod(y1, cells), seed)

    nx0 = _lerp(n00, n10, fx)
    nx1 = _lerp(n01, n11, fx)
    return _lerp(nx0, nx1, fy)


def _fbm(u: float, v: float, base_cells: int, octaves: int, seed: int, roughness: float) -> float:
    persistence = 0.52 + roughness * 0.2
    amplitude = 1.0
    total = 0.0
    normalizer = 0.0

    for octave in range(octaves):
        frequency = 1 << octave
        cells = max(2, int(base_cells * frequency))
        sample = _value_noise_periodic(
            u * cells + octave * 0.57,
            v * cells + octave * 0.41,
            cells,
            seed + octave * 131,
        )
        total += sample * amplitude
        normalizer += amplitude
        amplitude *= persistence

    return total / normalizer


def _tone_for_style(
    style: str,
    base: float,
    detail: float,
    ridge: float,
    u: float,
    v: float,
    params: TextureParams,
) -> float:
    if style == "moss":
        return _clamp(base * 0.75 + ridge * 0.28 + (detail - 0.5) * 0.14, 0.0, 1.0)
    if style == "lava":
        glow = math.pow(base, 1.62)
        cracks = math.pow(1.0 - ridge, 2.25)
        return _clamp(glow + cracks * 0.55, 0.0, 1.0)
    if style == "metal":
        bands = abs(math.sin((u * 1.8 + v * 1.05) * math.pi * params.scale))
        return _clamp(base * 0.62 + ridge * 0.14 + bands * 0.28, 0.0, 1.0)
    if style == "sand":
        dunes = math.sin((u * 2.3 - v * 1.4) * math.pi * params.scale * 0.45) * 0.09
        return _clamp(base * 0.82 + ridge * 0.13 + dunes, 0.0, 1.0)
    if style == "ice":
        fractures = math.pow(1.0 - ridge, 2.8)
        return _clamp(base * 0.58 + (1.0 - detail) * 0.2 + fractures * 0.4, 0.0, 1.0)
    if style == "toxic":
        blobs = math.pow(ridge, 1.45)
        return _clamp(base * 0.54 + blobs * 0.34 + (detail - 0.5) * 0.22, 0.0, 1.0)
    return base


def _parse_style_stops(style: str) -> list[tuple[float, tuple[int, int, int]]]:
    stops = get_style(style)["stops"]
    return [(float(pos), _hex_to_rgb(hex_color)) for pos, hex_color in stops]


def _sample_gradient(stops: list[tuple[float, tuple[int, int, int]]], tone: float) -> tuple[int, int, int]:
    if tone <= stops[0][0]:
        return stops[0][1]
    if tone >= stops[-1][0]:
        return stops[-1][1]

    for index in range(1, len(stops)):
        prev_pos, prev_color = stops[index - 1]
        curr_pos, curr_color = stops[index]
        if tone <= curr_pos:
            local_t = (tone - prev_pos) / (curr_pos - prev_pos)
            return (
                int(round(_lerp(prev_color[0], curr_color[0], local_t))),
                int(round(_lerp(prev_color[1], curr_color[1], local_t))),
                int(round(_lerp(prev_color[2], curr_color[2], local_t))),
            )

    return stops[-1][1]


def _blend_channel(old: int, new: float, opacity: float) -> int:
    return int(round(old * (1.0 - opacity) + new * opacity))


def _paint_pixel(
    pixels: bytearray,
    width: int,
    height: int,
    x: int,
    y: int,
    brush_mode: str,
    color: tuple[int, int, int],
    opacity: float,
) -> None:
    wrapped_x = x % width
    wrapped_y = y % height
    index = (wrapped_y * width + wrapped_x) * 4
    old_r = pixels[index]
    old_g = pixels[index + 1]
    old_b = pixels[index + 2]

    if brush_mode == "lighten":
        new_r = old_r + (255 - old_r) * opacity
        new_g = old_g + (255 - old_g) * opacity
        new_b = old_b + (255 - old_b) * opacity
    elif brush_mode == "darken":
        new_r = old_r * (1.0 - opacity)
        new_g = old_g * (1.0 - opacity)
        new_b = old_b * (1.0 - opacity)
    else:
        new_r = _blend_channel(old_r, color[0], opacity)
        new_g = _blend_channel(old_g, color[1], opacity)
        new_b = _blend_channel(old_b, color[2], opacity)
        pixels[index] = int(_clamp(new_r, 0.0, 255.0))
        pixels[index + 1] = int(_clamp(new_g, 0.0, 255.0))
        pixels[index + 2] = int(_clamp(new_b, 0.0, 255.0))
        return

    pixels[index] = int(_clamp(new_r, 0.0, 255.0))
    pixels[index + 1] = int(_clamp(new_g, 0.0, 255.0))
    pixels[index + 2] = int(_clamp(new_b, 0.0, 255.0))


def _dab_wrapped(
    pixels: bytearray,
    width: int,
    height: int,
    center_x: float,
    center_y: float,
    radius: float,
    *,
    brush_mode: str,
    color: tuple[int, int, int],
    opacity: float,
) -> None:
    if radius <= 0.0:
        return

    min_x = math.floor(center_x - radius)
    max_x = math.ceil(center_x + radius)
    min_y = math.floor(center_y - radius)
    max_y = math.ceil(center_y + radius)
    radius_sq = radius * radius

    for y in range(min_y, max_y + 1):
        for x in range(min_x, max_x + 1):
            dx = x - center_x
            dy = y - center_y
            if dx * dx + dy * dy <= radius_sq:
                _paint_pixel(
                    pixels,
                    width,
                    height,
                    x,
                    y,
                    brush_mode=brush_mode,
                    color=color,
                    opacity=opacity,
                )


def _create_rng(seed: int):
    state = (seed & 0xFFFFFFFF) or 1

    def _next() -> float:
        nonlocal state
        state = (state * 1664525 + 1013904223) & 0xFFFFFFFF
        return state / 4294967296.0

    return _next


def _apply_handcrafted_pass(pixels: bytearray, params: TextureParams) -> None:
    strength = _clamp(params.handcraft, 0.0, 1.0)
    if strength <= 0.0:
        return

    size = params.size
    rand = _create_rng(params.seed + 104729)
    size_scale = size / 256.0
    stroke_count = int(14 + strength * 90)

    style_stops = get_style(params.style)["stops"]
    style_colors = [_hex_to_rgb(stop[1]) for stop in style_stops]
    style_len = len(style_colors)

    for _ in range(stroke_count):
        x = rand() * size
        y = rand() * size
        direction = rand() * math.pi * 2.0
        curve = (rand() - 0.5) * 0.7
        length = (8 + rand() * 22 + strength * 28) * size_scale
        mode_roll = rand()
        brush_mode = "tint"
        if mode_roll >= 0.55 and mode_roll < 0.79:
            brush_mode = "lighten"
        elif mode_roll >= 0.79:
            brush_mode = "darken"

        color = style_colors[min(style_len - 1, int(rand() * style_len))]
        opacity = _clamp(0.03 + strength * 0.12 + rand() * 0.07, 0.02, 0.32)
        radius = (0.9 + rand() * 2.8 + strength * 2.0) * size_scale
        segment_len = max(1.0, radius * 0.8)
        steps = max(2, int(length / segment_len))
        step_distance = length / steps

        prev_x = x
        prev_y = y
        for _segment in range(steps):
            direction += curve * 0.08 + (rand() - 0.5) * 0.18
            next_x = prev_x + math.cos(direction) * step_distance
            next_y = prev_y + math.sin(direction) * step_distance
            distance = math.hypot(next_x - prev_x, next_y - prev_y)
            sample_count = max(1, int(distance / max(0.8, radius * 0.33)))
            for sample in range(sample_count + 1):
                t = sample / sample_count
                jitter = radius * 0.2
                point_x = _lerp(prev_x, next_x, t) + (rand() - 0.5) * jitter
                point_y = _lerp(prev_y, next_y, t) + (rand() - 0.5) * jitter
                dab_radius = radius * (0.65 + rand() * 0.45)
                _dab_wrapped(
                    pixels,
                    size,
                    size,
                    point_x,
                    point_y,
                    dab_radius,
                    brush_mode=brush_mode,
                    color=color,
                    opacity=opacity,
                )
            prev_x = next_x
            prev_y = next_y

    chip_count = int(36 + strength * 180)
    for _ in range(chip_count):
        dark_chip = rand() < 0.52
        brush_mode = "darken" if dark_chip else "lighten"
        opacity = 0.03 + rand() * (0.05 + strength * 0.09)
        radius = (0.5 + rand() * 1.6 + strength * 0.4) * size_scale
        _dab_wrapped(
            pixels,
            size,
            size,
            rand() * size,
            rand() * size,
            radius,
            brush_mode=brush_mode,
            color=(255, 255, 255),
            opacity=opacity,
        )


def generate_texture(params: TextureParams) -> TextureImage:
    width = params.size
    height = params.size
    pixels = bytearray(width * height * 4)
    style_stops = _parse_style_stops(params.style)

    for y in range(height):
        v = y / height
        for x in range(width):
            u = x / width
            base = _fbm(u, v, params.scale, params.octaves, params.seed, params.roughness)
            detail = _fbm(
                u + 0.217,
                v + 0.173,
                params.scale * 2,
                max(2, params.octaves - 1),
                params.seed + 991,
                _clamp(params.roughness + 0.08, 0.0, 1.4),
            )
            ridge = 1.0 - abs(detail * 2.0 - 1.0)
            tone = _tone_for_style(params.style, base, detail, ridge, u, v, params)
            tone = (tone - 0.5) * params.contrast + 0.5
            tone += (_hash2d(x, y, params.seed + 4049) - 0.5) * params.grain
            tone = _clamp(tone, 0.0, 1.0)
            red, green, blue = _sample_gradient(style_stops, tone)

            idx = (y * width + x) * 4
            pixels[idx] = red
            pixels[idx + 1] = green
            pixels[idx + 2] = blue
            pixels[idx + 3] = 255

    _apply_handcrafted_pass(pixels, params)
    return TextureImage(width=width, height=height, pixels=bytes(pixels))

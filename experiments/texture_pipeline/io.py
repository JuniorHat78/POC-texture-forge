from __future__ import annotations

import json
import struct
import zlib
from pathlib import Path
from typing import Any

from .core import TextureImage


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _chunk(chunk_type: bytes, data: bytes) -> bytes:
    length = struct.pack(">I", len(data))
    crc = zlib.crc32(chunk_type + data) & 0xFFFFFFFF
    return length + chunk_type + data + struct.pack(">I", crc)


def _encode_png(image: TextureImage) -> bytes:
    if image.width <= 0 or image.height <= 0:
        raise ValueError("image width/height must be > 0")

    row_size = image.width * 4
    if len(image.pixels) != row_size * image.height:
        raise ValueError("image pixel length does not match width/height")

    raw = bytearray()
    for y in range(image.height):
        raw.append(0)
        row_start = y * row_size
        raw.extend(image.pixels[row_start : row_start + row_size])

    compressed = zlib.compress(bytes(raw), level=9)
    ihdr = struct.pack(">IIBBBBB", image.width, image.height, 8, 6, 0, 0, 0)

    return b"".join(
        [
            PNG_SIGNATURE,
            _chunk(b"IHDR", ihdr),
            _chunk(b"IDAT", compressed),
            _chunk(b"IEND", b""),
        ]
    )


def _atomic_write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with temp_path.open("wb") as file:
        file.write(content)
    temp_path.replace(path)


def write_png(path: Path, image: TextureImage) -> None:
    _atomic_write_bytes(path, _encode_png(image))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, sort_keys=True)
    temp_path.replace(path)

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


def _paeth_predictor(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa = abs(p - a)
    pb = abs(p - b)
    pc = abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def _decode_scanlines(raw: bytes, *, width: int, height: int, channels: int) -> bytes:
    row_bytes = width * channels
    expected = height * (1 + row_bytes)
    if len(raw) != expected:
        raise ValueError("PNG payload length does not match image dimensions")

    output = bytearray(height * row_bytes)
    prior = bytearray(row_bytes)
    bpp = channels

    for y in range(height):
        src_row_start = y * (1 + row_bytes)
        filter_type = raw[src_row_start]
        src = raw[src_row_start + 1 : src_row_start + 1 + row_bytes]
        recon = bytearray(row_bytes)

        if filter_type == 0:
            recon[:] = src
        elif filter_type == 1:
            for i in range(row_bytes):
                left = recon[i - bpp] if i >= bpp else 0
                recon[i] = (src[i] + left) & 0xFF
        elif filter_type == 2:
            for i in range(row_bytes):
                up = prior[i]
                recon[i] = (src[i] + up) & 0xFF
        elif filter_type == 3:
            for i in range(row_bytes):
                left = recon[i - bpp] if i >= bpp else 0
                up = prior[i]
                recon[i] = (src[i] + ((left + up) // 2)) & 0xFF
        elif filter_type == 4:
            for i in range(row_bytes):
                left = recon[i - bpp] if i >= bpp else 0
                up = prior[i]
                up_left = prior[i - bpp] if i >= bpp else 0
                recon[i] = (src[i] + _paeth_predictor(left, up, up_left)) & 0xFF
        else:
            raise ValueError(f"Unsupported PNG filter type: {filter_type}")

        dst_row_start = y * row_bytes
        output[dst_row_start : dst_row_start + row_bytes] = recon
        prior = recon

    return bytes(output)


def _to_rgba(decoded: bytes, *, width: int, height: int, channels: int) -> bytes:
    if channels == 4:
        return decoded

    rgba = bytearray(width * height * 4)
    if channels == 3:
        src = 0
        dst = 0
        while src < len(decoded):
            rgba[dst] = decoded[src]
            rgba[dst + 1] = decoded[src + 1]
            rgba[dst + 2] = decoded[src + 2]
            rgba[dst + 3] = 255
            src += 3
            dst += 4
        return bytes(rgba)

    if channels == 1:
        src = 0
        dst = 0
        while src < len(decoded):
            lum = decoded[src]
            rgba[dst] = lum
            rgba[dst + 1] = lum
            rgba[dst + 2] = lum
            rgba[dst + 3] = 255
            src += 1
            dst += 4
        return bytes(rgba)

    raise ValueError(f"Unsupported PNG channel count: {channels}")


def _decode_png(content: bytes) -> TextureImage:
    if len(content) < len(PNG_SIGNATURE) or content[: len(PNG_SIGNATURE)] != PNG_SIGNATURE:
        raise ValueError("Invalid PNG signature")

    width = 0
    height = 0
    bit_depth = 0
    color_type = 0
    compression_method = 0
    filter_method = 0
    interlace_method = 0
    idat_parts: list[bytes] = []

    offset = len(PNG_SIGNATURE)
    seen_ihdr = False
    seen_iend = False

    while offset < len(content):
        if offset + 12 > len(content):
            raise ValueError("Truncated PNG chunk header")
        length = struct.unpack(">I", content[offset : offset + 4])[0]
        chunk_type = content[offset + 4 : offset + 8]
        data_start = offset + 8
        data_end = data_start + length
        crc_end = data_end + 4
        if crc_end > len(content):
            raise ValueError("Truncated PNG chunk data")

        chunk_data = content[data_start:data_end]
        crc_expected = struct.unpack(">I", content[data_end:crc_end])[0]
        crc_actual = zlib.crc32(chunk_type + chunk_data) & 0xFFFFFFFF
        if crc_actual != crc_expected:
            raise ValueError(f"PNG chunk CRC mismatch for {chunk_type.decode('ascii', errors='ignore')}")

        if chunk_type == b"IHDR":
            if seen_ihdr:
                raise ValueError("PNG contains multiple IHDR chunks")
            if len(chunk_data) != 13:
                raise ValueError("Invalid IHDR chunk length")
            (
                width,
                height,
                bit_depth,
                color_type,
                compression_method,
                filter_method,
                interlace_method,
            ) = struct.unpack(">IIBBBBB", chunk_data)
            seen_ihdr = True
        elif chunk_type == b"IDAT":
            idat_parts.append(chunk_data)
        elif chunk_type == b"IEND":
            seen_iend = True
            offset = crc_end
            break

        offset = crc_end

    if not seen_ihdr:
        raise ValueError("PNG is missing IHDR chunk")
    if not seen_iend:
        raise ValueError("PNG is missing IEND chunk")
    if width <= 0 or height <= 0:
        raise ValueError("PNG width/height must be > 0")
    if bit_depth != 8:
        raise ValueError(f"Unsupported PNG bit depth: {bit_depth}")
    if compression_method != 0 or filter_method != 0:
        raise ValueError("Unsupported PNG compression/filter method")
    if interlace_method != 0:
        raise ValueError("Interlaced PNG is not supported")

    channel_map = {0: 1, 2: 3, 6: 4}
    if color_type not in channel_map:
        raise ValueError(f"Unsupported PNG color type: {color_type}")
    channels = channel_map[color_type]

    if not idat_parts:
        raise ValueError("PNG is missing IDAT chunk")
    try:
        raw = zlib.decompress(b"".join(idat_parts))
    except zlib.error as exc:
        raise ValueError("Failed to decompress PNG IDAT payload") from exc

    decoded = _decode_scanlines(raw, width=width, height=height, channels=channels)
    rgba = _to_rgba(decoded, width=width, height=height, channels=channels)
    return TextureImage(width=width, height=height, pixels=rgba)


def _atomic_write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with temp_path.open("wb") as file:
        file.write(content)
    temp_path.replace(path)


def write_png(path: Path, image: TextureImage) -> None:
    _atomic_write_bytes(path, _encode_png(image))


def read_png(path: Path) -> TextureImage:
    with path.open("rb") as file:
        content = file.read()
    return _decode_png(content)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, sort_keys=True)
    temp_path.replace(path)


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)

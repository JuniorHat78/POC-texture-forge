import pathlib
import struct
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.texture_pipeline.core import TextureImage
from experiments.texture_pipeline.io import PNG_SIGNATURE, read_json, read_png, write_json, write_png


def _sample_image(width: int, height: int) -> TextureImage:
    pixels = bytearray(width * height * 4)
    for y in range(height):
        for x in range(width):
            idx = (y * width + x) * 4
            pixels[idx] = (x * 13 + y * 7) % 256
            pixels[idx + 1] = (x * 3 + y * 17) % 256
            pixels[idx + 2] = (x * 11 + y * 5) % 256
            pixels[idx + 3] = 255
    return TextureImage(width=width, height=height, pixels=bytes(pixels))


def _corrupt_first_idat_byte(content: bytes) -> bytes:
    data = bytearray(content)
    offset = len(PNG_SIGNATURE)
    while offset + 12 <= len(data):
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        chunk_type = bytes(data[offset + 4 : offset + 8])
        data_start = offset + 8
        data_end = data_start + length
        crc_end = data_end + 4
        if crc_end > len(data):
            break
        if chunk_type == b"IDAT" and length > 0:
            data[data_start] ^= 0xFF
            return bytes(data)
        offset = crc_end
    raise AssertionError("IDAT chunk not found")


class TexturePngIoTests(unittest.TestCase):
    def test_write_and_read_png_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = pathlib.Path(tmp_dir) / "sample.png"
            source = _sample_image(16, 12)
            write_png(path, source)
            decoded = read_png(path)
            self.assertEqual(decoded.width, source.width)
            self.assertEqual(decoded.height, source.height)
            self.assertEqual(decoded.pixels, source.pixels)

    def test_read_png_rejects_bad_signature(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = pathlib.Path(tmp_dir) / "bad.png"
            path.write_bytes(b"not-a-png")
            with self.assertRaises(ValueError):
                read_png(path)

    def test_read_png_rejects_truncated_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = pathlib.Path(tmp_dir) / "truncated.png"
            source = _sample_image(8, 8)
            write_png(path, source)
            content = path.read_bytes()
            path.write_bytes(content[:-5])
            with self.assertRaises(ValueError):
                read_png(path)

    def test_read_png_rejects_crc_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = pathlib.Path(tmp_dir) / "corrupt.png"
            source = _sample_image(8, 8)
            write_png(path, source)
            corrupted = _corrupt_first_idat_byte(path.read_bytes())
            path.write_bytes(corrupted)
            with self.assertRaises(ValueError):
                read_png(path)

    def test_write_and_read_json_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = pathlib.Path(tmp_dir) / "sample.json"
            payload = {"a": 1, "b": {"style": "moss"}}
            write_json(path, payload)
            loaded = read_json(path)
            self.assertEqual(loaded, payload)


if __name__ == "__main__":
    unittest.main()

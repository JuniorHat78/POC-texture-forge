import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.texture_cli import main
from experiments.texture_pipeline.core import TextureImage
from experiments.texture_pipeline.io import write_json, write_png


def _solid_image(width: int, height: int, rgba: tuple[int, int, int, int]) -> TextureImage:
    pixels = bytearray(width * height * 4)
    for idx in range(0, len(pixels), 4):
        pixels[idx] = rgba[0]
        pixels[idx + 1] = rgba[1]
        pixels[idx + 2] = rgba[2]
        pixels[idx + 3] = rgba[3]
    return TextureImage(width=width, height=height, pixels=bytes(pixels))


class InspectPngFidelityTests(unittest.TestCase):
    def test_strict_inspect_uses_actual_png_pixels(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = pathlib.Path(tmp_dir)
            texture = tmp_path / "moss-77-128-h45.png"
            write_png(texture, _solid_image(8, 8, (120, 120, 120, 255)))

            report_dir = tmp_path / "review"
            code = main(
                [
                    "inspect",
                    "--input",
                    str(tmp_path),
                    "--out",
                    str(report_dir),
                    "--quality-profile",
                    "default",
                    "--strict",
                ]
            )

            self.assertEqual(code, 3)
            report = json.loads((report_dir / "quality-report.json").read_text(encoding="utf-8"))
            summary = report["summary"]
            self.assertEqual(summary["evaluated"], 1)
            self.assertEqual(summary["pass_count"], 0)
            self.assertEqual(summary["failed_files"], [texture.name])

    def test_unparseable_stem_uses_sidecar_style_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = pathlib.Path(tmp_dir)
            texture = tmp_path / "custom_name.png"
            write_png(texture, _solid_image(8, 8, (60, 100, 160, 255)))
            write_json(
                texture.with_suffix(".json"),
                {
                    "params": {
                        "style": "lava",
                        "seed": 1234,
                        "size": 128,
                        "scale": 7,
                        "octaves": 4,
                        "roughness": 0.68,
                        "contrast": 1.12,
                        "grain": 0.06,
                        "handcraft": 0.35,
                    }
                },
            )

            report_dir = tmp_path / "review"
            code = main(["inspect", "--input", str(tmp_path), "--out", str(report_dir)])
            self.assertEqual(code, 0)

            report = json.loads((report_dir / "quality-report.json").read_text(encoding="utf-8"))
            style_breakdown = report["summary"]["style_breakdown"]
            self.assertIn("lava", style_breakdown)
            self.assertNotIn("unknown", style_breakdown)

    def test_invalid_png_is_skipped_and_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = pathlib.Path(tmp_dir)
            valid_png = tmp_path / "moss-42-128-h35.png"
            invalid_png = tmp_path / "bad-image.png"
            write_png(valid_png, _solid_image(8, 8, (90, 140, 90, 255)))
            invalid_png.write_bytes(b"not-a-png")

            report_dir = tmp_path / "review"
            code = main(["inspect", "--input", str(tmp_path), "--out", str(report_dir)])
            self.assertEqual(code, 0)

            report = json.loads((report_dir / "quality-report.json").read_text(encoding="utf-8"))
            summary = report["summary"]
            self.assertEqual(summary["evaluated"], 1)
            self.assertEqual(summary["skipped"], 1)
            self.assertIn("bad-image.png", summary["skipped_files"])

    def test_unparseable_stem_without_sidecar_maps_to_unknown_style(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = pathlib.Path(tmp_dir)
            texture = tmp_path / "totally-custom.png"
            write_png(texture, _solid_image(8, 8, (20, 30, 40, 255)))

            report_dir = tmp_path / "review"
            code = main(["inspect", "--input", str(tmp_path), "--out", str(report_dir)])
            self.assertEqual(code, 0)

            report = json.loads((report_dir / "quality-report.json").read_text(encoding="utf-8"))
            style_breakdown = report["summary"]["style_breakdown"]
            self.assertIn("unknown", style_breakdown)


if __name__ == "__main__":
    unittest.main()

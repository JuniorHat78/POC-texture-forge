import pathlib
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.texture_cli import main
from experiments.texture_pipeline.core import TextureImage
from experiments.texture_pipeline.io import write_png


def _solid_image(width: int, height: int, rgba: tuple[int, int, int, int]) -> TextureImage:
    pixels = bytearray(width * height * 4)
    for idx in range(0, len(pixels), 4):
        pixels[idx] = rgba[0]
        pixels[idx + 1] = rgba[1]
        pixels[idx + 2] = rgba[2]
        pixels[idx + 3] = rgba[3]
    return TextureImage(width=width, height=height, pixels=bytes(pixels))


class TextureCliErrorPathTests(unittest.TestCase):
    def test_batch_rejects_zero_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            code = main(
                [
                    "batch",
                    "--style",
                    "moss",
                    "--seed",
                    "1",
                    "--size",
                    "128",
                    "--count",
                    "0",
                    "--out",
                    tmp_dir,
                ]
            )
        self.assertEqual(code, 2)

    def test_inspect_rejects_missing_directory(self) -> None:
        code = main(
            [
                "inspect",
                "--input",
                "textures/does_not_exist_anywhere_12345",
                "--out",
                "textures/review/tmp_missing_dir",
            ]
        )
        self.assertEqual(code, 2)

    def test_inspect_rejects_unparseable_filenames(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            bad_name = pathlib.Path(tmp_dir) / "random-name.png"
            bad_name.write_bytes(b"not-a-real-png")

            code = main(
                [
                    "inspect",
                    "--input",
                    tmp_dir,
                    "--out",
                    str(pathlib.Path(tmp_dir) / "review"),
                ]
            )
            self.assertEqual(code, 2)

    def test_inspect_strict_fails_when_any_texture_fails_quality(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            fake_texture = pathlib.Path(tmp_dir) / "moss-10-128-h45.png"
            write_png(fake_texture, _solid_image(8, 8, (120, 120, 120, 255)))

            failing_metrics = {
                "seam_score": 0.99,
                "luminance_min": 0.0,
                "luminance_max": 1.0,
                "luminance_mean": 0.4,
                "luminance_std": 0.01,
                "luminance_spread": 1.0,
                "pass_seam": False,
                "pass_spread": True,
                "pass_std": False,
                "pass_overall": False,
            }

            with mock.patch("experiments.texture_cli.evaluate_quality", return_value=failing_metrics):
                code = main(
                    [
                        "inspect",
                        "--input",
                        tmp_dir,
                        "--out",
                        str(pathlib.Path(tmp_dir) / "review"),
                        "--strict",
                    ]
                )

            self.assertEqual(code, 3)

    def test_inspect_rejects_non_positive_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            texture = pathlib.Path(tmp_dir) / "moss-11-128-h45.png"
            write_png(texture, _solid_image(8, 8, (120, 120, 120, 255)))
            code = main(
                [
                    "inspect",
                    "--input",
                    tmp_dir,
                    "--out",
                    str(pathlib.Path(tmp_dir) / "review"),
                    "--limit",
                    "0",
                ]
            )
            self.assertEqual(code, 2)

    def test_inspect_rejects_non_positive_columns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            texture = pathlib.Path(tmp_dir) / "moss-12-128-h45.png"
            write_png(texture, _solid_image(8, 8, (120, 120, 120, 255)))
            code = main(
                [
                    "inspect",
                    "--input",
                    tmp_dir,
                    "--out",
                    str(pathlib.Path(tmp_dir) / "review"),
                    "--columns",
                    "0",
                ]
            )
            self.assertEqual(code, 2)

    def test_matrix_rejects_bad_style_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            code = main(
                [
                    "matrix",
                    "--styles",
                    "moss,unknown",
                    "--seed",
                    "500",
                    "--size",
                    "128",
                    "--count-per-style",
                    "1",
                    "--out",
                    tmp_dir,
                ]
            )
            self.assertEqual(code, 2)

    def test_matrix_rejects_non_positive_count_per_style(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            code = main(
                [
                    "matrix",
                    "--styles",
                    "all",
                    "--seed",
                    "500",
                    "--size",
                    "128",
                    "--count-per-style",
                    "0",
                    "--out",
                    tmp_dir,
                ]
            )
            self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()

import pathlib
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.texture_cli import main


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
            fake_texture.write_bytes(b"placeholder")

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

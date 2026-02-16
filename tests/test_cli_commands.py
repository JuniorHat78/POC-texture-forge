import pathlib
import sys
import tempfile
import unittest
import json

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.texture_cli import main


class TextureCliTests(unittest.TestCase):
    def test_render_dry_run_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            code = main(
                [
                    "render",
                    "--style",
                    "moss",
                    "--seed",
                    "42",
                    "--size",
                    "128",
                    "--dry-run",
                    "--out",
                    tmp_dir,
                ]
            )
            self.assertEqual(code, 0)
            pngs = list(pathlib.Path(tmp_dir).glob("*.png"))
            self.assertEqual(len(pngs), 0)

    def test_render_creates_png(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            code = main(
                [
                    "render",
                    "--style",
                    "moss",
                    "--seed",
                    "42",
                    "--size",
                    "128",
                    "--out",
                    tmp_dir,
                ]
            )
            self.assertEqual(code, 0)
            pngs = list(pathlib.Path(tmp_dir).glob("*.png"))
            self.assertEqual(len(pngs), 1)

    def test_batch_creates_many_pngs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            code = main(
                [
                    "batch",
                    "--style",
                    "lava",
                    "--seed",
                    "100",
                    "--size",
                    "128",
                    "--count",
                    "2",
                    "--out",
                    tmp_dir,
                ]
            )
            self.assertEqual(code, 0)
            pngs = list(pathlib.Path(tmp_dir).glob("*.png"))
            self.assertEqual(len(pngs), 2)

    def test_batch_dry_run_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            code = main(
                [
                    "batch",
                    "--style",
                    "lava",
                    "--seed",
                    "100",
                    "--size",
                    "128",
                    "--count",
                    "2",
                    "--dry-run",
                    "--out",
                    tmp_dir,
                ]
            )
            self.assertEqual(code, 0)
            pngs = list(pathlib.Path(tmp_dir).glob("*.png"))
            self.assertEqual(len(pngs), 0)

    def test_matrix_all_styles_generates_expected_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            code = main(
                [
                    "matrix",
                    "--styles",
                    "all",
                    "--seed",
                    "300",
                    "--size",
                    "128",
                    "--count-per-style",
                    "1",
                    "--out",
                    tmp_dir,
                ]
            )
            self.assertEqual(code, 0)
            pngs = list(pathlib.Path(tmp_dir).glob("*.png"))
            self.assertEqual(len(pngs), 6)

    def test_matrix_subset_generates_expected_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            code = main(
                [
                    "matrix",
                    "--styles",
                    "moss,lava",
                    "--seed",
                    "400",
                    "--size",
                    "128",
                    "--count-per-style",
                    "2",
                    "--out",
                    tmp_dir,
                ]
            )
            self.assertEqual(code, 0)
            pngs = list(pathlib.Path(tmp_dir).glob("*.png"))
            self.assertEqual(len(pngs), 4)

    def test_matrix_dry_run_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            code = main(
                [
                    "matrix",
                    "--styles",
                    "moss,lava",
                    "--seed",
                    "410",
                    "--size",
                    "128",
                    "--count-per-style",
                    "2",
                    "--dry-run",
                    "--out",
                    tmp_dir,
                ]
            )
            self.assertEqual(code, 0)
            pngs = list(pathlib.Path(tmp_dir).glob("*.png"))
            self.assertEqual(len(pngs), 0)

    def test_inspect_generates_report_and_contact_sheet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            render_code = main(
                [
                    "batch",
                    "--style",
                    "sand",
                    "--seed",
                    "200",
                    "--size",
                    "128",
                    "--count",
                    "2",
                    "--out",
                    tmp_dir,
                ]
            )
            self.assertEqual(render_code, 0)

            report_dir = pathlib.Path(tmp_dir) / "review"
            inspect_code = main(
                [
                    "inspect",
                    "--input",
                    tmp_dir,
                    "--out",
                    str(report_dir),
                ]
            )
            self.assertEqual(inspect_code, 0)
            self.assertTrue((report_dir / "quality-report.json").exists())
            self.assertTrue((report_dir / "contact-sheet.png").exists())

    def test_inspect_records_quality_profile_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            render_code = main(
                [
                    "batch",
                    "--style",
                    "moss",
                    "--seed",
                    "101",
                    "--size",
                    "128",
                    "--count",
                    "1",
                    "--out",
                    tmp_dir,
                ]
            )
            self.assertEqual(render_code, 0)

            report_dir = pathlib.Path(tmp_dir) / "review"
            inspect_code = main(
                [
                    "inspect",
                    "--input",
                    tmp_dir,
                    "--out",
                    str(report_dir),
                    "--quality-profile",
                    "strict",
                ]
            )
            self.assertEqual(inspect_code, 0)

            report = json.loads((report_dir / "quality-report.json").read_text(encoding="utf-8"))
            summary = report["summary"]
            self.assertEqual(summary["quality_profile"], "strict")
            self.assertIn("quality_thresholds", summary)
            self.assertIn("max_seam_score", summary["quality_thresholds"])

    def test_inspect_timestamped_writes_nested_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            render_code = main(
                [
                    "batch",
                    "--style",
                    "sand",
                    "--seed",
                    "111",
                    "--size",
                    "128",
                    "--count",
                    "1",
                    "--out",
                    tmp_dir,
                ]
            )
            self.assertEqual(render_code, 0)

            report_dir = pathlib.Path(tmp_dir) / "review"
            inspect_code = main(
                [
                    "inspect",
                    "--input",
                    tmp_dir,
                    "--out",
                    str(report_dir),
                    "--timestamped",
                ]
            )
            self.assertEqual(inspect_code, 0)

            reports = list(report_dir.rglob("quality-report.json"))
            sheets = list(report_dir.rglob("contact-sheet.png"))
            self.assertEqual(len(reports), 1)
            self.assertEqual(len(sheets), 1)
            self.assertNotEqual(reports[0].parent, report_dir)


if __name__ == "__main__":
    unittest.main()

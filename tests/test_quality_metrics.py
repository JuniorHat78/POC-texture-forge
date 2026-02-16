import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.texture_pipeline.contract import TextureParams
from experiments.texture_pipeline.core import generate_texture
from experiments.texture_pipeline.quality import QualityThresholds, contact_sheet, evaluate_quality


class TextureQualityMetricTests(unittest.TestCase):
    def test_quality_metrics_have_expected_keys(self) -> None:
        params = TextureParams.from_overrides({"style": "ice", "seed": 9001, "size": 128})
        image = generate_texture(params)
        metrics = evaluate_quality(image)
        self.assertIn("seam_score", metrics)
        self.assertIn("luminance_spread", metrics)
        self.assertIn("pass_overall", metrics)
        self.assertGreaterEqual(float(metrics["luminance_spread"]), 0.0)

    def test_contact_sheet_dimensions(self) -> None:
        params = TextureParams.from_overrides({"style": "metal", "seed": 777, "size": 128})
        images = [generate_texture(params), generate_texture(params), generate_texture(params)]
        sheet = contact_sheet(images, columns=2, padding=2)
        self.assertEqual(sheet.width, 2 * 128 + 3 * 2)
        self.assertEqual(sheet.height, 2 * 128 + 3 * 2)

    def test_custom_thresholds_are_applied(self) -> None:
        params = TextureParams.from_overrides({"style": "ice", "seed": 99, "size": 128})
        image = generate_texture(params)
        thresholds = QualityThresholds(
            max_seam_score=0.0,
            min_luminance_spread=0.95,
            min_luminance_std=0.4,
        )
        metrics = evaluate_quality(image, thresholds=thresholds)
        self.assertFalse(bool(metrics["pass_overall"]))
        self.assertFalse(bool(metrics["pass_seam"]))
        self.assertFalse(bool(metrics["pass_spread"]))
        self.assertFalse(bool(metrics["pass_std"]))


if __name__ == "__main__":
    unittest.main()

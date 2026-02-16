import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.texture_pipeline.core import TextureImage
from experiments.texture_pipeline.quality import evaluate_quality


class TextureQualityRegressionTests(unittest.TestCase):
    def test_flat_texture_fails_quality_thresholds(self) -> None:
        width = 64
        height = 64
        pixels = bytearray(width * height * 4)
        for idx in range(0, len(pixels), 4):
            pixels[idx] = 120
            pixels[idx + 1] = 120
            pixels[idx + 2] = 120
            pixels[idx + 3] = 255

        image = TextureImage(width=width, height=height, pixels=bytes(pixels))
        metrics = evaluate_quality(image)

        self.assertFalse(bool(metrics["pass_overall"]))
        self.assertFalse(bool(metrics["pass_spread"]))
        self.assertFalse(bool(metrics["pass_std"]))


if __name__ == "__main__":
    unittest.main()

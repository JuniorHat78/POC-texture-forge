import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.texture_pipeline.contract import TextureParams


class TextureParamsValidationTests(unittest.TestCase):
    def test_accepts_valid_defaults(self) -> None:
        params = TextureParams.from_overrides({"style": "moss", "seed": 42})
        self.assertEqual(params.style, "moss")
        self.assertEqual(params.seed, 42)
        self.assertEqual(params.size, 256)

    def test_rejects_unknown_style(self) -> None:
        with self.assertRaises(ValueError):
            TextureParams.from_overrides({"style": "unknown-style", "seed": 7})

    def test_rejects_invalid_size(self) -> None:
        with self.assertRaises(ValueError):
            TextureParams.from_overrides({"style": "moss", "seed": 7, "size": 300})

    def test_rejects_out_of_range_roughness(self) -> None:
        with self.assertRaises(ValueError):
            TextureParams.from_overrides({"style": "moss", "seed": 7, "roughness": 1.6})


if __name__ == "__main__":
    unittest.main()

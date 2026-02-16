import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.texture_pipeline.contract import TextureParams


class TextureContractBoundsTests(unittest.TestCase):
    def test_rejects_negative_seed(self) -> None:
        with self.assertRaises(ValueError):
            TextureParams.from_overrides({"style": "moss", "seed": -1})

    def test_rejects_scale_out_of_range(self) -> None:
        with self.assertRaises(ValueError):
            TextureParams.from_overrides({"style": "moss", "seed": 1, "scale": 1})
        with self.assertRaises(ValueError):
            TextureParams.from_overrides({"style": "moss", "seed": 1, "scale": 33})

    def test_rejects_octaves_out_of_range(self) -> None:
        with self.assertRaises(ValueError):
            TextureParams.from_overrides({"style": "moss", "seed": 1, "octaves": 0})
        with self.assertRaises(ValueError):
            TextureParams.from_overrides({"style": "moss", "seed": 1, "octaves": 9})

    def test_rejects_contrast_out_of_range(self) -> None:
        with self.assertRaises(ValueError):
            TextureParams.from_overrides({"style": "moss", "seed": 1, "contrast": 0.39})
        with self.assertRaises(ValueError):
            TextureParams.from_overrides({"style": "moss", "seed": 1, "contrast": 3.1})

    def test_rejects_grain_out_of_range(self) -> None:
        with self.assertRaises(ValueError):
            TextureParams.from_overrides({"style": "moss", "seed": 1, "grain": -0.01})
        with self.assertRaises(ValueError):
            TextureParams.from_overrides({"style": "moss", "seed": 1, "grain": 0.61})

    def test_rejects_handcraft_out_of_range(self) -> None:
        with self.assertRaises(ValueError):
            TextureParams.from_overrides({"style": "moss", "seed": 1, "handcraft": -0.01})
        with self.assertRaises(ValueError):
            TextureParams.from_overrides({"style": "moss", "seed": 1, "handcraft": 1.01})

    def test_rejects_bool_for_integer_fields(self) -> None:
        with self.assertRaises(ValueError):
            TextureParams.from_overrides({"style": "moss", "seed": True})
        with self.assertRaises(ValueError):
            TextureParams.from_overrides({"style": "moss", "seed": 1, "scale": False})

    def test_rejects_bool_for_float_fields(self) -> None:
        with self.assertRaises(ValueError):
            TextureParams.from_overrides({"style": "moss", "seed": 1, "roughness": True})
        with self.assertRaises(ValueError):
            TextureParams.from_overrides({"style": "moss", "seed": 1, "contrast": False})

    def test_filename_roundtrip_accepts_uppercase_style(self) -> None:
        params = TextureParams.from_filename_stem("MOSS-42-128-h35")
        self.assertEqual(params.style, "moss")
        self.assertEqual(params.seed, 42)
        self.assertEqual(params.size, 128)
        self.assertAlmostEqual(params.handcraft, 0.35, places=2)


if __name__ == "__main__":
    unittest.main()

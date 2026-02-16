import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.texture_pipeline.contract import TextureParams


class TextureContractRoundtripTests(unittest.TestCase):
    def test_filename_roundtrip_preserves_core_identity(self) -> None:
        original = TextureParams.from_overrides(
            {
                "style": "toxic",
                "seed": 987654,
                "size": 512,
                "handcraft": 0.58,
            }
        )
        stem = original.to_filename_stem()
        reconstructed = TextureParams.from_filename_stem(stem)

        self.assertEqual(reconstructed.style, original.style)
        self.assertEqual(reconstructed.seed, original.seed)
        self.assertEqual(reconstructed.size, original.size)
        self.assertAlmostEqual(reconstructed.handcraft, original.handcraft, places=2)

    def test_overrides_take_precedence_over_preset(self) -> None:
        params = TextureParams.from_overrides(
            {
                "style": "ice",
                "scale": 12,
            },
            preset_name="subtle",
        )
        self.assertEqual(params.style, "ice")
        self.assertEqual(params.scale, 12)

    def test_rejects_bad_filename_stem(self) -> None:
        with self.assertRaises(ValueError):
            TextureParams.from_filename_stem("not-a-valid-stem")


if __name__ == "__main__":
    unittest.main()

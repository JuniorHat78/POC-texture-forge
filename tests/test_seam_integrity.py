import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.texture_pipeline.contract import TextureParams
from experiments.texture_pipeline.core import generate_texture
from experiments.texture_pipeline.quality import edge_mismatch_score


class TextureSeamIntegrityTests(unittest.TestCase):
    def test_edge_mismatch_is_reasonable_for_tileable_texture(self) -> None:
        params = TextureParams.from_overrides(
            {"style": "moss", "seed": 12345, "size": 128, "handcraft": 0.3}
        )
        image = generate_texture(params)
        mismatch = edge_mismatch_score(image)
        self.assertLess(mismatch, 0.28)


if __name__ == "__main__":
    unittest.main()

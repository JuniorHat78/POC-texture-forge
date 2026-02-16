import hashlib
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.texture_pipeline.contract import TextureParams
from experiments.texture_pipeline.core import generate_texture


def texture_digest(params: TextureParams) -> str:
    image = generate_texture(params)
    return hashlib.sha256(image.pixels).hexdigest()


class TextureDeterminismTests(unittest.TestCase):
    def test_same_seed_is_identical(self) -> None:
        a = TextureParams.from_overrides({"style": "lava", "seed": 1001, "size": 128})
        b = TextureParams.from_overrides({"style": "lava", "seed": 1001, "size": 128})
        self.assertEqual(texture_digest(a), texture_digest(b))

    def test_different_seed_is_not_identical(self) -> None:
        a = TextureParams.from_overrides({"style": "lava", "seed": 1001, "size": 128})
        b = TextureParams.from_overrides({"style": "lava", "seed": 1002, "size": 128})
        self.assertNotEqual(texture_digest(a), texture_digest(b))


if __name__ == "__main__":
    unittest.main()

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.texture_pipeline.core import TextureImage
from experiments.texture_pipeline.quality import contact_sheet, edge_mismatch_score, luminance_summary


def _solid_image(width: int, height: int, rgba: tuple[int, int, int, int]) -> TextureImage:
    pixels = bytearray(width * height * 4)
    for idx in range(0, len(pixels), 4):
        pixels[idx] = rgba[0]
        pixels[idx + 1] = rgba[1]
        pixels[idx + 2] = rgba[2]
        pixels[idx + 3] = rgba[3]
    return TextureImage(width=width, height=height, pixels=bytes(pixels))


class TextureQualityEdgeCaseTests(unittest.TestCase):
    def test_contact_sheet_rejects_empty_images(self) -> None:
        with self.assertRaises(ValueError):
            contact_sheet([], columns=2, padding=2)

    def test_contact_sheet_rejects_non_positive_columns(self) -> None:
        image = _solid_image(8, 8, (1, 2, 3, 255))
        with self.assertRaises(ValueError):
            contact_sheet([image], columns=0, padding=2)

    def test_contact_sheet_rejects_mismatched_dimensions(self) -> None:
        image_a = _solid_image(8, 8, (1, 2, 3, 255))
        image_b = _solid_image(9, 8, (1, 2, 3, 255))
        with self.assertRaises(ValueError):
            contact_sheet([image_a, image_b], columns=2, padding=2)

    def test_edge_mismatch_is_zero_for_single_pixel(self) -> None:
        image = _solid_image(1, 1, (20, 30, 40, 255))
        self.assertEqual(edge_mismatch_score(image), 0.0)

    def test_luminance_summary_handles_empty_pixel_buffer(self) -> None:
        image = TextureImage(width=0, height=0, pixels=b"")
        summary = luminance_summary(image)
        self.assertEqual(summary["min"], 0.0)
        self.assertEqual(summary["max"], 0.0)
        self.assertEqual(summary["spread"], 0.0)


if __name__ == "__main__":
    unittest.main()

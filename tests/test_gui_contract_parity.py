import json
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


HTML_PATH = ROOT / "experiments" / "texture-lab.html"
PRESETS_PATH = ROOT / "experiments" / "texture-presets.json"


def _find_input_value(html: str, element_id: str) -> str:
    pattern = re.compile(rf'<input[^>]*id="{re.escape(element_id)}"[^>]*value="([^"]+)"', re.IGNORECASE)
    match = pattern.search(html)
    if not match:
        raise AssertionError(f"Could not find input default for id '{element_id}'")
    return match.group(1)


def _find_select_default(html: str, element_id: str) -> str:
    block_pattern = re.compile(
        rf'<select[^>]*id="{re.escape(element_id)}"[^>]*>(.*?)</select>',
        re.IGNORECASE | re.DOTALL,
    )
    block_match = block_pattern.search(html)
    if not block_match:
        raise AssertionError(f"Could not find select block for id '{element_id}'")

    block = block_match.group(1)
    selected = re.search(r'<option[^>]*value="([^"]+)"[^>]*selected', block, re.IGNORECASE)
    if selected:
        return selected.group(1)

    first = re.search(r'<option[^>]*value="([^"]+)"', block, re.IGNORECASE)
    if not first:
        raise AssertionError(f"Could not find option values for select id '{element_id}'")
    return first.group(1)


def _find_select_options(html: str, element_id: str) -> list[str]:
    block_pattern = re.compile(
        rf'<select[^>]*id="{re.escape(element_id)}"[^>]*>(.*?)</select>',
        re.IGNORECASE | re.DOTALL,
    )
    block_match = block_pattern.search(html)
    if not block_match:
        raise AssertionError(f"Could not find select block for id '{element_id}'")
    block = block_match.group(1)
    return re.findall(r'<option[^>]*value="([^"]+)"', block, re.IGNORECASE)


class GuiContractParityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.html = HTML_PATH.read_text(encoding="utf-8")
        self.presets = json.loads(PRESETS_PATH.read_text(encoding="utf-8"))
        self.defaults = self.presets["defaults"]

    def test_gui_defaults_match_contract_defaults(self) -> None:
        self.assertEqual(_find_select_default(self.html, "styleSelect"), self.defaults["style"])
        self.assertEqual(int(_find_input_value(self.html, "seedInput")), int(self.defaults["seed"]))
        self.assertEqual(int(_find_select_default(self.html, "sizeSelect")), int(self.defaults["size"]))
        self.assertEqual(int(_find_input_value(self.html, "scaleInput")), int(self.defaults["scale"]))
        self.assertEqual(int(_find_input_value(self.html, "octavesInput")), int(self.defaults["octaves"]))
        self.assertEqual(int(_find_input_value(self.html, "roughnessInput")), int(round(self.defaults["roughness"] * 100)))
        self.assertEqual(int(_find_input_value(self.html, "contrastInput")), int(round(self.defaults["contrast"] * 100)))
        self.assertEqual(int(_find_input_value(self.html, "grainInput")), int(round(self.defaults["grain"] * 100)))
        self.assertEqual(int(_find_input_value(self.html, "handcraftInput")), int(round(self.defaults["handcraft"] * 100)))

    def test_gui_size_options_match_allowed_sizes(self) -> None:
        allowed_sizes = sorted(int(value) for value in self.presets["allowed_sizes"])
        html_sizes = sorted(int(value) for value in _find_select_options(self.html, "sizeSelect"))
        self.assertEqual(html_sizes, allowed_sizes)


if __name__ == "__main__":
    unittest.main()

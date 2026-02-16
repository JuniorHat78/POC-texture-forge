import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

HTML_PATH = ROOT / "experiments" / "texture-lab.html"
UI_JS_PATH = ROOT / "experiments" / "texture-lab.ui.js"
ENGINE_JS_PATH = ROOT / "experiments" / "texture-lab.engine.js"
HANDCRAFT_JS_PATH = ROOT / "experiments" / "texture-lab.handcraft.js"
WORKER_JS_PATH = ROOT / "experiments" / "texture-lab.worker.js"


def _has_element_id(html: str, element_id: str) -> bool:
    pattern = re.compile(rf'id="{re.escape(element_id)}"', re.IGNORECASE)
    return bool(pattern.search(html))


class GuiPowerFeaturesTests(unittest.TestCase):
    def test_html_has_undo_redo_buttons_and_status_line(self) -> None:
        html = HTML_PATH.read_text(encoding="utf-8")
        self.assertTrue(_has_element_id(html, "undoPaintBtn"))
        self.assertTrue(_has_element_id(html, "redoPaintBtn"))
        self.assertTrue(_has_element_id(html, "renderStatus"))

    def test_html_mentions_hotkeys(self) -> None:
        html = HTML_PATH.read_text(encoding="utf-8")
        self.assertIn("Ctrl/Cmd+Z", html)
        self.assertIn("Ctrl/Cmd+Shift+Z", html)

    def test_engine_references_worker_rendering(self) -> None:
        source = ENGINE_JS_PATH.read_text(encoding="utf-8")
        self.assertIn("texture-lab.worker.js", source)
        self.assertIn("pendingRenderId", source)
        self.assertIn("setRenderBusy", source)

    def test_handcraft_exposes_undo_and_redo_actions(self) -> None:
        source = HANDCRAFT_JS_PATH.read_text(encoding="utf-8")
        self.assertIn("function undoPaintAction()", source)
        self.assertIn("function redoPaintAction()", source)
        self.assertIn("Lab.undoPaintAction = undoPaintAction", source)
        self.assertIn("Lab.redoPaintAction = redoPaintAction", source)

    def test_ui_wires_hotkeys_and_buttons(self) -> None:
        source = UI_JS_PATH.read_text(encoding="utf-8")
        self.assertIn("document.addEventListener(\"keydown\", handleHotkeys)", source)
        self.assertIn("d.undoPaintBtn.addEventListener(\"click\"", source)
        self.assertIn("d.redoPaintBtn.addEventListener(\"click\"", source)

    def test_worker_file_exists_and_handles_render_message(self) -> None:
        self.assertTrue(WORKER_JS_PATH.exists())
        source = WORKER_JS_PATH.read_text(encoding="utf-8")
        self.assertIn("self.addEventListener(\"message\"", source)
        self.assertIn("type: \"rendered\"", source)


if __name__ == "__main__":
    unittest.main()

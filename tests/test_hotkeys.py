import sys
import types

import pytest

sys.modules['keyboard'] = types.SimpleNamespace(add_hotkey=lambda *a, **k: None, wait=lambda: None)
sys.modules['llama_cpp'] = types.SimpleNamespace(Llama=object)

from config import Config
from utils.hotkeys import HotkeyManager

class Dummy:
    def __init__(self):
        self.started = False
    def start(self):
        self.started = True
    def stop(self):
        self.started = False


def test_toggle_translation():
    cfg = Config()
    ocr = Dummy()
    overlay = Dummy()
    translator = Dummy()

    hk = HotkeyManager(config=cfg, ocr=ocr, overlay=overlay, translator=translator)

    hk._toggle_translation()
    assert ocr.started and overlay.started and translator.started

    hk._toggle_translation()
    assert not ocr.started and not overlay.started and not translator.started

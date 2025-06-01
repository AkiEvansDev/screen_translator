"""
Handles global hotkey registration and triggering actions such as
screen region selection and toggling translation mode.
"""

import logging
import threading
import keyboard

from typing import Callable
from config import Config
from utils.screenshot import select_screen_region

class HotkeyManager:
    """Manages hotkeys for the Screen Translator app."""

    def __init__(self, config: Config, ocr, overlay):
        """
        Initialize the hotkey manager.

        Args:
            config (Config): App configuration.
            ocr (OCRProcessor): OCR component.
            overlay (TranslationOverlay): UI component.
        """
        self.config = config
        self.ocr = ocr
        self.overlay = overlay
        self.translation_enabled = False

    def listen(self) -> None:
        """Start listening for global hotkeys."""
        logging.info("Hotkey listener started.")

        keyboard.add_hotkey(self.config.hotkey_select_region, self._select_ocr_region)
        keyboard.add_hotkey(self.config.hotkey_set_output_region, self._select_output_region)
        keyboard.add_hotkey(self.config.hotkey_toggle_translation, self._toggle_translation)

        keyboard.wait()

    def _select_ocr_region(self) -> None:
        """Callback for selecting OCR capture region."""
        region = select_screen_region()
        if region:
            self.ocr.set_region(region)
            logging.info(f"OCR region set to {region}")

    def _select_output_region(self) -> None:
        """Callback for selecting output overlay region."""
        region = select_screen_region()
        if region:
            self.overlay.set_region(region)
            logging.info(f"Output region set to {region}")

    def _toggle_translation(self) -> None:
        """Enable or disable live translation."""
        self.translation_enabled = not self.translation_enabled
        if self.translation_enabled:
            self.ocr.start()
            self.overlay.start()
            logging.info("Translation enabled.")
        else:
            self.ocr.stop()
            self.overlay.stop()
            logging.info("Translation disabled.")
"""
Main entry point for the Screen Translator application.
Initializes OCR, translation, UI, and hotkey listener components.
"""

import logging
import threading
import time
from queue import Queue
from utils.hotkeys import HotkeyManager
from ocr.ocr_processor import OCRProcessor
from translator.translator import LLMTranslator
from ui.overlay_window import TranslationOverlay
from config import Config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def main():
    try:
        logging.info("Starting Screen Translator...")

        # Communication queues
        ocr_text_queue = Queue()
        translated_text_queue = Queue()

        # Instantiate components
        config = Config()
        ocr = OCRProcessor(config=config, output_queue=ocr_text_queue)
        translator = LLMTranslator(config=config, input_queue=ocr_text_queue, output_queue=translated_text_queue)
        overlay = TranslationOverlay(config=config, input_queue=translated_text_queue)
        hotkeys = HotkeyManager(config=config, ocr=ocr, overlay=overlay, translator=translator)

        # Start hotkey listener
        hotkey_thread = threading.Thread(target=hotkeys.listen, daemon=True)
        hotkey_thread.start()

        # Main loop placeholder
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logging.info("Screen Translator stopped by user.")
    except Exception as e:
        logging.exception("Unexpected error: %s", e)

if __name__ == "__main__":
    main()
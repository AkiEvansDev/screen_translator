"""
OCRProcessor handles screen region capture and text extraction using PaddleOCR.
"""

import logging
import threading
import time
from typing import Optional, Tuple
from queue import Queue
import mss
import numpy as np
import cv2
from paddleocr import PaddleOCR

from config import Config

Region = Tuple[int, int, int, int]  # (left, top, width, height)

class OCRProcessor:
    """Handles periodic OCR capture and text extraction."""

    def __init__(self, config: Config, output_queue: Queue):
        """
        Args:
            config (Config): App configuration.
            output_queue (Queue): Queue to send recognized text to.
        """
        self.config = config
        self.output_queue = output_queue
        self.region: Optional[Region] = None
        self.ocr = PaddleOCR(use_angle_cls=True, lang='en')  # Customize language if needed

        self._running = False
        self._thread = None
        self._lock = threading.Lock()

    def set_region(self, region: Region) -> None:
        """Update the region of the screen to capture."""
        with self._lock:
            self.region = region

    def start(self) -> None:
        """Start the OCR thread."""
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
            logging.info("OCR processing started.")

    def stop(self) -> None:
        """Stop the OCR thread."""
        self._running = False
        if self._thread:
            self._thread.join()
            logging.info("OCR processing stopped.")

    def _run(self) -> None:
        """Main loop for capturing and processing screen images."""
        with mss.mss() as sct:
            while self._running:
                region = self._get_region()
                if not region:
                    time.sleep(1)
                    continue

                try:
                    screenshot = sct.grab({
                        "left": region[0],
                        "top": region[1],
                        "width": region[2],
                        "height": region[3],
                    })
                    image = np.array(screenshot)
                    image = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)

                    result = self.ocr.ocr(image, cls=True)
                    text = self._extract_text(result)

                    if text:
                        self.output_queue.put(text)
                        logging.debug(f"OCR text: {text}")

                except Exception as e:
                    logging.error(f"OCR capture failed: {e}")

                time.sleep(self.config.ocr_interval)

    def _get_region(self) -> Optional[Region]:
        """Thread-safe access to the region."""
        with self._lock:
            return self.region

    @staticmethod
    def _extract_text(ocr_result) -> str:
        """Join detected OCR lines into a single string."""
        lines = []
        for line in ocr_result[0]:
            text, _ = line[1]
            lines.append(text)
        return "\n".join(lines).strip()

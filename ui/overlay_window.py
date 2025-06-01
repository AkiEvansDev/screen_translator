"""
Displays a transparent, always-on-top, click-through overlay with translated text.
"""

import logging
import threading
import tkinter as tk
from queue import Queue, Empty
from typing import Optional, Tuple
from config import Config

Region = Tuple[int, int, int, int]

class TranslationOverlay:
    """Displays translated text in a transparent overlay."""

    def __init__(self, config: Config, input_queue: Queue):
        """
        Args:
            config (Config): App config.
            input_queue (Queue): Queue containing translated strings.
        """
        self.config = config
        self.input_queue = input_queue
        self.region: Optional[Region] = None

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._root: Optional[tk.Tk] = None
        self._label: Optional[tk.Label] = None

    def set_region(self, region: Region) -> None:
        """Set position and size of the overlay."""
        self.region = region

    def start(self) -> None:
        """Start overlay UI in a background thread."""
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
            logging.info("Translation overlay started.")

    def stop(self) -> None:
        """Stop the overlay UI."""
        self._running = False
        if self._root:
            # Ensure Tk operations run in the UI thread
            self._root.after(0, self._root.quit)
        if self._thread:
            self._thread.join()
            logging.info("Translation overlay stopped.")

    def _run(self) -> None:
        """Run Tkinter overlay window loop."""
        self._root = tk.Tk()
        self._root.title("Screen Translator Overlay")
        self._root.overrideredirect(True)
        self._root.attributes("-topmost", True)
        self._root.attributes("-transparentcolor", "black")
        self._root.config(bg="black")

        if self.region:
            x, y, w, h = self.region
            self._root.geometry(f"{w}x{h}+{x}+{y}")

        self._label = tk.Label(
            self._root,
            text="",
            font=(self.config.default_overlay_font, self.config.default_overlay_font_size),
            fg="white",
            bg="black",
            justify="left",
            wraplength=self.config.overlay_wrap_length,
        )
        self._label.pack(expand=True, fill="both")

        self._update_loop()
        self._root.mainloop()

    def _update_loop(self) -> None:
        """Fetch latest translation from queue and update label."""
        def poll():
            if not self._running:
                return
            try:
                text = self.input_queue.get_nowait()
                self._label.config(text=text)
            except Empty:
                pass
            self._root.after(500, poll)

        self._root.after(500, poll)

import threading
import time
import sys
import ctypes
from typing import Optional, Tuple

import keyboard
import easyocr
import numpy as np
from PIL import ImageGrab, ImageOps, Image
import tkinter as tk
from llama_cpp import Llama

from config import Config


def make_window_clickthrough(hwnd: int):
    """Make a window transparent for mouse/keyboard events (Windows only)."""
    if sys.platform != "win32":
        return
    GWL_EXSTYLE = -20
    WS_EX_LAYERED = 0x00080000
    WS_EX_TRANSPARENT = 0x00000020
    style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    style |= WS_EX_LAYERED | WS_EX_TRANSPARENT
    ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)


class RegionSelector:
    """Interactive region selector using Tkinter."""

    def select(self) -> Optional[Tuple[int, int, int, int]]:
        result = {}
        root = tk.Tk()
        root.attributes("-fullscreen", True)
        root.attributes("-alpha", 0.3)
        root.attributes("-topmost", True)
        root.config(cursor="cross")
        canvas = tk.Canvas(root, bg="black")
        canvas.pack(fill=tk.BOTH, expand=True)
        rect = None
        start = [0, 0]

        def on_press(event):
            nonlocal rect
            start[0], start[1] = event.x, event.y
            rect = canvas.create_rectangle(start[0], start[1], event.x, event.y, outline="red")

        def on_move(event):
            if rect:
                canvas.coords(rect, start[0], start[1], event.x, event.y)

        def on_release(event):
            end = (event.x, event.y)
            x1, y1 = start
            x2, y2 = end
            left = min(x1, x2)
            top = min(y1, y2)
            right = max(x1, x2)
            bottom = max(y1, y2)
            result["box"] = (left, top, right, bottom)
            root.destroy()

        canvas.bind("<ButtonPress-1>", on_press)
        canvas.bind("<B1-Motion>", on_move)
        canvas.bind("<ButtonRelease-1>", on_release)
        root.mainloop()
        return result.get("box")


class OverlayWindow(threading.Thread):
    """Semi-transparent overlay window for displaying translated text."""

    def __init__(self, region: Tuple[int, int, int, int], cfg: Config):
        super().__init__(daemon=True)
        self.region = region
        self.cfg = cfg
        self.root = None
        self.label = None

    def run(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.5)
        x1, y1, x2, y2 = self.region
        self.root.geometry(f"{x2 - x1}x{y2 - y1}+{x1}+{y1}")
        self.root.configure(bg="black")
        self.label = tk.Label(
            self.root,
            fg="white",
            bg="black",
            font=(self.cfg.default_overlay_font, self.cfg.default_overlay_font_size),
            justify="left",
            wraplength=self.cfg.overlay_wrap_length,
        )
        self.label.pack(fill=tk.BOTH, expand=True)
        make_window_clickthrough(self.root.winfo_id())
        self.root.mainloop()

    def set_text(self, text: str):
        if self.label:
            self.label.config(text=text)


class ScreenTranslator:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.ocr_region: Optional[Tuple[int, int, int, int]] = None
        self.overlay_region: Optional[Tuple[int, int, int, int]] = None
        self.overlay: Optional[OverlayWindow] = None
        self.enabled = False
        self.llm = Llama(model_path=cfg.llm_model_path, n_gpu_layers=cfg.llm_gpu_layers, main_gpu=cfg.llm_gpu_index)
        self.reader = easyocr.Reader(["en"], gpu=False)
        keyboard.add_hotkey(cfg.hotkey_select_region, self.set_ocr_region)
        keyboard.add_hotkey(cfg.hotkey_set_output_region, self.set_output_region)
        keyboard.add_hotkey(cfg.hotkey_toggle_translation, self.toggle)

    def set_ocr_region(self):
        selector = RegionSelector()
        region = selector.select()
        if region:
            self.ocr_region = region
            print(f"OCR region set to {region}")

    def set_output_region(self):
        selector = RegionSelector()
        region = selector.select()
        if region:
            self.overlay_region = region
            if self.overlay:
                self.overlay.root.destroy()
            self.overlay = OverlayWindow(region, self.cfg)
            self.overlay.start()
            print(f"Output region set to {region}")

    def toggle(self):
        self.enabled = not self.enabled
        state = "enabled" if self.enabled else "disabled"
        print(f"Translation {state}")

    def extract_text(self, img: Image.Image) -> str:
        gray = ImageOps.grayscale(img)
        binary = gray.point(lambda p: 255 if p > 200 else 0)
        results = self.reader.readtext(np.array(binary), detail=0)
        return " ".join(results).strip()

    def translate(self, text: str) -> str:
        prompt = self.cfg.llm_prompt_template.format(text=text)
        result = self.llm(prompt, stop=["Translation:"], max_tokens=128)
        return result["choices"][0]["text"].strip()

    def run(self):
        while True:
            if self.enabled and self.ocr_region and self.overlay:
                img = ImageGrab.grab(bbox=self.ocr_region)
                text = self.extract_text(img)
                if text:
                    translation = self.translate(text)
                    self.overlay.set_text(translation)
            time.sleep(self.cfg.ocr_interval)


if __name__ == "__main__":
    config = Config()
    app = ScreenTranslator(config)
    print("Screen translator running. Use hotkeys to control.")
    app.run()

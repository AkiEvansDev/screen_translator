import os
import re
import threading
import time
import sys
from ctypes import windll
from typing import Optional, Tuple

from PIL import ImageGrab, ImageOps, Image
import cv2
import numpy as np

import keyboard
from PyQt5 import QtWidgets, QtCore, QtGui
from concurrent.futures import ThreadPoolExecutor

import easyocr
from llama_cpp import Llama

from config import Config

os.environ["CUDA_VISIBLE_DEVICES"] = "1"

GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x80000
WS_EX_TRANSPARENT = 0x20

user32 = windll.user32

def make_window_transparent(hwnd):
    """Make a window transparent for mouse/keyboard events (Windows only)."""
    if sys.platform != "win32":
        return

    ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style | WS_EX_LAYERED | WS_EX_TRANSPARENT)


def compute_translation_region(ocr_region: tuple, margin: int = 10) -> tuple:
    x1, y1, x2, y2 = ocr_region
    height = y2 - y1

    if y1 - height - margin > 0:
        return (x1, y1 - height - margin, x2, y1 - margin)
    else:
        return (x1, y2 + margin, x2, y2 + height + margin)


class RegionSelector:
    def select(self) -> Optional[Tuple[int, int, int, int]]:
        import tkinter as tk
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


class OverlayManager(QtCore.QObject):
    update_overlay_signal = QtCore.pyqtSignal(tuple, str)

    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self.overlays = {}
        self.update_overlay_signal.connect(self._update_region_gui)

    def update_region(self, region: tuple, text: str):
        self.update_overlay_signal.emit(region, text)

    def _update_region_gui(self, region: tuple, text: str):
        if not text.strip():
            if region in self.overlays:
                self.overlays[region][0].close()
                del self.overlays[region]
            return

        if region in self.overlays:
            _, label = self.overlays[region]
            label.setText(text)
        else:
            window, label = self._create_window(region, text)
            self.overlays[region] = (window, label)

    def _create_window(self, region: tuple, text: str):
        x1, y1, x2, y2 = region
        width, height = x2 - x1, y2 - y1

        window = QtWidgets.QWidget()
        window.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.Tool)
        window.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        window.setGeometry(x1, y1, width, height)

        layout = QtWidgets.QVBoxLayout(window)
        layout.setContentsMargins(10, 10, 10, 10)

        label = QtWidgets.QLabel(text)
        label.setStyleSheet("color: white; background-color: rgba(0, 0, 0, 180); padding: 10px;")
        label.setFont(QtGui.QFont(self.cfg.default_overlay_font, self.cfg.default_overlay_font_size))
        label.setAlignment(QtCore.Qt.AlignCenter)
        label.setWordWrap(True)
        layout.addWidget(label)

        hwnd = int(window.winId())
        make_window_transparent(hwnd)

        window.show()
        return window, label


class ScreenTranslator(QtCore.QObject):
    def __init__(self, cfg: Config):
        super().__init__()
        self.cfg = cfg
        self.overlay = OverlayManager(cfg)
        self.executor = ThreadPoolExecutor(max_workers=2)

        self.ocr_region = None
        self.translate_region = None

        self.auto_timer = QtCore.QTimer()
        self.auto_timer.timeout.connect(self._run_auto_translation)
        self.auto_translation_active = False

        self.single_ocr_region = None
        self.single_translate_region = None

        self.llm = Llama(
            model_path=cfg.llm_model_path,
            n_gpu_layers=cfg.llm_gpu_layers,
            main_gpu=cfg.llm_gpu_index,
            n_ctx=2048,
            n_batch=64,
            embedding=False,
            logits_all=False,
            verbose=True,
            chat_format="chatml"
        )

        self.reader = easyocr.Reader(["en"], gpu=True)

        keyboard.add_hotkey(cfg.hotkey_set_region, self.set_region)
        keyboard.add_hotkey(cfg.hotkey_auto_translation, self.auto_translation)
        keyboard.add_hotkey(cfg.hotkey_ocr, self.ocr)
        keyboard.add_hotkey(cfg.hotkey_translate, self.translate)

    def set_region(self):
        region = RegionSelector().select()
        if region:
            if self.translate_region:
                self.overlay.update_region(self.translate_region, "")
            self.ocr_region = region
            self.translate_region = compute_translation_region(region)

    def auto_translation(self):
        if not (self.ocr_region and self.translate_region):
            return

        if self.auto_translation_active:
            self.auto_timer.stop()
            self.overlay.update_region(self.translate_region, "")
            self.auto_translation_active = False
            return

        self.auto_translation_active = True
        interval_ms = int(self.cfg.ocr_interval * 1000)
        self.auto_timer.start(interval_ms)

    def _run_auto_translation(self):
        if self.ocr_region and self.translate_region:
            self.executor.submit(self._run_auto_ocr_and_translate)

    def _run_auto_ocr_and_translate(self):
        img = ImageGrab.grab(bbox=self.ocr_region)
        text = self._extract_text(img)
        if text:
            translated = self._translate(text)
            if translated:
                self.overlay.update_region(self.translate_region, translated)

    def ocr(self):
        if self.single_ocr_region:
            self.overlay.update_region(self.single_ocr_region, "")
            self.single_ocr_region = None
            return

        region = RegionSelector().select()
        if region:
            self.executor.submit(self._run_ocr_and_show, region)

    def _run_ocr_and_show(self, region):
        img = ImageGrab.grab(bbox=region)
        text = self._extract_text(img)
        if text:
            self.single_ocr_region = region
            self.overlay.update_region(region, text)

    def translate(self):
        if self.single_translate_region:
            self.overlay.update_region(self.single_translate_region, "")
            self.single_translate_region = None
            return

        region = RegionSelector().select()
        if region:
            self.executor.submit(self._run_translate_and_show, region)

    def _run_translate_and_show(self, region):
        img = ImageGrab.grab(bbox=region)
        text = self._extract_text(img)
        if text:
            translate = self._translate(text)
            if translate:
                self.single_translate_region = region
                self.overlay.update_region(region, translate)

    def _extract_text(self, img: Image.Image) -> str:
        img_np = np.array(img)
        gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        blur = cv2.GaussianBlur(gray, (3, 3), 0)
        _, binary = cv2.threshold(blur, 180, 255, cv2.THRESH_BINARY)

        results = self.reader.readtext(binary, detail=0)
        return " ".join(results).strip()
        # gray = ImageOps.grayscale(img)
        # binary = gray.point(lambda p: 255 if p > 200 else 0)
        # results = self.reader.readtext(np.array(binary), detail=0)
        # return " ".join(results).strip()

    def _translate(self, text: str) -> str:
        if not text.strip():
            return ""

        prompt = self.cfg.llm_prompt_template.format(text=text)
        result = self.llm(
            prompt,
            max_tokens=512,
            stop=["</s>", "[INST]", "[/INST]", "<|im_start|>", "<|im_end|>"],
            temperature=0.5,
            top_p=0.95,
        )

        return self._clean_translation(result["choices"][0]["text"])
    
    def _clean_translation(self, output: str) -> str:
        text = re.sub(r'<\|?im_start\|?>', '', output)
        text = re.sub(r'<\|?im_end\|?>', '', text)
        return text.strip()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    cfg = Config()
    translator = ScreenTranslator(cfg)
    sys.exit(app.exec_())

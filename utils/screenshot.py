"""
Provides interactive screen region selection using Tkinter.
Returns a rectangle in (left, top, width, height) format.
"""

import tkinter as tk
from typing import Optional, Tuple

Region = Tuple[int, int, int, int]

def select_screen_region() -> Optional[Region]:
    """Launch a transparent selection tool and return selected region."""
    region: Optional[Region] = None

    root = tk.Tk()
    root.attributes("-fullscreen", True)
    root.attributes("-alpha", 0.3)
    root.attributes("-topmost", True)
    root.config(cursor="cross")
    root.configure(background="black")

    start_x = start_y = end_x = end_y = 0
    canvas = tk.Canvas(root, bg="black", highlightthickness=0)
    canvas.pack(fill=tk.BOTH, expand=True)

    rect_id = None

    def on_mouse_down(event):
        nonlocal start_x, start_y, rect_id
        start_x, start_y = event.x, event.y
        rect_id = canvas.create_rectangle(start_x, start_y, start_x, start_y, outline="red", width=2)

    def on_mouse_drag(event):
        nonlocal rect_id
        if rect_id:
            canvas.coords(rect_id, start_x, start_y, event.x, event.y)

    def on_mouse_up(event):
        nonlocal region
        end_x, end_y = event.x, event.y
        left = min(start_x, end_x)
        top = min(start_y, end_y)
        width = abs(end_x - start_x)
        height = abs(end_y - start_y)
        region = (left, top, width, height)
        root.destroy()

    canvas.bind("<Button-1>", on_mouse_down)
    canvas.bind("<B1-Motion>", on_mouse_drag)
    canvas.bind("<ButtonRelease-1>", on_mouse_up)

    root.mainloop()
    return region

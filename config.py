"""
Application configuration for paths, hotkeys, and runtime parameters.
"""

from dataclasses import dataclass

@dataclass
class Config:
    # === OCR Settings ===
    ocr_interval: float = 1.5  # Seconds between OCR scans

    # === Hotkey Bindings ===
    hotkey_select_region: str = "ctrl+alt+1"
    hotkey_set_output_region: str = "ctrl+alt+2"
    hotkey_toggle_translation: str = "ctrl+alt+3"

    # === LLM Settings ===
    llm_model_path: str = "./models/mistral-7b-instruct-v0.2.Q6_K.gguf"
    llm_gpu_layers: int = 35
    llm_gpu_index: int = 1  # Targeting second GPU (GPU:1)
    llm_prompt_template: str = "Translate the following text to Russian:\n\n{text}\n\nTranslation:"

    # === UI Settings ===
    default_overlay_font: str = "Arial"
    default_overlay_font_size: int = 18
    overlay_wrap_length: int = 800

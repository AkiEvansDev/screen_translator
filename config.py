"""
Application configuration for paths, hotkeys, and runtime parameters.
"""

from dataclasses import dataclass

@dataclass
class Config:
    # === OCR Settings ===
    ocr_interval: float = 4  # Seconds between OCR scans

    # === Hotkey Bindings ===
    hotkey_set_region: str = "alt+1"
    hotkey_auto_translation: str = "alt+2"
    hotkey_translate: str = "alt+3"
    hotkey_ocr: str = "alt+4"

    # === LLM Settings ===
    llm_model_path: str = "./models/Nous-Hermes-2-Mistral-7B-DPO.Q6_K.gguf"
    llm_gpu_layers: int = 35
    llm_gpu_index: int = 1  # Targeting second GPU (GPU:1)
    llm_prompt_template: str = (
        "<|im_start|>system\n"
        "You are a professional machine translation engine. "
        "Your task is to translate imperfect English OCR text into fluent Russian. "
        "The input may contain incomplete sentences, broken words, typos, or layout artifacts. "
        "Translate as faithfully and fluently as possible. "
        "Do not include the original text. Do not explain anything. "
        "Output only the translation in Russian. Avoid placeholders or comments like [unreadable]."
        "<|im_end|>\n"
        "<|im_start|>user\n"
        "{text}"
        "<|im_end|>\n"
        "<|im_start|>assistant\n"
    )

    # === UI Settings ===
    default_overlay_font: str = "Arial"
    default_overlay_font_size: int = 14

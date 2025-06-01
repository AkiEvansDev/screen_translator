# Screen Translator

A basic screen translation tool for Windows using local LLM models. Hotkeys allow
selection of the OCR region, the output overlay, and toggling translation.

## Features

- Hotkeys (configurable in `config.py`)
  - **Ctrl+Alt+1** – select region to perform OCR
  - **Ctrl+Alt+2** – select region for translation overlay
  - **Ctrl+Alt+3** – toggle translation on or off
- OCR performed with **EasyOCR** for white text on complex backgrounds
- Translation performed locally with `llama-cpp-python` on GPU index 1
- Overlay window is semi-transparent and click-through

## Usage

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Place the GGUF model file in the `models` folder (see `config.py` for name).
3. Run the application:
   ```bash
   python main.py
   ```
4. Use the hotkeys to select the OCR and output regions and to enable
   translation.

## Notes

This project is a lightweight example and may need additional tuning on Windows
(e.g. installing dependencies for **EasyOCR** and ensuring GPU drivers support
`llama-cpp-python`).

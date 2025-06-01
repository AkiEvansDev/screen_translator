"""
LLMTranslator performs local translation using a llama-cpp model in GGUF format.
"""

import logging
import threading
import time
from typing import Optional
from queue import Queue, Empty
from llama_cpp import Llama
from config import Config

class LLMTranslator:
    """Handles translation of OCR-extracted text using a local LLM."""

    def __init__(self, config: Config, input_queue: Queue, output_queue: Queue):
        """
        Args:
            config (Config): App configuration.
            input_queue (Queue): OCR output queue.
            output_queue (Queue): Queue for sending translated text.
        """
        self.config = config
        self.input_queue = input_queue
        self.output_queue = output_queue

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self.llm = self._load_model()

    def _load_model(self) -> Llama:
        """Load LLM model with GPU configuration."""
        logging.info("Loading LLM model from disk...")
        return Llama(
            model_path=self.config.llm_model_path,
            n_gpu_layers=self.config.llm_gpu_layers,
            main_gpu=self.config.llm_gpu_index,
            n_ctx=2048,
            use_mlock=True,
            verbose=False,
        )

    def start(self) -> None:
        """Start the translation thread."""
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
            logging.info("LLM translation started.")

    def stop(self) -> None:
        """Stop the translation thread."""
        self._running = False
        if self._thread:
            self._thread.join()
            logging.info("LLM translation stopped.")

    def _run(self) -> None:
        """Consume OCR text and produce translated text."""
        while self._running:
            try:
                text = self.input_queue.get(timeout=1)
                prompt = self.config.llm_prompt_template.format(text=text.strip())
                logging.debug(f"LLM prompt: {prompt}")

                response = self.llm(prompt, max_tokens=256, stop=["\n"])
                translated = response["choices"][0]["text"].strip()

                if translated:
                    self.output_queue.put(translated)
                    logging.info(f"Translated: {translated}")

            except Empty:
                continue
            except Exception as e:
                logging.exception(f"Translation error: {e}")
                time.sleep(2)

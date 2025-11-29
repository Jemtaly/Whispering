#!/usr/bin/env python3

"""
TTS Provider module for ResembleAI ChatterboxTTS integration.
Handles text-to-speech synthesis with voice cloning support.
"""

import io
import os
import warnings
from typing import Optional, Literal

import numpy as np
import torch

# Suppress warnings during model loading
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=UserWarning)


class TTSProvider:
    """
    Wrapper for ChatterboxTTS with support for voice cloning and audio generation.

    Handles model initialization, voice reference management, and speech synthesis
    with configurable parameters.
    """

    def __init__(
        self,
        device: Literal["cpu", "cuda", "auto"] = "auto",
        model_type: Literal["standard", "multilingual"] = "standard"
    ):
        """
        Initialize TTS provider.

        Args:
            device: Compute device (cpu/cuda/auto)
            model_type: Model variant (standard or multilingual)
        """
        self.device = self._resolve_device(device)
        self.model_type = model_type
        self.model = None
        self.sample_rate = 24000  # ChatterboxTTS default sample rate

        # Model will be loaded lazily on first synthesis
        self._initialized = False

    def _resolve_device(self, device: str) -> str:
        """Resolve device string to actual device."""
        if device == "auto":
            return "cuda" if torch.cuda.is_available() else "cpu"
        return device

    def _ensure_initialized(self):
        """Lazy load the TTS model on first use."""
        if self._initialized:
            return

        try:
            if self.model_type == "multilingual":
                from chatterbox.mtl_tts import ChatterboxMultilingualTTS
                print(f"Loading multilingual TTS model on {self.device}...")
                self.model = ChatterboxMultilingualTTS.from_pretrained(device=self.device)
            else:
                from chatterbox.tts import ChatterboxTTS
                print(f"Loading TTS model on {self.device}...")
                self.model = ChatterboxTTS.from_pretrained(device=self.device)

            self._initialized = True
            print(f"✓ TTS model loaded successfully on {self.device}")

        except ImportError as e:
            error_msg = (
                "ChatterboxTTS not installed.\n"
                "Install with: pip install chatterbox-tts --no-deps\n"
                "See INSTALL_TTS.md for details."
            )
            raise ImportError(error_msg) from e
        except RuntimeError as e:
            # Check for common CUDA/cuDNN errors
            error_str = str(e)
            if "cuDNN" in error_str or "CUDA" in error_str:
                error_msg = (
                    f"Failed to initialize TTS model - CUDA/cuDNN error:\n{e}\n\n"
                    "This is likely a cuDNN version mismatch.\n"
                    "PyTorch comes with its own cuDNN - don't install nvidia-cudnn separately.\n"
                    "Check run.sh doesn't add conflicting cuDNN to LD_LIBRARY_PATH.\n"
                    "Run: python debug_cuda.py for detailed diagnostics."
                )
                raise RuntimeError(error_msg) from e
            else:
                raise RuntimeError(f"Failed to initialize TTS model: {e}") from e
        except Exception as e:
            raise RuntimeError(f"Unexpected error initializing TTS: {e}") from e

    def synthesize(
        self,
        text: str,
        reference_audio_path: Optional[str] = None,
        language: str = "en",
        exaggeration: float = 0.5,
        cfg: float = 0.5
    ) -> tuple[np.ndarray, int]:
        """
        Synthesize speech from text.

        Args:
            text: Text to synthesize (max 300 characters recommended)
            reference_audio_path: Path to reference voice audio file (optional)
            language: Language code (for multilingual model)
            exaggeration: Expressiveness control (0.0-1.0, default 0.5)
            cfg: Classifier-free guidance scale (0.0-1.0, default 0.5)

        Returns:
            Tuple of (audio_array, sample_rate)
            audio_array: numpy array of audio samples
            sample_rate: sample rate in Hz

        Raises:
            ValueError: If text exceeds safe length
        """
        # Ensure model is loaded
        self._ensure_initialized()

        # Validate text length (300 char limit)
        if len(text) > 300:
            raise ValueError(
                f"Text too long ({len(text)} chars). Maximum 300 characters per call. "
                "Use TTSController for automatic chunking."
            )

        if not text.strip():
            raise ValueError("Cannot synthesize empty text")

        try:
            # Generate audio using ChatterboxTTS API
            # API: generate(text, repetition_penalty, min_p, top_p, audio_prompt_path, exaggeration, cfg_weight, temperature)
            audio = self.model.generate(
                text=text,
                audio_prompt_path=reference_audio_path,
                exaggeration=exaggeration,
                cfg_weight=cfg,
                temperature=0.8,  # Default from API
            )

            # Convert to numpy array if needed
            if isinstance(audio, torch.Tensor):
                audio = audio.cpu().numpy()

            # Ensure correct shape (flatten if needed)
            if len(audio.shape) > 1:
                audio = audio.flatten()

            return audio, self.sample_rate

        except Exception as e:
            raise RuntimeError(f"TTS synthesis failed: {e}") from e

    def get_device(self) -> str:
        """Get current compute device."""
        return self.device

    def is_initialized(self) -> bool:
        """Check if model is loaded."""
        return self._initialized

    def unload(self):
        """Unload model to free memory."""
        if self.model is not None:
            del self.model
            self.model = None
            self._initialized = False

            # Clear CUDA cache if applicable
            if self.device == "cuda" and torch.cuda.is_available():
                torch.cuda.empty_cache()


if __name__ == "__main__":
    # Simple test
    print("Testing TTSProvider...")

    provider = TTSProvider(device="auto")
    print(f"Device: {provider.get_device()}")

    test_text = "Hello! This is a test of the text to speech system."
    print(f"Synthesizing: {test_text}")

    try:
        audio, sr = provider.synthesize(test_text)
        print(f"Success! Generated {len(audio)} samples at {sr}Hz")
        print(f"Duration: {len(audio)/sr:.2f} seconds")
    except Exception as e:
        print(f"Error: {e}")

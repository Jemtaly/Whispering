#!/usr/bin/env python3

"""
TTS Controller module for orchestrating text-to-speech operations.
Handles text chunking, audio file generation, and voice management.
"""

import os
import re
import threading
from pathlib import Path
from typing import Optional, Callable, Literal

import numpy as np
import soundfile as sf

from tts_provider import TTSProvider


class TTSController:
    """
    High-level controller for TTS operations.

    Handles:
    - Intelligent text chunking (max 300 chars per synthesis)
    - Audio file generation (WAV/OGG)
    - Voice reference management
    - Async synthesis with callbacks
    """

    MAX_CHUNK_SIZE = 300  # Character limit per synthesis call

    def __init__(
        self,
        device: Literal["cpu", "cuda", "auto"] = "auto",
        output_dir: str = "tts_output",
        model_type: Literal["standard", "multilingual"] = "standard"
    ):
        """
        Initialize TTS controller.

        Args:
            device: Compute device for TTS model
            output_dir: Directory for saving audio files
            model_type: TTS model variant
        """
        self.provider = TTSProvider(device=device, model_type=model_type)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        self.reference_voice_path: Optional[str] = None
        self.language = "en"
        self.exaggeration = 0.5
        self.cfg = 0.5

        # Callbacks
        self.on_progress: Optional[Callable[[str], None]] = None
        self.on_complete: Optional[Callable[[str], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None

    def set_reference_voice(self, audio_path: Optional[str]):
        """Set reference voice for voice cloning."""
        if audio_path and not os.path.exists(audio_path):
            raise FileNotFoundError(f"Reference voice file not found: {audio_path}")
        self.reference_voice_path = audio_path

    def set_parameters(
        self,
        language: str = "en",
        exaggeration: float = 0.5,
        cfg: float = 0.5
    ):
        """Configure synthesis parameters."""
        self.language = language
        self.exaggeration = exaggeration
        self.cfg = cfg

    def chunk_text(self, text: str) -> list[str]:
        """
        Intelligently chunk text into segments ≤ 300 characters.

        Splits at sentence boundaries when possible, otherwise at word boundaries.

        Args:
            text: Input text to chunk

        Returns:
            List of text chunks, each ≤ 300 characters
        """
        if len(text) <= self.MAX_CHUNK_SIZE:
            return [text]

        chunks = []

        # Split into sentences first
        # Matches . ! ? followed by space or end of string
        sentence_pattern = r'([.!?]+[\s]+|[.!?]+$)'
        sentences = re.split(sentence_pattern, text)

        # Recombine sentence text with punctuation
        cleaned_sentences = []
        i = 0
        while i < len(sentences):
            if i + 1 < len(sentences) and re.match(sentence_pattern, sentences[i + 1]):
                # Combine sentence with its punctuation
                cleaned_sentences.append(sentences[i] + sentences[i + 1])
                i += 2
            elif sentences[i].strip():
                cleaned_sentences.append(sentences[i])
                i += 1
            else:
                i += 1

        # Now group sentences into chunks
        current_chunk = ""

        for sentence in cleaned_sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # If single sentence exceeds limit, split at word boundaries
            if len(sentence) > self.MAX_CHUNK_SIZE:
                # Save current chunk if any
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""

                # Split long sentence into words
                words = sentence.split()
                word_chunk = ""

                for word in words:
                    if len(word_chunk) + len(word) + 1 <= self.MAX_CHUNK_SIZE:
                        word_chunk += (" " if word_chunk else "") + word
                    else:
                        if word_chunk:
                            chunks.append(word_chunk.strip())
                        word_chunk = word

                if word_chunk:
                    chunks.append(word_chunk.strip())

            # If adding sentence doesn't exceed limit, add to current chunk
            elif len(current_chunk) + len(sentence) + 1 <= self.MAX_CHUNK_SIZE:
                current_chunk += (" " if current_chunk else "") + sentence

            # Otherwise, save current chunk and start new one
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence

        # Don't forget last chunk
        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def synthesize_to_file(
        self,
        text: str,
        output_filename: str,
        file_format: Literal["wav", "ogg"] = "wav",
        async_mode: bool = False
    ) -> Optional[str]:
        """
        Synthesize text to audio file.

        Automatically chunks text if needed and concatenates audio.

        Args:
            text: Text to synthesize
            output_filename: Output filename (without extension)
            file_format: Output format (wav or ogg)
            async_mode: Run in background thread

        Returns:
            Path to generated file (None if async)
        """
        if async_mode:
            thread = threading.Thread(
                target=self._synthesize_worker,
                args=(text, output_filename, file_format)
            )
            thread.daemon = True
            thread.start()
            return None
        else:
            return self._synthesize_worker(text, output_filename, file_format)

    def _synthesize_worker(
        self,
        text: str,
        output_filename: str,
        file_format: str
    ) -> Optional[str]:
        """Worker function for synthesis (can run async)."""
        try:
            # Progress callback
            if self.on_progress:
                self.on_progress("Chunking text...")

            chunks = self.chunk_text(text)

            if self.on_progress:
                self.on_progress(f"Synthesizing {len(chunks)} chunk(s)...")

            # Synthesize each chunk
            audio_segments = []

            for i, chunk in enumerate(chunks):
                if self.on_progress:
                    self.on_progress(f"Chunk {i+1}/{len(chunks)}: {chunk[:50]}...")

                audio, sr = self.provider.synthesize(
                    text=chunk,
                    reference_audio_path=self.reference_voice_path,
                    language=self.language,
                    exaggeration=self.exaggeration,
                    cfg=self.cfg
                )
                audio_segments.append(audio)

            # Concatenate audio segments
            if len(audio_segments) > 1:
                full_audio = np.concatenate(audio_segments)
            else:
                full_audio = audio_segments[0]

            # Save to file
            output_path = self.output_dir / f"{output_filename}.{file_format}"

            if self.on_progress:
                self.on_progress(f"Saving to {output_path}...")

            # soundfile handles both WAV and OGG
            sf.write(
                str(output_path),
                full_audio,
                self.provider.sample_rate,
                format=file_format.upper()
            )

            if self.on_complete:
                self.on_complete(str(output_path))

            return str(output_path)

        except Exception as e:
            error_msg = f"TTS synthesis failed: {e}"
            if self.on_error:
                self.on_error(error_msg)
            else:
                print(error_msg)
            return None

    def synthesize_to_array(self, text: str) -> Optional[tuple[np.ndarray, int]]:
        """
        Synthesize text to numpy array (for playback without saving).

        Args:
            text: Text to synthesize

        Returns:
            Tuple of (audio_array, sample_rate) or None on error
        """
        try:
            chunks = self.chunk_text(text)
            audio_segments = []

            for chunk in chunks:
                audio, sr = self.provider.synthesize(
                    text=chunk,
                    reference_audio_path=self.reference_voice_path,
                    language=self.language,
                    exaggeration=self.exaggeration,
                    cfg=self.cfg
                )
                audio_segments.append(audio)

            # Concatenate
            if len(audio_segments) > 1:
                full_audio = np.concatenate(audio_segments)
            else:
                full_audio = audio_segments[0]

            return full_audio, self.provider.sample_rate

        except Exception as e:
            if self.on_error:
                self.on_error(f"TTS synthesis failed: {e}")
            return None


if __name__ == "__main__":
    # Test chunking
    controller = TTSController()

    test_text = "This is a test. " * 50  # Long text
    print(f"Original text length: {len(test_text)}")

    chunks = controller.chunk_text(test_text)
    print(f"\nChunked into {len(chunks)} segments:")
    for i, chunk in enumerate(chunks):
        print(f"  {i+1}. [{len(chunk)} chars] {chunk[:60]}...")

    # Test synthesis
    short_text = "Hello world! This is a test of the text to speech system."
    print(f"\n\nSynthesizing: {short_text}")

    try:
        result = controller.synthesize_to_file(
            short_text,
            "test_output",
            file_format="wav"
        )
        if result:
            print(f"Success! Saved to: {result}")
    except Exception as e:
        print(f"Error: {e}")

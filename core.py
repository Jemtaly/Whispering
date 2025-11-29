#!/usr/bin/env python3

import collections
import io
import math
import threading
import wave
from urllib.parse import quote

import numpy as np
import requests
import sounddevice as sd
from cmque import DataDeque, PairDeque, Queue
from faster_whisper import WhisperModel


models = ["tiny", "base", "small", "medium", "large-v1", "large-v2", "large-v3", "large"]
devices = ["cpu", "cuda", "auto"]
sources = ["af", "am", "ar", "as", "az", "ba", "be", "bg", "bn", "bo", "br", "bs", "ca", "cs", "cy", "da", "de", "el", "en", "es", "et", "eu", "fa", "fi", "fo", "fr", "gl", "gu", "ha", "haw", "he", "hi", "hr", "ht", "hu", "hy", "id", "is", "it", "ja", "jw", "ka", "kk", "km", "kn", "ko", "la", "lb", "ln", "lo", "lt", "lv", "mg", "mi", "mk", "ml", "mn", "mr", "ms", "mt", "my", "ne", "nl", "nn", "no", "oc", "pa", "pl", "ps", "pt", "ro", "ru", "sa", "sd", "si", "sk", "sl", "sn", "so", "sq", "sr", "su", "sv", "sw", "ta", "te", "tg", "th", "tk", "tl", "tr", "tt", "uk", "ur", "uz", "vi", "yi", "yo", "yue", "zh"]
targets = ["af", "ak", "am", "ar", "as", "ay", "az", "be", "bg", "bho", "bm", "bn", "bs", "ca", "ceb", "ckb", "co", "cs", "cy", "da", "de", "doi", "dv", "ee", "el", "en", "eo", "es", "et", "eu", "fa", "fi", "fil", "fr", "fy", "ga", "gd", "gl", "gn", "gom", "gu", "ha", "haw", "he", "hi", "hmn", "hr", "ht", "hu", "hy", "id", "ig", "ilo", "is", "it", "ja", "jw", "ka", "kk", "km", "kn", "ko", "kri", "ku", "ky", "la", "lb", "lg", "ln", "lo", "lt", "lus", "lv", "mai", "mg", "mi", "mk", "ml", "mn", "mni-Mtei", "mr", "ms", "mt", "my", "ne", "nl", "no", "nso", "ny", "om", "or", "pa", "pl", "ps", "pt", "qu", "ro", "ru", "rw", "sa", "sd", "si", "sk", "sl", "sm", "sn", "so", "sq", "sr", "st", "su", "sv", "sw", "ta", "te", "tg", "th", "ti", "tk", "tl", "tr", "ts", "tt", "ug", "uk", "ur", "uz", "vi", "xh", "yi", "yo", "zh-CN", "zh-TW", "zu"]


class ParagraphDetector:
    """
    Adaptive paragraph detection based on speech pause patterns.
    
    Uses statistical analysis of pause durations to detect "significant" pauses
    that likely indicate paragraph breaks, while also enforcing hard limits
    on paragraph length.
    
    Parameters:
        threshold_std: Number of standard deviations above mean for a "significant" pause (default: 1.5)
        min_pause: Minimum pause duration to consider as potential break (default: 0.8s)
        max_chars: Maximum characters per paragraph before forced break (default: 500)
        max_words: Maximum words per paragraph before forced break (default: 100)
        window_size: Number of recent pauses to use for statistics (default: 30)
        warmup_count: Minimum pauses needed before adaptive mode (default: 5)
        warmup_threshold: Fixed threshold during warmup period (default: 2.0s)
    """
    
    def __init__(
        self,
        threshold_std=1.5,
        min_pause=0.8,
        max_chars=500,
        max_words=100,
        window_size=30,
        warmup_count=5,
        warmup_threshold=2.0
    ):
        self.threshold_std = threshold_std
        self.min_pause = min_pause
        self.max_chars = max_chars
        self.max_words = max_words
        self.window_size = window_size
        self.warmup_count = warmup_count
        self.warmup_threshold = warmup_threshold
        
        # State
        self.pause_history = []
        self.current_para_chars = 0
        self.current_para_words = 0
        self.last_absolute_end = None  # Track absolute end time across batches
    
    def _add_pause(self, duration):
        """Record a pause duration for statistics."""
        if duration > 0:  # Only track actual pauses
            self.pause_history.append(duration)
            if len(self.pause_history) > self.window_size:
                self.pause_history.pop(0)
    
    def _get_adaptive_threshold(self):
        """Calculate the current adaptive threshold based on pause history."""
        if len(self.pause_history) < self.warmup_count:
            return self.warmup_threshold
        
        n = len(self.pause_history)
        mean = sum(self.pause_history) / n
        variance = sum((p - mean) ** 2 for p in self.pause_history) / n
        std = math.sqrt(variance) if variance > 0 else 0
        
        # Threshold is mean + (threshold_std * std), but at least min_pause
        threshold = mean + (self.threshold_std * std)
        return max(threshold, self.min_pause)
    
    def _reset_paragraph(self):
        """Reset paragraph counters."""
        self.current_para_chars = 0
        self.current_para_words = 0
    
    def process_segments(self, segments, time_offset=0.0):
        """
        Process a list of Whisper segments and return text with paragraph breaks.
        
        Args:
            segments: List of Whisper segment objects with .text, .start, .end
            time_offset: Cumulative audio offset to convert relative to absolute timestamps
            
        Returns:
            String with paragraph breaks (\n\n) inserted where appropriate
        """
        if not segments:
            return ""
        
        result_parts = []
        
        for segment in segments:
            text = segment.text
            should_break = False
            
            # Convert to absolute timestamps
            absolute_start = segment.start + time_offset
            absolute_end = segment.end + time_offset
            
            # Check hard limits first
            new_chars = self.current_para_chars + len(text)
            new_words = self.current_para_words + len(text.split())
            if self.current_para_chars > 0:
                if new_chars > self.max_chars or new_words > self.max_words:
                    should_break = True
            
            # Check pause using absolute timestamps (works across batches!)
            if not should_break and self.last_absolute_end is not None:
                pause_duration = absolute_start - self.last_absolute_end
                if pause_duration > 0:
                    self._add_pause(pause_duration)
                    if pause_duration >= self.min_pause:
                        threshold = self._get_adaptive_threshold()
                        if pause_duration > threshold:
                            should_break = True
            
            # Apply break
            if should_break:
                result_parts.append("\n\n")
                self._reset_paragraph()
            
            # Add text and update counters
            result_parts.append(text)
            self.current_para_chars += len(text)
            self.current_para_words += len(text.split())
            
            # Track absolute end time for next comparison
            self.last_absolute_end = absolute_end
        
        return "".join(result_parts)
    
    def get_stats(self):
        """Return current statistics for debugging/display."""
        if len(self.pause_history) < 2:
            return {
                "pause_count": len(self.pause_history),
                "mean": None,
                "std": None,
                "threshold": self.warmup_threshold,
                "mode": "warmup"
            }
        
        n = len(self.pause_history)
        mean = sum(self.pause_history) / n
        variance = sum((p - mean) ** 2 for p in self.pause_history) / n
        std = math.sqrt(variance) if variance > 0 else 0
        
        return {
            "pause_count": n,
            "mean": round(mean, 3),
            "std": round(std, 3),
            "threshold": round(self._get_adaptive_threshold(), 3),
            "mode": "adaptive" if n >= self.warmup_count else "warmup"
        }
sources = ["af", "am", "ar", "as", "az", "ba", "be", "bg", "bn", "bo", "br", "bs", "ca", "cs", "cy", "da", "de", "el", "en", "es", "et", "eu", "fa", "fi", "fo", "fr", "gl", "gu", "ha", "haw", "he", "hi", "hr", "ht", "hu", "hy", "id", "is", "it", "ja", "jw", "ka", "kk", "km", "kn", "ko", "la", "lb", "ln", "lo", "lt", "lv", "mg", "mi", "mk", "ml", "mn", "mr", "ms", "mt", "my", "ne", "nl", "nn", "no", "oc", "pa", "pl", "ps", "pt", "ro", "ru", "sa", "sd", "si", "sk", "sl", "sn", "so", "sq", "sr", "su", "sv", "sw", "ta", "te", "tg", "th", "tk", "tl", "tr", "tt", "uk", "ur", "uz", "vi", "yi", "yo", "yue", "zh"]
targets = ["af", "ak", "am", "ar", "as", "ay", "az", "be", "bg", "bho", "bm", "bn", "bs", "ca", "ceb", "ckb", "co", "cs", "cy", "da", "de", "doi", "dv", "ee", "el", "en", "eo", "es", "et", "eu", "fa", "fi", "fil", "fr", "fy", "ga", "gd", "gl", "gn", "gom", "gu", "ha", "haw", "he", "hi", "hmn", "hr", "ht", "hu", "hy", "id", "ig", "ilo", "is", "it", "ja", "jw", "ka", "kk", "km", "kn", "ko", "kri", "ku", "ky", "la", "lb", "lg", "ln", "lo", "lt", "lus", "lv", "mai", "mg", "mi", "mk", "ml", "mn", "mni-Mtei", "mr", "ms", "mt", "my", "ne", "nl", "no", "nso", "ny", "om", "or", "pa", "pl", "ps", "pt", "qu", "ro", "ru", "rw", "sa", "sd", "si", "sk", "sl", "sm", "sn", "so", "sq", "sr", "st", "su", "sv", "sw", "ta", "te", "tg", "th", "ti", "tk", "tl", "tr", "ts", "tt", "ug", "uk", "ur", "uz", "vi", "xh", "yi", "yo", "zh-CN", "zh-TW", "zu"]

# Audio settings - Whisper expects 16kHz mono
TARGET_SAMPLE_RATE = 16000
SAMPLE_WIDTH = 2  # 16-bit audio
CHUNK_DURATION = 0.1  # seconds per chunk


def get_preferred_hostapi_index():
    """Find the best host API: ALSA only (JACK causes crashes)."""
    apis = sd.query_hostapis()
    for i, api in enumerate(apis):
        if 'alsa' in api['name'].lower():
            return i, 'alsa'
    return 0, 'unknown'


def get_mic_names():
    """Get list of input device names, preferring stable devices."""
    devices_list = sd.query_devices()
    
    mics = []
    
    # First priority: ALSA virtual devices named "pipewire" or "pulse" (these route through PipeWire)
    for i, d in enumerate(devices_list):
        if d['max_input_channels'] > 0:
            name_lower = d['name'].lower()
            # Only ALSA devices (JACK crashes)
            api_name = sd.query_hostapis(d['hostapi'])['name'].lower()
            if 'alsa' not in api_name:
                continue
            if 'pipewire' in name_lower or name_lower == 'pulse':
                mics.append((i, d['name']))
    
    # Second priority: Simple ALSA hardware devices (limited channels, not default)
    for i, d in enumerate(devices_list):
        if d['max_input_channels'] > 0 and d['max_input_channels'] <= 8:
            api_name = sd.query_hostapis(d['hostapi'])['name'].lower()
            if 'alsa' not in api_name:
                continue
            name_lower = d['name'].lower()
            # Skip virtual devices we already added, skip default/jack
            if 'pipewire' in name_lower or name_lower == 'pulse':
                continue
            if name_lower in ('default', 'jack'):
                continue
            if 'hw:' in d['name']:  # Real hardware
                if (i, d['name']) not in mics:
                    mics.append((i, d['name']))
    
    return mics


def get_default_device_index():
    """Get the best default device (pipewire or pulse, not the actual 'default')."""
    devices_list = sd.query_devices()
    # Prefer pipewire, then pulse
    for i, d in enumerate(devices_list):
        if d['name'].lower() == 'pipewire' and d['max_input_channels'] > 0:
            return i
    for i, d in enumerate(devices_list):
        if d['name'].lower() == 'pulse' and d['max_input_channels'] > 0:
            return i
    # Fallback: find first device with reasonable channel count
    for i, d in enumerate(devices_list):
        if d['max_input_channels'] > 0 and d['max_input_channels'] <= 4:
            api_name = sd.query_hostapis(d['hostapi'])['name'].lower()
            if 'alsa' in api_name:
                return i
    return None


def get_mic_index(mic_name):
    """Get device index by name."""
    if mic_name is None:
        return None
    mics = get_mic_names()
    # Try exact match first
    for idx, name in mics:
        if name == mic_name:
            return idx
    # Fall back to partial match
    for idx, name in mics:
        if mic_name in name:
            return idx
    raise ValueError(f"Microphone device not found: {mic_name}")


def get_device_info(device_index):
    """Get device sample rate and channels, with fallbacks."""
    if device_index is None:
        # Use smart default (pipewire/pulse)
        device_index = get_default_device_index()
    
    if device_index is None:
        # Ultimate fallback
        return 48000, 1
    
    device_info = sd.query_devices(device_index)
    
    # Get native sample rate (or use default)
    sample_rate = int(device_info.get('default_samplerate', 48000))
    
    # Get channels - limit to 2 to avoid issues with high channel count devices
    max_channels = int(device_info.get('max_input_channels', 1))
    channels = min(2, max(1, max_channels))  # Use 1-2 channels max
    
    return sample_rate, channels


def audio_to_wav_bytes(audio_data, sample_rate, sample_width, channels=1):
    """Convert raw audio bytes to WAV format in memory."""
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_data)
    buffer.seek(0)
    return buffer


def resample_to_mono_16k(data, orig_rate, orig_channels):
    """Convert audio to mono 16kHz for Whisper."""
    # Ensure we have a copy to avoid memory issues
    audio = np.array(data, dtype=np.float32, copy=True) / 32768.0
    
    # Convert to mono if stereo/multi-channel
    if orig_channels > 1 and len(audio.shape) > 1:
        audio = audio.mean(axis=1)
    else:
        audio = audio.flatten()
    
    # Resample if needed
    if orig_rate != TARGET_SAMPLE_RATE:
        # Simple resampling using linear interpolation
        duration = len(audio) / orig_rate
        new_length = int(duration * TARGET_SAMPLE_RATE)
        if new_length > 0:
            indices = np.linspace(0, len(audio) - 1, new_length)
            audio = np.interp(indices, np.arange(len(audio)), audio)
    
    # Convert back to int16
    audio = (audio * 32768.0).clip(-32768, 32767).astype(np.int16)
    return audio.tobytes()


def translate(text, source, target, timeout):
    if target is None:
        return [(text, "Target language is not specified.")]
    try:
        url = "https://translate.googleapis.com/translate_a/single?client=gtx&sl={}&tl={}&dt=t&q={}".format(source or "auto", target, quote(text))
        ans = requests.get(url, timeout=timeout).json()[0] or []
        return [(s, t) for t, s, *infos in ans]
    except:
        return [(text, "Translation service is unavailable.")]


def ai_translate(text, ai_processor):
    """
    Translate/process text using AI provider.

    Args:
        text: Text to process
        ai_processor: AITextProcessor instance

    Returns:
        (processed_text, error_message) tuple
    """
    if not text or not text.strip():
        return ("", None)

    try:
        result, error = ai_processor.process(text)
        return (result, error)
    except Exception as e:
        return (text, f"AI processing error: {str(e)}")


def proc(index, model, vad, memory, patience, timeout, prompt, source, target, tsres_queue, tlres_queue, ready, device="cpu", error=None, level=None, para_detect=True, para_threshold_std=1.5, para_min_pause=0.8, para_max_chars=500, para_max_words=100, ai_processor=None):
    # Create paragraph detector if enabled
    para_detector = ParagraphDetector(
        threshold_std=para_threshold_std,
        min_pause=para_min_pause,
        max_chars=para_max_chars,
        max_words=para_max_words
    ) if para_detect else None
    
    def ts_proc():
        prompts = collections.deque([prompt], memory)
        window = bytearray()
        cumulative_offset = 0.0  # Track total trimmed audio in seconds
        
        while frame := frame_queue.get():
            window.extend(frame)
            audio_file = audio_to_wav_bytes(window, TARGET_SAMPLE_RATE, SAMPLE_WIDTH, channels=1)
            segments, info = whisper_model.transcribe(audio_file, language=source, initial_prompt="".join(prompts), vad_filter=vad)
            segments = [segment for segment in segments]
            start = max(len(window) // SAMPLE_WIDTH / TARGET_SAMPLE_RATE - patience, 0.0)
            i = 0
            for segment in segments:
                if segment.end >= start:
                    if segment.start < start:
                        start = segment.start
                    break
                i += 1
            
            # Process done segments with paragraph detection
            done_segments = segments[:i]
            if para_detector and done_segments:
                # Pass cumulative offset so detector can compute absolute timestamps
                done_src = para_detector.process_segments(done_segments, cumulative_offset)
            else:
                done_src = "".join(segment.text for segment in done_segments)
            
            curr_src = "".join(segment.text for segment in segments[i:])
            prompts.extend(segment.text for segment in done_segments)
            
            # Update cumulative offset BEFORE trimming (start = seconds to trim)
            cumulative_offset += start
            
            del window[: int(start * TARGET_SAMPLE_RATE) * SAMPLE_WIDTH]
            ts2tl_queue.put((done_src, curr_src))
            tsres_queue.put((done_src, curr_src))
        ts2tl_queue.put(None)
        tsres_queue.put(None)

    def tl_proc():
        rsrv_src = ""
        accumulated_done = ""  # Accumulate done text before processing
        MIN_CHARS_TO_PROCESS = 150  # Minimum characters before AI processing

        while ts2tl := ts2tl_queue.get():
            done_src, curr_src = ts2tl

            # Use AI processing if available
            if ai_processor:
                # Accumulate done text
                if done_src:
                    accumulated_done += done_src

                # Only process when we have enough text AND a paragraph break
                # This accumulates more context and reduces API calls
                new_processed = ""
                should_process = (
                    accumulated_done and
                    '\n\n' in accumulated_done and
                    len(accumulated_done) >= MIN_CHARS_TO_PROCESS
                )

                if should_process:
                    # Split on paragraph breaks
                    parts = accumulated_done.split('\n\n')
                    # Keep last part (incomplete paragraph) in accumulated_done
                    to_process = '\n\n'.join(parts[:-1])
                    accumulated_done = parts[-1]

                    if to_process:
                        # Process with AI
                        processed, ai_error = ai_translate(to_process, ai_processor)
                        if ai_error:
                            # Log error to console but continue with result
                            print(f"AI Error: {ai_error}", flush=True)
                        new_processed = processed + '\n\n'  # Add back paragraph break

                # IMPORTANT: Do NOT send provisional text (curr_tgt)
                # Only send finalized chunks to avoid showing partial AI responses
                # Right pane stays empty until chunk is complete and processed
                tlres_queue.put((new_processed, ""))
            else:
                # Use original Google Translate
                if done_src or rsrv_src:
                    done_src = rsrv_src + done_src
                    done_snt = translate(done_src, source, target, timeout)
                    rsrv_src = done_snt.pop()[0]
                    done_tgt = "".join(t for s, t in done_snt)
                else:
                    done_tgt = ""
                curr_src = rsrv_src + curr_src
                curr_snt = translate(curr_src, source, target, timeout)
                curr_tgt = "".join(t for s, t in curr_snt)
                tlres_queue.put((done_tgt, curr_tgt))

        # Process any remaining accumulated text on exit
        if ai_processor and accumulated_done and accumulated_done.strip():
            final_tgt, _ = ai_translate(accumulated_done, ai_processor)
            tlres_queue.put((final_tgt, ""))

        tlres_queue.put(None)

    try:
        # Load model first (before opening audio stream)
        whisper_model = WhisperModel(model, device=device)
        
        # Use smart default if no device specified
        if index is None:
            index = get_default_device_index()
        
        # Query device capabilities
        sample_rate, channels = get_device_info(index)
        chunk_size = int(sample_rate * CHUNK_DURATION)
        
        frame_queue = Queue(DataDeque())
        ts2tl_queue = Queue(PairDeque())
        ts_thread = threading.Thread(target=ts_proc)
        tl_thread = threading.Thread(target=tl_proc)
        
        # Open audio stream with sounddevice
        with sd.InputStream(
            device=index,
            samplerate=sample_rate,
            channels=channels,
            dtype='int16',
            blocksize=chunk_size
        ) as stream:
            ts_thread.start()
            tl_thread.start()
            ready[0] = True
            
            while ready[0]:
                data, overflowed = stream.read(chunk_size)
                # Make a copy immediately to avoid memory issues
                data_copy = np.array(data, copy=True)
                
                # Calculate audio level (RMS) for the level meter
                if level is not None:
                    rms = np.sqrt(np.mean(data_copy.astype(np.float32)**2))
                    # Scale to 0-100 range (32768 is max for int16)
                    level[0] = min(100, int(rms / 328 * 100))
                
                # Convert to mono 16kHz for Whisper
                mono_16k = resample_to_mono_16k(data_copy, sample_rate, channels)
                frame_queue.put(mono_16k)
            
            frame_queue.put(None)
            ts_thread.join()
            tl_thread.join()
            
    except Exception as e:
        if error is not None:
            error[0] = str(e)
    finally:
        ready[0] = None

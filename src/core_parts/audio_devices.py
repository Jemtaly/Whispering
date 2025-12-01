import io
import wave
import numpy as np
import sounddevice as sd

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

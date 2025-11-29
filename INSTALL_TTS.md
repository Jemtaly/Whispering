# TTS Installation Guide

## Option 1: Install chatterbox-tts without deps (Recommended)

```bash
# Install base dependencies first
pip install -r requirements.txt

# Then install chatterbox-tts without its dependencies
pip install chatterbox-tts --no-deps

# Test if it works
python -c "from chatterbox.tts import ChatterboxTTS; print('✓ Success!')"
```

If this works, you're done! The pkuseg dependency might only be needed for features you don't use.

## Option 2: If Option 1 fails - Manual source installation

```bash
# Clone the chatterbox source
git clone https://github.com/resemble-ai/chatterbox /tmp/chatterbox
cd /tmp/chatterbox

# Edit setup.py or pyproject.toml to remove pkuseg from dependencies
# Then install
pip install -e .
```

## Option 3: Copy source directly into project

```bash
# Clone chatterbox repo
git clone https://github.com/resemble-ai/chatterbox /tmp/chatterbox

# Copy just the chatterbox module into your project
cp -r /tmp/chatterbox/chatterbox ./

# Now you can import it directly without pip install
```

## Option 4: Alternative TTS (if chatterbox doesn't work)

If chatterbox proves too difficult, we can switch to **Coqui TTS**:

```bash
pip install TTS
```

Usage:
```python
from TTS.api import TTS
tts = TTS("tts_models/en/ljspeech/tacotron2-DDC")
tts.tts_to_file(text="Hello world", file_path="output.wav")
```

## Testing

After installation, test with:

```bash
python tts_provider.py
```

This should synthesize a test phrase and show success.

# TTS Installation Guide

## Standard Installation (Recommended)

This is the correct installation process to avoid the pkuseg dependency conflict:

```bash
# Step 1: Install all dependencies from requirements.txt
pip install -r requirements.txt

# Step 2: Install chatterbox-tts WITHOUT its dependencies
# (we already installed the correct versions in step 1)
pip install chatterbox-tts --no-deps

# Step 3: Test if it works
python -c "from chatterbox.tts import ChatterboxTTS; print('✓ ChatterboxTTS loaded successfully!')"
```

**Why this works:**
- `requirements.txt` has all the individual components chatterbox needs (torch, transformers, etc.)
- We install chatterbox-tts with `--no-deps` so it doesn't pull in conflicting versions (like pkuseg)
- You get full control over dependency versions

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

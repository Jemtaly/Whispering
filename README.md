# Whispering

Real-time speech transcription and translation using [faster-whisper](https://github.com/SYSTRAN/faster-whisper) and Google Translate. Available in both GUI and TUI versions.

## Features

- **Real-time transcription** with iterative refinement for accuracy
- **AI-powered text processing** - intelligent proofreading and translation with OpenRouter integration
- **Live translation** to 100+ languages via Google Translate or AI models
- **Auto-type to any app** - dictate directly into browsers, editors, chat apps
- **Editable transcript** - manually edit text and add paragraph breaks
- **GPU acceleration** with CUDA support for fast inference
- **Adaptive paragraph detection** based on speech pause patterns
- **Audio level meter** to verify microphone input
- **PipeWire/PulseAudio integration** for reliable audio capture
- **Multiple model sizes** from tiny to large-v3

## AI Features (Optional)

Whispering now includes powerful AI-powered text processing capabilities:

- **Intelligent Proofreading** - Fix spelling, grammar, and punctuation errors in real-time
- **Context-Aware Translation** - Better translations that understand speech patterns
- **Multiple AI Models** - Choose from Claude, GPT-4, Gemini, Llama, and more via OpenRouter
- **Smart Text Processing** - Configurable triggers (time-based or word count-based)
- **Processing Modes** - Proofread only, translate only, or combined processing

See [AI_SETUP.md](AI_SETUP.md) for complete setup instructions and configuration options.

## Requirements

- Python 3.8+
- Linux with PipeWire or PulseAudio (recommended)
- NVIDIA GPU with CUDA 12 (optional, for GPU acceleration)

## Installation

```bash
# Clone the repository
git clone https://github.com/Jemtaly/Whispering.git
cd Whispering

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# For CUDA support, install NVIDIA libraries
pip install nvidia-cublas-cu12 nvidia-cudnn-cu12
```

## Dependencies

- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) - Fast Whisper inference with CTranslate2
- [sounddevice](https://python-sounddevice.readthedocs.io/) - Cross-platform audio I/O
- [numpy](https://numpy.org/) - Array processing
- [requests](https://requests.readthedocs.io/) - HTTP client for translation API
- [PyYAML](https://pyyaml.org/) - Configuration file parsing for AI features
- [python-dotenv](https://pypi.org/project/python-dotenv/) - Environment variable management for API keys
- [pyautogui](https://pyautogui.readthedocs.io/) - Optional, for auto-type feature (Windows/macOS/Linux X11)

## Usage

### GUI

Use the launcher script (recommended for CUDA support):

```bash
./run.sh
```

Or run directly:

```bash
python gui.py
```

**GUI Controls:**
- **Mic** - Select input device (system default uses PipeWire/PulseAudio)
- **Model** - Whisper model size (default: large-v3)
- **VAD** - Voice Activity Detection filter
- **¶** - Adaptive paragraph detection (inserts line breaks based on pauses)
- **⌨** - Auto-type: paste transcribed text into focused window
- **Device** - Inference device: cpu, cuda, or auto
- **Memory** - Number of previous segments used as context
- **Patience** - Seconds to wait before finalizing a segment
- **Timeout** - Translation service timeout
- **Source** - Source language (auto-detect if not set)
- **Target** - Target language (no translation if set to "none")
- **Level** - Real-time audio input level meter

### TUI

```bash
python tui.py [options]
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--mic` | auto | Microphone device name (partial match) |
| `--model` | large-v3 | Model: tiny, base, small, medium, large-v1/v2/v3 |
| `--device` | cuda | Inference device: cpu, cuda, auto |
| `--vad` | off | Enable voice activity detection |
| `--memory` | 3 | Previous segments used as prompt |
| `--patience` | 5.0 | Seconds before finalizing segment |
| `--timeout` | 5.0 | Translation timeout in seconds |
| `--prompt` | "" | Initial prompt for first segment |
| `--source` | auto | Source language code |
| `--target` | none | Target language code |
| `--no-para` | off | Disable adaptive paragraph detection |
| `--para-threshold` | 1.5 | Std deviations above mean for paragraph break |
| `--para-min-pause` | 0.8 | Minimum pause to consider (seconds) |
| `--para-max-chars` | 500 | Max characters per paragraph |
| `--para-max-words` | 100 | Max words per paragraph |

**Example:**

```bash
# Transcribe English, translate to Spanish, using GPU
python tui.py --source en --target es --device cuda

# Use specific microphone
python tui.py --mic "Webcam"
```

**TUI Controls:**
- `Space` - Start/Stop transcription
- `Q` - Quit

## Audio Device Selection

The application intelligently selects audio devices:

1. **System Default** - Uses the `pipewire` or `pulse` virtual device, which routes through your system's default microphone setting
2. **Named Devices** - Direct hardware access to specific microphones

**Supported Devices:**
- PipeWire virtual devices (recommended)
- PulseAudio virtual devices
- ALSA hardware devices with ≤8 channels

**Note:** JACK devices are excluded due to stability issues with PortAudio.

### Troubleshooting Audio

Run the debug script to check available devices:

```bash
python debug_audio.py
```

This will show:
- Available host APIs
- Recommended input devices
- Smart default device selection
- Quick recording test with level meter

## How It Works

### Transcription Pipeline

1. Audio is captured in real-time from the selected input device
2. Audio chunks are accumulated in a "transcription window"
3. The window is iteratively transcribed using Whisper
4. Text shown in **blue underline** is provisional (still in the window)
5. Text shown in **black** is finalized (moved out of window)
6. Recent finalized segments serve as context for subsequent transcription

### Translation

- Transcribed text is sent to Google Translate in real-time
- Source language can be auto-detected or specified
- Translation is skipped if target language is set to "none"

### Parameters Explained

**Patience:** Controls how long to wait for more speech before finalizing a segment.
- Too low: Sentences may be cut off mid-thought
- Too high: Transcription window grows large, slowing inference

**Memory:** Number of previous segments used as context prompt.
- Too low: Less context, potentially less accurate
- Too high: Long prompts slow down inference

### Adaptive Paragraph Detection

The paragraph detection feature automatically inserts line breaks based on the speaker's natural pause patterns:

1. **Learning phase:** During the first few segments, uses a fixed 2-second threshold
2. **Adaptive phase:** Calculates mean and standard deviation of all pauses
3. **Break detection:** Inserts paragraph break when pause exceeds `mean + (threshold × std_dev)`
4. **Hard limits:** Forces breaks at `max_chars` or `max_words` regardless of pauses

**How it adapts:**
- Fast speakers with short pauses: threshold adjusts lower
- Slow speakers with long pauses: threshold adjusts higher
- The `min_pause` floor prevents false positives from very brief hesitations

**Tuning tips:**
- Increase `--para-threshold` (e.g., 2.0) for fewer, longer paragraphs
- Decrease `--para-threshold` (e.g., 1.0) for more frequent breaks
- Adjust `--para-min-pause` if natural speech hesitations trigger false breaks

### Auto-Type Feature

The auto-type feature (⌨ checkbox) types transcribed text directly into the currently focused window as you speak. This allows you to dictate into any application: browsers, text editors, chat apps, etc.

**How it works:**
1. Enable the ⌨ checkbox before clicking Start
2. Click on the target window (browser, Discord, VS Code, etc.) to focus it
3. Speak into your microphone
4. Text appears in the focused window as it's transcribed

**Platform support:**

| Platform | Method | Setup Required |
|----------|--------|----------------|
| Windows | pyautogui | `pip install pyautogui` |
| macOS | pyautogui | `pip install pyautogui` + Accessibility permissions |
| Linux X11 | xdotool (preferred) | `sudo apt install xdotool xclip` |
| Linux Wayland | wtype or ydotool | See below |

**Linux X11 setup (recommended):**

```bash
# Install xdotool and xclip (fast, no Python packages needed)
sudo apt install xdotool xclip

# Or on Arch
sudo pacman -S xdotool xclip
```

**Linux Wayland setup:**

```bash
# Option 1: wtype + wl-clipboard (recommended for Wayland-native apps)
sudo apt install wtype wl-clipboard

# Option 2: ydotool (works with XWayland apps too)
sudo apt install ydotool
sudo systemctl enable --now ydotool
sudo usermod -aG input $USER  # then re-login
```

**Editing the transcript:**

The left text window is now editable! You can:
- Click anywhere to place cursor and edit text
- Press Enter to add manual paragraph breaks
- Select and delete text
- Copy/paste within the window

**Check your setup:**

```bash
python autotype.py --check
```

**Test auto-typing:**

```bash
python autotype.py --test "Hello, world!"
# Click on target window within 3 seconds
```

## CUDA Setup

For GPU acceleration with CUDA 12:

```bash
# Install CUDA libraries in virtualenv
pip install nvidia-cublas-cu12 nvidia-cudnn-cu12

# The run.sh script automatically sets LD_LIBRARY_PATH
./run.sh
```

If you have CUDA 13 installed system-wide, the pip packages provide CUDA 12 libraries that faster-whisper requires.

## File Structure

```
Whispering/
├── gui.py           # GUI application (Tkinter)
├── tui.py           # TUI application (curses)
├── core.py          # Core transcription/translation logic
├── cmque.py         # Thread-safe queue utilities
├── autotype.py      # Cross-platform typing utility
├── ai_provider.py   # OpenRouter AI integration
├── ai_config.py     # AI configuration loader
├── ai_config.yaml   # AI models and prompts configuration
├── settings.py      # Settings persistence framework
├── .env.example     # Example environment variables template
├── AI_SETUP.md      # AI features setup guide
├── run.sh           # Launcher script (sets CUDA paths)
├── debug_audio.py   # Audio device diagnostics
└── requirements.txt # Python dependencies
```

## Extending

The core logic in `core.py` separates transcription and translation cleanly:

- **Transcription:** Uses faster-whisper with configurable model and device
- **Translation:** Uses Google Translate API (can be replaced with other services)
- **Audio capture:** Uses sounddevice with automatic resampling to 16kHz mono

To use a different translation service, modify the `translate()` function in `core.py`.

## Troubleshooting

**"Library libcublas.so.12 is not found"**
- Install CUDA 12 libraries: `pip install nvidia-cublas-cu12 nvidia-cudnn-cu12`
- Use the `run.sh` launcher script

**Audio device crashes or hangs**
- Use the `pipewire` or `pulse` virtual device instead of direct hardware
- Run `debug_audio.py` to identify stable devices
- Avoid JACK devices (known stability issues)

**No audio level shown**
- Check that the correct microphone is selected
- Verify microphone isn't muted in system settings
- Run `debug_audio.py` to test recording

**Slow transcription**
- Use a smaller model (base, small) instead of large-v3
- Enable CUDA if you have an NVIDIA GPU
- Reduce the `memory` parameter

**Auto-type not working**
- Run `python autotype.py --check` to see available backends
- Linux X11: Install xdotool and xclip: `sudo apt install xdotool xclip`
- Linux Wayland: Install wtype: `sudo apt install wtype wl-clipboard`
- Windows/macOS: Install pyautogui: `pip install pyautogui`
- Test with: `python autotype.py --test "Hello"`

## License

MIT License

## Acknowledgments

- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) - Fast Whisper implementation
- [OpenAI Whisper](https://github.com/openai/whisper) - Original speech recognition model
- [Google Translate](https://translate.google.com/) - Translation service

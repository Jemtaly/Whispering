#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Find Python version in venv
PYTHON_VERSION=$(ls "$SCRIPT_DIR/.venv/lib/" | grep python | head -1)
VENV_SITE="$SCRIPT_DIR/.venv/lib/$PYTHON_VERSION/site-packages"

# Add NVIDIA CUDA libraries to path
export LD_LIBRARY_PATH="$VENV_SITE/nvidia/cublas/lib:$VENV_SITE/nvidia/cudnn/lib:$LD_LIBRARY_PATH"

# Prefer PulseAudio/PipeWire over ALSA for audio
export SDL_AUDIODRIVER=pulse

source "$SCRIPT_DIR/.venv/bin/activate"

# Run GUI, filtering ALSA noise but keeping real errors
python "$SCRIPT_DIR/gui.py" "$@" 2> >(grep -v "^ALSA lib\|^Expression '" >&2)

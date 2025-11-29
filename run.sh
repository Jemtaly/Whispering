#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Find Python version in venv
PYTHON_VERSION=$(ls "$SCRIPT_DIR/.venv/lib/" | grep python | head -1)
VENV_SITE="$SCRIPT_DIR/.venv/lib/$PYTHON_VERSION/site-packages"

# IMPORTANT: PyTorch comes with its own bundled cuDNN
# DO NOT add nvidia/cudnn to LD_LIBRARY_PATH - it causes version conflicts
# Only add cublas if needed for CUDA operations
if [ -d "$VENV_SITE/nvidia/cublas/lib" ]; then
    export LD_LIBRARY_PATH="$VENV_SITE/nvidia/cublas/lib:$LD_LIBRARY_PATH"
fi

# Prefer PulseAudio/PipeWire over ALSA for audio
export SDL_AUDIODRIVER=pulse

source "$SCRIPT_DIR/.venv/bin/activate"

# Debug mode: uncomment to see full errors
# python "$SCRIPT_DIR/gui.py" "$@"

# Production mode: filter ALSA noise
python "$SCRIPT_DIR/gui.py" "$@" 2> >(grep -v "^ALSA lib\|^Expression '" >&2)

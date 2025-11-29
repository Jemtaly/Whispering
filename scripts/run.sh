#!/bin/bash
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# IMPORTANT: PyTorch comes with its own bundled CUDA libraries (cuDNN, cuBLAS, etc.)
# DO NOT set LD_LIBRARY_PATH - let PyTorch find its own libraries
# Uncomment the lines below ONLY if you get "libcublas.so not found" errors

# Find Python version in venv (commented out for now)
# PYTHON_VERSION=$(ls "$PROJECT_DIR/.venv/lib/" | grep python | head -1)
# VENV_SITE="$PROJECT_DIR/.venv/lib/$PYTHON_VERSION/site-packages"
# export LD_LIBRARY_PATH="$VENV_SITE/nvidia/cublas/lib:$LD_LIBRARY_PATH"

# Prefer PulseAudio/PipeWire over ALSA for audio
export SDL_AUDIODRIVER=pulse

source "$PROJECT_DIR/.venv/bin/activate"

# Add src to Python path
export PYTHONPATH="$PROJECT_DIR/src:$PYTHONPATH"

# Debug mode: uncomment to see full errors
# python "$PROJECT_DIR/src/gui.py" "$@"

# Production mode: filter ALSA noise
python "$PROJECT_DIR/src/gui.py" "$@" 2> >(grep -v "^ALSA lib\|^Expression '" >&2)

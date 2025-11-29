#!/usr/bin/env python3
"""
Debug script to check CUDA, PyTorch, and TTS setup.
"""

import sys

print("=" * 60)
print("CUDA & TTS Environment Check")
print("=" * 60)

# 1. Check Python version
print(f"\n1. Python Version: {sys.version}")

# 2. Check PyTorch
try:
    import torch
    print(f"\n2. PyTorch:")
    print(f"   Version: {torch.__version__}")
    print(f"   CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"   CUDA version: {torch.version.cuda}")
        print(f"   cuDNN version: {torch.backends.cudnn.version()}")
        print(f"   GPU: {torch.cuda.get_device_name(0)}")
    else:
        print("   ⚠ CUDA not available - will use CPU")
except ImportError as e:
    print(f"\n2. PyTorch: ❌ NOT INSTALLED ({e})")

# 3. Check TTS dependencies
print(f"\n3. TTS Dependencies:")

deps = [
    "torchaudio",
    "soundfile",
    "librosa",
    "transformers",
    "diffusers",
    "omegaconf",
]

for dep in deps:
    try:
        mod = __import__(dep)
        version = getattr(mod, "__version__", "unknown")
        print(f"   ✓ {dep}: {version}")
    except ImportError:
        print(f"   ❌ {dep}: NOT INSTALLED")

# 4. Check ChatterboxTTS
print(f"\n4. ChatterboxTTS:")
try:
    from chatterbox.tts import ChatterboxTTS
    print(f"   ✓ chatterbox.tts: Available")

    # Try to initialize (this will test CUDA/cuDNN)
    print(f"   Testing initialization...")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = ChatterboxTTS.from_pretrained(device=device)
    print(f"   ✓ Model loaded successfully on {device}")

    # Try synthesis
    print(f"   Testing synthesis...")
    wav = model.generate("Test")
    print(f"   ✓ Synthesis works! Generated {len(wav[0])} samples")

except ImportError as e:
    print(f"   ❌ chatterbox NOT installed ({e})")
    print(f"   Run: pip install chatterbox-tts --no-deps")
except Exception as e:
    print(f"   ❌ Error initializing: {e}")
    print(f"\n   Detailed error:")
    import traceback
    traceback.print_exc()

# 5. Check TTS controller
print(f"\n5. TTS Controller:")
try:
    from tts_controller import TTSController
    controller = TTSController(device="auto")
    print(f"   ✓ TTSController loaded")
    print(f"   Device: {controller.provider.get_device()}")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n" + "=" * 60)
print("Summary:")
print("=" * 60)

if torch.cuda.is_available():
    print("✓ CUDA is working")
else:
    print("⚠ CUDA not available - TTS will be SLOW on CPU")

try:
    from chatterbox.tts import ChatterboxTTS
    print("✓ ChatterboxTTS is installed")
except:
    print("❌ ChatterboxTTS not available")

print("\nIf you see errors above, check:")
print("1. PyTorch CUDA version matches your system")
print("2. No conflicting cuDNN in LD_LIBRARY_PATH (check run.sh)")
print("3. chatterbox-tts is installed: pip install chatterbox-tts --no-deps")
print("=" * 60)

#!/usr/bin/env python3
"""Debug script to check audio devices and host APIs."""

import sounddevice as sd
import numpy as np

print("=" * 60)
print("HOST APIs:")
print("=" * 60)
for i, api in enumerate(sd.query_hostapis()):
    print(f"  [{i}] {api['name']}")
    print(f"      default_input: {api.get('default_input_device', 'N/A')}")
    print(f"      default_output: {api.get('default_output_device', 'N/A')}")
    print()

print("=" * 60)
print("RECOMMENDED INPUT DEVICES (ALSA only, stable):")
print("=" * 60)
recommended = []
for i, d in enumerate(sd.query_devices()):
    if d['max_input_channels'] > 0:
        name = d['name']
        name_lower = name.lower()
        api_name = sd.query_hostapis(d['hostapi'])['name'].lower()
        
        # Only recommend ALSA devices (JACK crashes)
        if 'alsa' not in api_name:
            continue
            
        # Skip problematic default
        if name_lower == 'default':
            continue
            
        # Highlight good choices
        is_recommended = (
            'pipewire' in name_lower or 
            name_lower == 'pulse' or
            ('hw:' in name and d['max_input_channels'] <= 4)
        )
        if is_recommended:
            recommended.append(i)
            print(f"  ★ [{i}] {d['name']}")
            print(f"        channels: {d['max_input_channels']}, rate: {d['default_samplerate']}")
            print()

print("=" * 60)
print("ALL ALSA INPUT DEVICES (JACK excluded - causes crashes):")
print("=" * 60)
for i, d in enumerate(sd.query_devices()):
    if d['max_input_channels'] > 0:
        api_name = sd.query_hostapis(d['hostapi'])['name']
        if 'alsa' not in api_name.lower():
            continue
        marker = "★" if i in recommended else " "
        warn = " ⚠ HIGH CHANNELS" if d['max_input_channels'] > 32 else ""
        print(f"  {marker}[{i}] {d['name']}{warn}")
        print(f"        channels: {d['max_input_channels']}, rate: {d['default_samplerate']}")
        print()

# Smart default
smart_default = None
for i, d in enumerate(sd.query_devices()):
    if d['name'].lower() == 'pipewire' and d['max_input_channels'] > 0:
        smart_default = i
        break
if smart_default is None:
    for i, d in enumerate(sd.query_devices()):
        if d['name'].lower() == 'pulse' and d['max_input_channels'] > 0:
            smart_default = i
            break

print("=" * 60)
print("SMART DEFAULT DEVICE (used by app):")
print("=" * 60)
if smart_default is not None:
    d = sd.query_devices(smart_default)
    print(f"  Index: {smart_default}")
    print(f"  Name: {d['name']}")
    print(f"  Channels: {d['max_input_channels']} (app will use max 2)")
    print(f"  Sample rate: {d['default_samplerate']}")
else:
    print("  No smart default found!")

# Test with recommended device
test_device = smart_default if smart_default else (recommended[0] if recommended else None)

print()
print("=" * 60)
print(f"QUICK TEST - Recording 1 second from device {test_device}...")
print("=" * 60)
try:
    if test_device is not None:
        device_info = sd.query_devices(test_device)
        sample_rate = int(device_info['default_samplerate'])
        channels = min(2, device_info['max_input_channels'])
        device_name = device_info['name']
    else:
        raise RuntimeError("No suitable device found")
    
    print(f"  Device: {device_name}")
    print(f"  Sample rate: {sample_rate}, Channels: {channels}")
    print("  Recording...")
    
    audio = sd.rec(
        int(1 * sample_rate), 
        samplerate=sample_rate, 
        channels=channels, 
        dtype='int16',
        device=test_device
    )
    sd.wait()
    
    rms = np.sqrt(np.mean(audio.astype(np.float32)**2))
    peak = np.max(np.abs(audio))
    
    print(f"  ✓ Recorded {len(audio)} samples")
    print(f"  RMS level: {rms:.1f}")
    print(f"  Peak level: {peak}")
    
    if peak > 100:
        print("  ✓ Audio is being captured!")
    else:
        print("  ⚠ Very low audio level - mic might be muted")
        
except Exception as e:
    print(f"  ✗ Error: {e}")
    import traceback
    traceback.print_exc()

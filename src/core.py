#!/usr/bin/env python3

from core_parts.paragraph_detector import ParagraphDetector
from core_parts.audio_devices import (
    TARGET_SAMPLE_RATE, SAMPLE_WIDTH, CHUNK_DURATION,
    get_preferred_hostapi_index, get_mic_names, get_default_device_index,
    get_mic_index, get_device_info, audio_to_wav_bytes, resample_to_mono_16k
)
from core_parts.processing import (
    translate, parse_ai_proofread_translate, ai_translate, proc
)

# Re-export constants
models = ["tiny", "base", "small", "medium", "large-v1", "large-v2", "large-v3", "large"]
devices = ["cpu", "cuda", "auto"]
sources = ["af", "am", "ar", "as", "az", "ba", "be", "bg", "bn", "bo", "br", "bs", "ca", "cs", "cy", "da", "de", "el", "en", "es", "et", "eu", "fa", "fi", "fo", "fr", "gl", "gu", "ha", "haw", "he", "hi", "hr", "ht", "hu", "hy", "id", "is", "it", "ja", "jw", "ka", "kk", "km", "kn", "ko", "la", "lb", "ln", "lo", "lt", "lv", "mg", "mi", "mk", "ml", "mn", "mr", "ms", "mt", "my", "ne", "nl", "nn", "no", "oc", "pa", "pl", "ps", "pt", "ro", "ru", "sa", "sd", "si", "sk", "sl", "sn", "so", "sq", "sr", "su", "sv", "sw", "ta", "te", "tg", "th", "tk", "tl", "tr", "tt", "uk", "ur", "uz", "vi", "yi", "yo", "yue", "zh"]
targets = ["af", "ak", "am", "ar", "as", "ay", "az", "be", "bg", "bho", "bm", "bn", "bs", "ca", "ceb", "ckb", "co", "cs", "cy", "da", "de", "doi", "dv", "ee", "el", "en", "eo", "es", "et", "eu", "fa", "fi", "fil", "fr", "fy", "ga", "gd", "gl", "gn", "gom", "gu", "ha", "haw", "he", "hi", "hmn", "hr", "ht", "hu", "hy", "id", "ig", "ilo", "is", "it", "ja", "jw", "ka", "kk", "km", "kn", "ko", "kri", "ku", "ky", "la", "lb", "lg", "ln", "lo", "lt", "lus", "lv", "mai", "mg", "mi", "mk", "ml", "mn", "mni-Mtei", "mr", "ms", "mt", "my", "ne", "nl", "no", "nso", "ny", "om", "or", "pa", "pl", "ps", "pt", "qu", "ro", "ru", "rw", "sa", "sd", "si", "sk", "sl", "sm", "sn", "so", "sq", "sr", "st", "su", "sv", "sw", "ta", "te", "tg", "th", "ti", "tk", "tl", "tr", "ts", "tt", "ug", "uk", "ur", "uz", "vi", "xh", "yi", "yo", "zh-CN", "zh-TW", "zu"]

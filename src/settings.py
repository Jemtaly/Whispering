#!/usr/bin/env python3
"""
Settings Manager
Saves and loads user preferences for Whispering application
"""

import json
from pathlib import Path
from typing import Dict, Any


class Settings:
    """Manages application settings persistence."""

    def __init__(self, settings_file: str = "whispering_settings.json"):
        self.settings_file = Path(settings_file)
        self.defaults = {
            "mic_index": 0,
            "model": "large-v3",
            "vad": True,
            "para_detect": True,
            "autotype": False,
            "device": "cuda",
            "memory": 3,
            "patience": 5.0,
            "timeout": 5.0,
            "source": "auto",
            "target": "none",
            "prompt": "",
            "ai_enabled": False,
            "ai_mode": "Proofread",
            "ai_model_index": 0,
            "ai_process_interval": 20,  # Seconds between AI processing (changed from minutes to seconds)
            "ai_trigger_mode": "time",  # "time" or "words"
            "ai_process_words": 150,  # Words per processing batch
            "text_visible": True,  # Text windows visible by default
            "auto_stop_enabled": False,  # Auto-stop disabled by default
            "auto_stop_minutes": 5  # Auto-stop after N minutes of inactivity
        }
        self.settings = self.load()

    def load(self) -> Dict[str, Any]:
        """Load settings from file, or return defaults if file doesn't exist."""
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r') as f:
                    loaded = json.load(f)
                    # Merge with defaults (in case new settings were added)
                    return {**self.defaults, **loaded}
            except Exception as e:
                print(f"Error loading settings: {e}")
                return self.defaults.copy()
        return self.defaults.copy()

    def save(self, settings: Dict[str, Any] = None):
        """Save settings to file."""
        if settings:
            self.settings = settings

        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def get(self, key: str, default=None):
        """Get a setting value."""
        return self.settings.get(key, default)

    def set(self, key: str, value: Any):
        """Set a setting value."""
        self.settings[key] = value

    def update(self, updates: Dict[str, Any]):
        """Update multiple settings at once."""
        self.settings.update(updates)

"""Debug output control module.

Reads debug settings from configuration and provides a simple
debug_print() function that only outputs when debug mode is enabled.
"""

from settings import Settings

# Module-level settings instance
_settings = None
DEBUG_ENABLED = False


def _load_debug_setting():
    """Load debug setting from configuration file."""
    global _settings, DEBUG_ENABLED
    if _settings is None:
        _settings = Settings()
    DEBUG_ENABLED = _settings.get("debug_enabled", False)
    return DEBUG_ENABLED


# Load on module import
_load_debug_setting()


def debug_print(*args, **kwargs):
    """Print debug message only if debug mode is enabled in settings."""
    if DEBUG_ENABLED:
        print(*args, **kwargs)

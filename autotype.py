#!/usr/bin/env python3
"""
Cross-platform auto-type module for pasting text into focused windows.

Supports multiple backends:
- Linux X11: xdotool + xclip (preferred)
- Linux Wayland: wtype + wl-clipboard or ydotool
- Windows: pyautogui
- macOS: pyautogui

Uses clipboard + paste approach for reliable Unicode support.
"""

import argparse
import os
import platform
import subprocess
import sys
import time
from typing import Optional, Tuple


class AutoTypeBackend:
    """Base class for auto-type backends."""

    def __init__(self):
        self.name = "unknown"
        self.available = False

    def check_available(self) -> bool:
        """Check if this backend is available on the system."""
        return False

    def set_clipboard(self, text: str) -> bool:
        """Set clipboard contents. Returns True on success."""
        return False

    def paste(self) -> bool:
        """Trigger paste operation. Returns True on success."""
        return False

    def move_to_end(self) -> bool:
        """Move cursor to end of text field. Override in subclasses if needed."""
        return True  # Default: no-op, rely on paste behavior

    def type_text(self, text: str, restore_clipboard: bool = True, move_to_end: bool = True) -> bool:
        """
        Type text into the focused window.

        Args:
            text: Text to type
            restore_clipboard: Whether to restore original clipboard (default: True)
            move_to_end: Whether to move cursor to end before pasting (default: True)

        Returns:
            True if successful, False otherwise
        """
        if not text:
            return True

        # Save original clipboard if requested
        old_clipboard = None
        if restore_clipboard:
            old_clipboard = self.get_clipboard()

        # Set clipboard to new text
        if not self.set_clipboard(text):
            return False

        # Small delay to ensure clipboard is set
        time.sleep(0.05)

        # Move to end if requested
        if move_to_end:
            self.move_to_end()
            time.sleep(0.02)

        # Paste
        success = self.paste()

        # Restore clipboard if requested
        if restore_clipboard and old_clipboard is not None:
            time.sleep(0.05)
            self.set_clipboard(old_clipboard)

        return success

    def get_clipboard(self) -> Optional[str]:
        """Get current clipboard contents."""
        return None


class XdotoolBackend(AutoTypeBackend):
    """Linux X11 backend using xdotool + xclip."""

    def __init__(self):
        super().__init__()
        self.name = "xdotool + xclip"
        self.available = self.check_available()

    def check_available(self) -> bool:
        try:
            # Check if running X11
            if os.environ.get('WAYLAND_DISPLAY'):
                return False
            if not os.environ.get('DISPLAY'):
                return False

            # Check for xdotool and xclip
            subprocess.run(['which', 'xdotool'], capture_output=True, check=True)
            subprocess.run(['which', 'xclip'], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def set_clipboard(self, text: str) -> bool:
        try:
            subprocess.run(
                ['xclip', '-selection', 'clipboard'],
                input=text.encode('utf-8'),
                check=True,
                capture_output=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def get_clipboard(self) -> Optional[str]:
        try:
            result = subprocess.run(
                ['xclip', '-selection', 'clipboard', '-o'],
                capture_output=True,
                check=True
            )
            return result.stdout.decode('utf-8', errors='ignore')
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None

    def move_to_end(self) -> bool:
        """Move cursor to end of text using Ctrl+End."""
        try:
            result = subprocess.run(
                ['xdotool', 'getwindowfocus'],
                capture_output=True,
                check=True
            )
            window_id = result.stdout.decode('utf-8').strip()

            # Send Ctrl+End to move to end
            subprocess.run(
                ['xdotool', 'key', '--window', window_id, 'ctrl+End'],
                check=True,
                capture_output=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def paste(self) -> bool:
        try:
            # Get focused window
            result = subprocess.run(
                ['xdotool', 'getwindowfocus'],
                capture_output=True,
                check=True
            )
            window_id = result.stdout.decode('utf-8').strip()

            # Send Ctrl+V to paste
            subprocess.run(
                ['xdotool', 'key', '--window', window_id, 'ctrl+v'],
                check=True,
                capture_output=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False


class WtypeBackend(AutoTypeBackend):
    """Linux Wayland backend using wtype + wl-clipboard."""

    def __init__(self):
        super().__init__()
        self.name = "wtype + wl-clipboard"
        self.available = self.check_available()

    def check_available(self) -> bool:
        try:
            # Check if running Wayland
            if not os.environ.get('WAYLAND_DISPLAY'):
                return False

            # Check for wtype and wl-copy
            subprocess.run(['which', 'wtype'], capture_output=True, check=True)
            subprocess.run(['which', 'wl-copy'], capture_output=True, check=True)
            subprocess.run(['which', 'wl-paste'], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def set_clipboard(self, text: str) -> bool:
        try:
            subprocess.run(
                ['wl-copy'],
                input=text.encode('utf-8'),
                check=True,
                capture_output=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def get_clipboard(self) -> Optional[str]:
        try:
            result = subprocess.run(
                ['wl-paste'],
                capture_output=True,
                check=True
            )
            return result.stdout.decode('utf-8', errors='ignore')
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None

    def move_to_end(self) -> bool:
        """Move cursor to end using Ctrl+End."""
        try:
            # Send Ctrl+End using wtype
            subprocess.run(
                ['wtype', '-M', 'ctrl', '-P', 'End', '-p', 'End', '-m', 'ctrl'],
                check=True,
                capture_output=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def paste(self) -> bool:
        try:
            # Send Ctrl+V using wtype
            subprocess.run(
                ['wtype', '-M', 'ctrl', '-P', 'v', '-p', 'v', '-m', 'ctrl'],
                check=True,
                capture_output=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False


class YdotoolBackend(AutoTypeBackend):
    """Linux Wayland backend using ydotool."""

    def __init__(self):
        super().__init__()
        self.name = "ydotool + wl-clipboard"
        self.available = self.check_available()

    def check_available(self) -> bool:
        try:
            # Check for ydotool and wl-copy
            subprocess.run(['which', 'ydotool'], capture_output=True, check=True)
            subprocess.run(['which', 'wl-copy'], capture_output=True, check=True)
            subprocess.run(['which', 'wl-paste'], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def set_clipboard(self, text: str) -> bool:
        try:
            subprocess.run(
                ['wl-copy'],
                input=text.encode('utf-8'),
                check=True,
                capture_output=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def get_clipboard(self) -> Optional[str]:
        try:
            result = subprocess.run(
                ['wl-paste'],
                capture_output=True,
                check=True
            )
            return result.stdout.decode('utf-8', errors='ignore')
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None

    def move_to_end(self) -> bool:
        """Move cursor to end using Ctrl+End."""
        try:
            # Send Ctrl+End using ydotool (Ctrl=29, End=107)
            subprocess.run(
                ['ydotool', 'key', '29:1', '107:1', '107:0', '29:0'],  # Ctrl down, End down, End up, Ctrl up
                check=True,
                capture_output=True,
                timeout=2
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def paste(self) -> bool:
        try:
            # Send Ctrl+V using ydotool (Ctrl=29, V=47)
            subprocess.run(
                ['ydotool', 'key', '29:1', '47:1', '47:0', '29:0'],  # Ctrl down, V down, V up, Ctrl up
                check=True,
                capture_output=True,
                timeout=2
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return False


class PyAutoGUIBackend(AutoTypeBackend):
    """Cross-platform backend using pyautogui."""

    def __init__(self):
        super().__init__()
        self.name = "pyautogui"
        self.available = self.check_available()
        self.pyautogui = None
        if self.available:
            import pyautogui
            self.pyautogui = pyautogui
            # Disable fail-safe for automation
            self.pyautogui.FAILSAFE = False

    def check_available(self) -> bool:
        try:
            import pyautogui
            return True
        except ImportError:
            return False

    def set_clipboard(self, text: str) -> bool:
        if not self.pyautogui:
            return False
        try:
            # Try to use pyperclip (usually installed with pyautogui)
            import pyperclip
            pyperclip.copy(text)
            return True
        except ImportError:
            # Fallback to platform-specific clipboard
            system = platform.system()
            try:
                if system == 'Darwin':  # macOS
                    subprocess.run(['pbcopy'], input=text.encode('utf-8'), check=True)
                elif system == 'Linux':
                    # Try xclip first, then wl-copy
                    try:
                        subprocess.run(['xclip', '-selection', 'clipboard'],
                                     input=text.encode('utf-8'), check=True)
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        subprocess.run(['wl-copy'], input=text.encode('utf-8'), check=True)
                elif system == 'Windows':
                    # Windows has built-in clipboard in pyautogui
                    import win32clipboard
                    win32clipboard.OpenClipboard()
                    win32clipboard.EmptyClipboard()
                    win32clipboard.SetClipboardText(text)
                    win32clipboard.CloseClipboard()
                return True
            except Exception:
                return False

    def get_clipboard(self) -> Optional[str]:
        try:
            import pyperclip
            return pyperclip.paste()
        except ImportError:
            return None

    def move_to_end(self) -> bool:
        """Move cursor to end using Ctrl+End or Cmd+Down."""
        if not self.pyautogui:
            return False
        try:
            system = platform.system()
            if system == 'Darwin':  # macOS uses Cmd+Down to go to end
                self.pyautogui.hotkey('command', 'down')
            else:  # Windows, Linux use Ctrl+End
                self.pyautogui.hotkey('ctrl', 'end')
            return True
        except Exception:
            return False

    def paste(self) -> bool:
        if not self.pyautogui:
            return False
        try:
            # Detect platform for correct hotkey
            system = platform.system()
            if system == 'Darwin':  # macOS
                self.pyautogui.hotkey('command', 'v')
            else:  # Windows, Linux
                self.pyautogui.hotkey('ctrl', 'v')
            return True
        except Exception:
            return False


def detect_backend() -> Optional[AutoTypeBackend]:
    """Detect the best available backend for the current platform."""
    backends = [
        XdotoolBackend(),      # Preferred for Linux X11
        WtypeBackend(),        # Preferred for Wayland
        YdotoolBackend(),      # Alternative for Wayland
        PyAutoGUIBackend(),    # Cross-platform fallback
    ]

    for backend in backends:
        if backend.available:
            return backend

    return None


# Global backend instance
_backend: Optional[AutoTypeBackend] = None


def get_backend() -> Optional[AutoTypeBackend]:
    """Get or initialize the global backend."""
    global _backend
    if _backend is None:
        _backend = detect_backend()
    return _backend


def type_text(text: str, restore_clipboard: bool = True, move_to_end: bool = True) -> bool:
    """
    Type text into the focused window.

    Args:
        text: Text to type
        restore_clipboard: Whether to restore original clipboard after typing
        move_to_end: Move cursor to end of text before pasting (default: True)

    Returns:
        True if successful, False if no backend available or operation failed
    """
    backend = get_backend()
    if not backend:
        return False

    return backend.type_text(text, restore_clipboard, move_to_end)


def check_backends() -> Tuple[Optional[AutoTypeBackend], list]:
    """
    Check all available backends.

    Returns:
        (selected_backend, all_backends) tuple
    """
    backends = [
        XdotoolBackend(),
        WtypeBackend(),
        YdotoolBackend(),
        PyAutoGUIBackend(),
    ]

    selected = None
    for backend in backends:
        if backend.available and selected is None:
            selected = backend

    return selected, backends


def main():
    """CLI interface for autotype."""
    parser = argparse.ArgumentParser(description="Auto-type text into focused windows")
    parser.add_argument('--check', action='store_true', help="Check available backends")
    parser.add_argument('--test', type=str, help="Test typing with given text")
    args = parser.parse_args()

    if args.check:
        print("Checking auto-type backends...")
        print(f"Platform: {platform.system()}")
        print(f"Display: X11={bool(os.environ.get('DISPLAY'))}, "
              f"Wayland={bool(os.environ.get('WAYLAND_DISPLAY'))}")
        print()

        selected, backends = check_backends()

        for backend in backends:
            status = "✓ AVAILABLE" if backend.available else "✗ Not available"
            marker = " [SELECTED]" if backend == selected else ""
            print(f"{status}: {backend.name}{marker}")

        if not selected:
            print("\n⚠ WARNING: No auto-type backend available!")
            print("\nInstall options:")
            print("  Linux X11:  sudo apt install xdotool xclip")
            print("  Linux Wayland:  sudo apt install wtype wl-clipboard")
            print("  Cross-platform:  pip install pyautogui")
            sys.exit(1)
        else:
            print(f"\n✓ Auto-type is ready using: {selected.name}")
            sys.exit(0)

    elif args.test:
        print(f"Testing auto-type with: \"{args.test}\"")
        backend = get_backend()

        if not backend:
            print("ERROR: No auto-type backend available")
            print("Run with --check to see installation options")
            sys.exit(1)

        print(f"Using backend: {backend.name}")
        print("Click on target window within 3 seconds...")

        for i in range(3, 0, -1):
            print(f"  {i}...")
            time.sleep(1)

        print("Typing now...")
        success = type_text(args.test, restore_clipboard=True)

        if success:
            print("✓ Success!")
            sys.exit(0)
        else:
            print("✗ Failed to type text")
            sys.exit(1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

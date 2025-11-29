#!/usr/bin/env python3
"""
Cross-platform module to type text into the currently focused window.

Uses clipboard + paste approach for maximum compatibility:
- Windows: pyautogui (Ctrl+V)
- macOS: pyautogui (Cmd+V)
- Linux X11: xdotool (preferred) or pyautogui (Ctrl+V)
- Linux Wayland: wtype or ydotool (Ctrl+V)

Dependencies:
- xdotool (Linux X11, usually pre-installed)
- pyautogui (Windows, macOS, Linux X11 fallback)
- wtype or ydotool (Linux Wayland only)
"""

import os
import platform
import shutil
import subprocess
import sys
import time


def get_platform_info():
    """Detect platform and display server."""
    system = platform.system().lower()

    if system == "linux":
        # Check for Wayland
        wayland = os.environ.get("WAYLAND_DISPLAY") or os.environ.get("XDG_SESSION_TYPE") == "wayland"
        return ("linux_wayland" if wayland else "linux_x11", wayland)
    elif system == "darwin":
        return ("macos", False)
    elif system == "windows":
        return ("windows", False)
    else:
        return ("unknown", False)


def check_dependencies():
    """Check which typing backends are available."""
    plat, is_wayland = get_platform_info()
    available = []
    missing = []

    # Check xdotool (Linux X11 - preferred)
    if plat == "linux_x11":
        if shutil.which("xdotool"):
            available.append("xdotool")
        else:
            missing.append("xdotool")

    # Check pyautogui (Windows, macOS, Linux X11 fallback)
    if plat != "linux_wayland":
        try:
            import pyautogui
            available.append("pyautogui")
        except ImportError:
            if plat != "linux_x11" or "xdotool" not in available:
                missing.append("pyautogui")

    # Check Wayland tools
    if plat == "linux_wayland":
        if shutil.which("wtype"):
            available.append("wtype")
        elif shutil.which("ydotool"):
            available.append("ydotool")
        else:
            missing.append("wtype or ydotool")

    return {
        "platform": plat,
        "is_wayland": is_wayland,
        "available": available,
        "missing": missing,
        "can_type": len(available) > 0
    }


def _copy_to_clipboard_xclip(text):
    """Copy text to clipboard using xclip (Linux)."""
    try:
        proc = subprocess.Popen(
            ["xclip", "-selection", "clipboard"],
            stdin=subprocess.PIPE,
            stderr=subprocess.DEVNULL
        )
        proc.communicate(input=text.encode("utf-8"))
        return proc.returncode == 0
    except FileNotFoundError:
        return False


def _copy_to_clipboard_xsel(text):
    """Copy text to clipboard using xsel (Linux)."""
    try:
        proc = subprocess.Popen(
            ["xsel", "--clipboard", "--input"],
            stdin=subprocess.PIPE,
            stderr=subprocess.DEVNULL
        )
        proc.communicate(input=text.encode("utf-8"))
        return proc.returncode == 0
    except FileNotFoundError:
        return False


def _copy_to_clipboard_wl(text):
    """Copy text to clipboard using wl-copy (Wayland)."""
    try:
        proc = subprocess.Popen(
            ["wl-copy"],
            stdin=subprocess.PIPE,
            stderr=subprocess.DEVNULL
        )
        proc.communicate(input=text.encode("utf-8"))
        return proc.returncode == 0
    except FileNotFoundError:
        return False


def _copy_to_clipboard_tk(text):
    """Copy text to system clipboard using tkinter (cross-platform)."""
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()  # Hide window
        root.clipboard_clear()
        root.clipboard_append(text)
        root.update()  # Required for clipboard to persist
        root.destroy()
        return True
    except Exception as e:
        print(f"Clipboard error: {e}", file=sys.stderr)
        return False


def _copy_to_clipboard(text):
    """Copy text to clipboard using best available method."""
    plat, is_wayland = get_platform_info()

    # Try platform-specific tools first (faster, more reliable)
    if is_wayland:
        if _copy_to_clipboard_wl(text):
            return True
    elif plat == "linux_x11":
        if _copy_to_clipboard_xclip(text):
            return True
        if _copy_to_clipboard_xsel(text):
            return True

    # Fallback to tkinter
    return _copy_to_clipboard_tk(text)


def _move_to_end_xdotool():
    """Move cursor to end of text using Ctrl+End with xdotool (X11)."""
    try:
        subprocess.run(
            ["xdotool", "key", "--clearmodifiers", "ctrl+End"],
            check=True,
            capture_output=True
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"xdotool error moving to end: {e}", file=sys.stderr)
        return False
    except FileNotFoundError:
        return False


def _paste_xdotool():
    """Simulate Ctrl+V using xdotool (X11)."""
    try:
        subprocess.run(
            ["xdotool", "key", "--clearmodifiers", "ctrl+v"],
            check=True,
            capture_output=True
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"xdotool error: {e}", file=sys.stderr)
        return False
    except FileNotFoundError:
        return False


def _move_to_end_pyautogui(is_macos=False):
    """Move cursor to end of text using Ctrl+End or Cmd+Down."""
    try:
        import pyautogui

        if is_macos:
            # macOS uses Cmd+Down to go to end
            pyautogui.hotkey("command", "down")
        else:
            # Windows/Linux use Ctrl+End
            pyautogui.hotkey("ctrl", "end")
        return True
    except Exception as e:
        print(f"pyautogui error moving to end: {e}", file=sys.stderr)
        return False


def _paste_pyautogui(is_macos=False):
    """Simulate paste keystroke using pyautogui."""
    try:
        import pyautogui

        # Small delay to ensure clipboard is ready
        time.sleep(0.02)

        if is_macos:
            pyautogui.hotkey("command", "v")
        else:
            pyautogui.hotkey("ctrl", "v")
        return True
    except Exception as e:
        print(f"pyautogui error: {e}", file=sys.stderr)
        return False


def _move_to_end_wtype():
    """Move cursor to end using Ctrl+End with wtype (Wayland)."""
    try:
        # wtype -M ctrl -P End -p End -m ctrl
        subprocess.run(
            ["wtype", "-M", "ctrl", "-P", "End", "-p", "End", "-m", "ctrl"],
            check=True,
            capture_output=True
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"wtype error moving to end: {e}", file=sys.stderr)
        return False
    except FileNotFoundError:
        return False


def _paste_wtype():
    """Simulate Ctrl+V using wtype (Wayland)."""
    try:
        # wtype -M ctrl -P v -p v -m ctrl
        subprocess.run(
            ["wtype", "-M", "ctrl", "-P", "v", "-p", "v", "-m", "ctrl"],
            check=True,
            capture_output=True
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"wtype error: {e}", file=sys.stderr)
        return False
    except FileNotFoundError:
        return False


def _move_to_end_ydotool():
    """Move cursor to end using Ctrl+End with ydotool (Wayland/X11)."""
    try:
        # ydotool key 29:1 107:1 107:0 29:0  (29=ctrl, 107=End)
        subprocess.run(
            ["ydotool", "key", "29:1", "107:1", "107:0", "29:0"],
            check=True,
            capture_output=True
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"ydotool error moving to end: {e}", file=sys.stderr)
        return False
    except FileNotFoundError:
        return False


def _paste_ydotool():
    """Simulate Ctrl+V using ydotool (Wayland/X11)."""
    try:
        # ydotool key 29:1 47:1 47:0 29:0  (29=ctrl, 47=v)
        subprocess.run(
            ["ydotool", "key", "29:1", "47:1", "47:0", "29:0"],
            check=True,
            capture_output=True
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"ydotool error: {e}", file=sys.stderr)
        return False
    except FileNotFoundError:
        return False


def type_text(text, restore_clipboard=False, move_to_end=True):
    """
    Type text into the currently focused window.

    Args:
        text: The text to type
        restore_clipboard: If True, restore original clipboard after typing
        move_to_end: If True, move cursor to end of text before pasting (default: True)

    Returns:
        True if successful, False otherwise
    """
    if not text:
        return True

    plat, is_wayland = get_platform_info()

    # Save original clipboard if requested (expensive, usually skip)
    original_clipboard = None
    if restore_clipboard:
        try:
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()
            try:
                original_clipboard = root.clipboard_get()
            except tk.TclError:
                original_clipboard = None  # Clipboard was empty
            root.destroy()
        except Exception:
            pass

    # Copy text to clipboard
    if not _copy_to_clipboard(text):
        print("Failed to copy to clipboard", file=sys.stderr)
        return False

    # Small delay for clipboard to be ready
    time.sleep(0.01)

    # Move cursor to end if requested
    if move_to_end:
        if plat == "linux_wayland":
            if shutil.which("wtype"):
                _move_to_end_wtype()
            elif shutil.which("ydotool"):
                _move_to_end_ydotool()
        elif plat == "linux_x11":
            if shutil.which("xdotool"):
                _move_to_end_xdotool()
            else:
                _move_to_end_pyautogui(is_macos=False)
        elif plat == "macos":
            _move_to_end_pyautogui(is_macos=True)
        elif plat == "windows":
            _move_to_end_pyautogui(is_macos=False)

        # Small delay after moving cursor
        time.sleep(0.02)

    # Simulate paste based on platform
    success = False

    if plat == "linux_wayland":
        # Try wtype first, then ydotool
        if shutil.which("wtype"):
            success = _paste_wtype()
        elif shutil.which("ydotool"):
            success = _paste_ydotool()
        else:
            print("Wayland detected but no typing tool available.", file=sys.stderr)
            print("Install wtype: sudo apt install wtype", file=sys.stderr)
            return False

    elif plat == "linux_x11":
        # Try xdotool first (usually available), then pyautogui
        if shutil.which("xdotool"):
            success = _paste_xdotool()
        else:
            success = _paste_pyautogui(is_macos=False)

    elif plat == "macos":
        success = _paste_pyautogui(is_macos=True)

    elif plat == "windows":
        success = _paste_pyautogui(is_macos=False)

    else:
        print(f"Unsupported platform: {plat}", file=sys.stderr)
        return False

    # Restore original clipboard
    if restore_clipboard and original_clipboard is not None:
        try:
            time.sleep(0.05)  # Wait for paste to complete
            _copy_to_clipboard(original_clipboard)
        except Exception:
            pass

    return success


def type_text_direct(text, interval=0.01):
    """
    Type text character by character (only works on X11/Windows/macOS).

    This is slower but doesn't use the clipboard.
    Does NOT work on Wayland.

    Args:
        text: The text to type
        interval: Delay between keystrokes in seconds
    """
    plat, is_wayland = get_platform_info()

    if is_wayland:
        print("Direct typing not supported on Wayland. Use type_text() instead.", file=sys.stderr)
        return False

    # Try xdotool first on Linux
    if plat == "linux_x11" and shutil.which("xdotool"):
        try:
            subprocess.run(
                ["xdotool", "type", "--clearmodifiers", "--delay", str(int(interval * 1000)), text],
                check=True,
                capture_output=True
            )
            return True
        except subprocess.CalledProcessError as e:
            print(f"xdotool type error: {e}", file=sys.stderr)

    # Fallback to pyautogui
    try:
        import pyautogui
        pyautogui.write(text, interval=interval)
        return True
    except Exception as e:
        print(f"Direct typing error: {e}", file=sys.stderr)
        return False


# CLI for testing
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Cross-platform typing utility")
    parser.add_argument("--check", action="store_true", help="Check available backends")
    parser.add_argument("--test", type=str, help="Type test text after 3 second delay")
    args = parser.parse_args()

    if args.check:
        info = check_dependencies()
        print(f"Platform: {info['platform']}")
        print(f"Wayland: {info['is_wayland']}")
        print(f"Available backends: {', '.join(info['available']) or 'None'}")
        print(f"Missing: {', '.join(info['missing']) or 'None'}")
        print(f"Can type: {'Yes' if info['can_type'] else 'No'}")

        if not info['can_type']:
            print("\nTo enable typing:")
            if info['platform'] == "linux_wayland":
                print("  Install wtype: sudo apt install wtype")
                print("  Or ydotool:    sudo apt install ydotool")
            elif info['platform'] == "linux_x11":
                print("  Install xdotool: sudo apt install xdotool")
                print("  Or pyautogui:    pip install pyautogui")
            else:
                print("  pip install pyautogui")

    elif args.test:
        print(f"Will type '{args.test}' in 3 seconds...")
        print("Click on the window where you want the text to appear!")
        time.sleep(3)

        if type_text(args.test):
            print("Success!")
        else:
            print("Failed to type text.")

    else:
        parser.print_help()

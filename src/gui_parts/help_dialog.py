import tkinter as tk
import tkinter.ttk as ttk

# Model VRAM estimates (based on faster-whisper benchmarks)
MODEL_VRAM = {
    "tiny": "~1 GB VRAM",
    "base": "~1.5 GB VRAM",
    "small": "~2 GB VRAM",
    "medium": "~3 GB VRAM",
    "large-v1": "~4.5 GB VRAM (fp16) / ~3 GB (int8)",
    "large-v2": "~4.5 GB VRAM (fp16) / ~3 GB (int8)",
    "large-v3": "~4.5 GB VRAM (fp16) / ~3 GB (int8)",
    "large": "~4.5 GB VRAM (fp16) / ~3 GB (int8)",
}

class HelpDialog:
    """Help dialog with detailed information."""

    # Track open dialogs for toggle behavior
    _open_dialogs = {}

    # Compact help text for each section
    HELP_TEXT = {
        "model": """Model: Whisper model size (tiny→large-v3, larger=more accurate)

VAD: Voice Activity Detection (filters silence/noise)

¶: Adaptive paragraph detection (auto line breaks by pauses)

⌨: Auto-type mode selector
  • Off - No auto-typing
  • Whisper - Type raw transcription immediately
  • Translation - Type Google Translate output (1-2 sec delay)
  • AI - Type AI-processed output (longer delay based on trigger)

Dev: Inference device (cuda=GPU, cpu=CPU, auto=best)

Mem: Context segments 1-10 (higher=better context, slower)

Pat: Patience seconds (wait time before finalizing segment)

Time: Translation timeout seconds""",

        "translate": """Source: Source language (auto=detect, or select specific)

Target: Target language (none=disabled, or select for Google Translate)

Note: AI Processing overrides Google Translate when enabled.""",

        "ai": """Enable AI: Intelligent proofreading and translation

Mode: Proofread | Translate | Proofread+Translate

Model: AI model selection (larger=more capable, higher cost)

Trigger: Time (every N min) | Words (every N words)

Setup: Add OPENROUTER_API_KEY to .env
See AI_SETUP.md for details.""",

        "tts": """Enable TTS: Convert text to speech

Voice: Browse=upload ref audio for cloning | Clear=default

Save File: Auto-save to tts_output/ with timestamp

Format: WAV (lossless) | OGG (compressed)

Setup: See INSTALL_TTS.md"""
    }

    @staticmethod
    def show(parent, section):
        """Show help dialog for a section with toggle behavior."""
        if section not in HelpDialog.HELP_TEXT:
            return

        # Toggle: if dialog is already open for this section, close it
        if section in HelpDialog._open_dialogs:
            try:
                HelpDialog._open_dialogs[section].destroy()
                del HelpDialog._open_dialogs[section]
            except:
                pass
            return

        # Create new dialog window
        dialog = tk.Toplevel(parent)
        dialog.title(f"Help - {section.title()}")
        dialog.geometry("450x280")
        dialog.resizable(False, False)

        # Create text widget with scrollbar
        text_frame = ttk.Frame(dialog)
        text_frame.pack(fill="both", expand=True, padx=10, pady=10)

        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side="right", fill="y")

        text_widget = tk.Text(text_frame, wrap="word", font=('TkDefaultFont', 9),
                             yscrollcommand=scrollbar.set, padx=8, pady=8)
        text_widget.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=text_widget.yview)

        # Insert help text
        text_widget.insert("1.0", HelpDialog.HELP_TEXT[section])
        text_widget.config(state="disabled")  # Read-only

        # Track dialog
        HelpDialog._open_dialogs[section] = dialog

        # Click outside to close functionality
        def on_focus_out(event):
            # Close dialog when clicking outside
            try:
                if dialog.winfo_exists():
                    dialog.destroy()
                    if section in HelpDialog._open_dialogs:
                        del HelpDialog._open_dialogs[section]
            except:
                pass

        # Cleanup on close
        def on_close():
            try:
                if section in HelpDialog._open_dialogs:
                    del HelpDialog._open_dialogs[section]
                dialog.destroy()
            except:
                pass

        dialog.protocol("WM_DELETE_WINDOW", on_close)

        # Bind focus out after a delay (to avoid immediate close on creation)
        dialog.after(200, lambda: dialog.bind("<FocusOut>", on_focus_out))

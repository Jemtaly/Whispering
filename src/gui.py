#!/usr/bin/env python3


import threading
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import filedialog, messagebox

import core
from cmque import PairDeque, Queue
from settings import Settings


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


class Text(tk.Text):
    def __init__(self, master, on_new_text=None, on_text_changed=None):
        super().__init__(master)
        self.res_queue = Queue(PairDeque())
        self.on_new_text = on_new_text  # Callback for NEW text only
        self.on_text_changed = on_text_changed  # Callback when any text changes
        self.tag_config("done", foreground="black")
        self.tag_config("curr", foreground="blue", underline=True)
        self.insert("end", "  ", "done")
        self.record = self.index("end-1c")
        self.prev_done = ""  # Track what we've already processed
        self.see("end")
        # Keep text editable! No state="disabled"
        self.poll()

    def poll(self):
        text_changed = False
        while self.res_queue:
            if res := self.res_queue.get():
                done, curr = res
                # Calculate NEW text (what we haven't processed yet)
                new_text = ""
                if len(done) > len(self.prev_done):
                    new_text = done[len(self.prev_done):]
                self.prev_done = done

                # Update display
                self.delete(self.record, "end")
                self.insert("end", done, "done")
                self.record = self.index("end-1c")
                self.insert("end", curr, "curr")
                self.see("end")
                text_changed = True

                # Fire callback with only NEW text
                if new_text and self.on_new_text:
                    self.on_new_text(new_text)
            else:
                # Stop signal - finalize current line
                done = self.get(self.record, "end-1c")
                self.delete(self.record, "end")
                self.insert("end", done, "done")
                self.insert("end", "\n", "done")
                self.insert("end", "  ", "done")
                self.record = self.index("end-1c")
                self.prev_done = ""  # Reset for next segment
                self.see("end")
                text_changed = True

        # Fire text changed callback if text was modified
        if text_changed and self.on_text_changed:
            self.on_text_changed()

        self.after(100, self.poll)

    def clear(self):
        """Clear all text and reset state."""
        self.delete("1.0", "end")
        self.insert("end", "  ", "done")
        self.record = self.index("end-1c")
        self.prev_done = ""
        # Fire text changed callback after clearing
        if self.on_text_changed:
            self.on_text_changed()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Whispering")
        self.autotype_mode_active = "Off"  # Track autotype mode: Off, Whisper, Translation, AI

        # Load settings first
        self.settings = Settings()

        # Load text visibility state from settings (default: True)
        self.text_visible = self.settings.get("text_visible", True)

        # Flag to track if we're shutting down (prevent TTS crashes)
        self.is_shutting_down = False

        # Set minimum window size - will adjust based on mode
        # For minimal mode: calculate based on controls, for full mode add space for text
        # Minimal mode: 400x850 minimum (never go below this)
        # Full mode: 900x850 gives space for text panels
        if self.text_visible:
            self.minsize(900, 850)  # Full mode - more vertical space for text
        else:
            self.minsize(400, 850)  # Minimal mode - never below 400x850

        # Try to load AI configuration
        self.ai_config = None
        self.ai_available = False
        try:
            from ai_config import load_ai_config
            self.ai_config = load_ai_config()
            self.ai_available = self.ai_config is not None
        except Exception as e:
            print(f"AI features not available: {e}")

        # Try to initialize TTS
        self.tts_controller = None
        self.tts_available = False
        try:
            from tts_controller import TTSController
            self.tts_controller = TTSController(device="auto", output_dir="tts_output")
            self.tts_controller.on_progress = self.on_tts_progress
            self.tts_controller.on_complete = self.on_tts_complete
            self.tts_controller.on_error = self.on_tts_error
            self.tts_available = True
        except Exception as e:
            print(f"TTS features not available: {e}")

        # Create frames - two column layout
        self.controls_frame = ttk.Frame(self, padding="5")

        # Text frame with labels
        self.text_frame = ttk.Frame(self)

        # Whisper output (top) - header frame with label and count
        ts_header = ttk.Frame(self.text_frame)
        ts_header.grid(row=0, column=0, sticky="ew", padx=5, pady=(0, 2))
        ts_label = ttk.Label(ts_header, text="Whisper Output", font=('TkDefaultFont', 9, 'bold'))
        ts_label.pack(side="left")
        self.ts_count_label = ttk.Label(ts_header, text="0 chars, 0 words", font=('TkDefaultFont', 8), foreground="gray")
        self.ts_count_label.pack(side="right")

        self.ts_text = Text(self.text_frame, on_new_text=self.on_new_transcription, on_text_changed=self.update_ts_count)
        self.ts_text.grid(row=1, column=0, sticky="nsew")

        # Proofread output (middle) - header frame with label and count
        pr_header = ttk.Frame(self.text_frame)
        pr_header.grid(row=2, column=0, sticky="ew", padx=5, pady=(5, 2))
        pr_label = ttk.Label(pr_header, text="Proofread Output", font=('TkDefaultFont', 9, 'bold'))
        pr_label.pack(side="left")
        self.pr_count_label = ttk.Label(pr_header, text="0 chars, 0 words", font=('TkDefaultFont', 8), foreground="gray")
        self.pr_count_label.pack(side="right")

        self.pr_text = Text(self.text_frame, on_new_text=self.on_new_proofread, on_text_changed=self.update_pr_count)
        self.pr_text.grid(row=3, column=0, sticky="nsew")

        # Hide proofread window by default (only show when AI proofread+translate is active)
        pr_header.grid_remove()
        self.pr_text.grid_remove()

        # Translation output (bottom) - header frame with label and count
        tl_header = ttk.Frame(self.text_frame)
        tl_header.grid(row=4, column=0, sticky="ew", padx=5, pady=(5, 2))
        tl_label = ttk.Label(tl_header, text="Translation Output", font=('TkDefaultFont', 9, 'bold'))
        tl_label.pack(side="left")
        self.tl_count_label = ttk.Label(tl_header, text="0 chars, 0 words", font=('TkDefaultFont', 8), foreground="gray")
        self.tl_count_label.pack(side="right")

        self.tl_text = Text(self.text_frame, on_new_text=self.on_new_translation, on_text_changed=self.update_tl_count)
        self.tl_text.grid(row=5, column=0, sticky="nsew")

        # Store references to show/hide proofread window dynamically
        self.pr_header = pr_header

        # Configure text_frame grid
        self.text_frame.columnconfigure(0, weight=1)
        self.text_frame.rowconfigure(1, weight=1)  # Whisper
        self.text_frame.rowconfigure(3, weight=1)  # Proofread
        self.text_frame.rowconfigure(5, weight=1)  # Translation

        # Grid layout: controls in column 0, text frame in column 1
        self.controls_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        self.text_frame.grid(row=0, column=1, sticky="nsew")

        # Configure grid weights
        self.columnconfigure(0, weight=0, minsize=350)  # Controls column - fixed width
        self.columnconfigure(1, weight=1)  # Text column - expandable
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # Row counter for controls_frame
        row = 0

        # === MIC SECTION ===
        mic_frame = ttk.Frame(self.controls_frame)
        mic_frame.grid(row=row, column=0, sticky="ew", pady=(0, 5))
        row += 1

        ttk.Label(mic_frame, text="Mic:").pack(side="left", padx=(0, 5))
        self.mic_list = core.get_mic_names()
        mic_display = ["(system default)"] + [name for idx, name in self.mic_list]
        self.mic_combo = ttk.Combobox(mic_frame, values=mic_display, state="readonly", width=25)
        self.mic_combo.current(0)
        self.mic_combo.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.mic_button = ttk.Button(mic_frame, text="↻", width=2, command=self.refresh_mics)
        self.mic_button.pack(side="left")

        # === TOGGLE BUTTON ===
        self.hide_text_button = ttk.Button(self.controls_frame, text="Hide Text ◀", command=self.toggle_text_display)
        self.hide_text_button.grid(row=row, column=0, sticky="ew", pady=(0, 10))
        row += 1

        # === MODEL SECTION ===
        ttk.Separator(self.controls_frame, orient="horizontal").grid(row=row, column=0, sticky="ew", pady=(0, 5))
        row += 1

        # Section header with help button
        model_header = ttk.Frame(self.controls_frame)
        model_header.grid(row=row, column=0, sticky="ew", pady=(0, 3))
        ttk.Label(model_header, text="Model Settings", font=('TkDefaultFont', 9, 'bold')).pack(side="left")
        help_btn = ttk.Button(model_header, text="?", width=2, command=lambda: HelpDialog.show(self, "model"))
        help_btn.pack(side="right")
        row += 1

        model_frame = ttk.Frame(self.controls_frame)
        model_frame.grid(row=row, column=0, sticky="ew", pady=(0, 3))
        row += 1

        ttk.Label(model_frame, text="Model:").pack(side="left", padx=(0, 5))
        self.model_combo = ttk.Combobox(model_frame, values=core.models, state="normal", width=15)
        self.model_combo.set("large-v3")
        self.model_combo.pack(side="left", fill="x", expand=True)
        self.model_combo.bind("<<ComboboxSelected>>", self.on_model_changed)

        # VRAM info label
        self.vram_label = ttk.Label(self.controls_frame, text=MODEL_VRAM.get("large-v3", ""),
                                     foreground="gray", font=('TkDefaultFont', 8))
        self.vram_label.grid(row=row, column=0, sticky="w", pady=(0, 5))
        row += 1

        # VAD, ¶, ⌨, Device grouped
        options_frame = ttk.Frame(self.controls_frame)
        options_frame.grid(row=row, column=0, sticky="ew", pady=(0, 5))
        row += 1

        self.vad_check = ttk.Checkbutton(options_frame, text="VAD", onvalue=True, offvalue=False)
        self.vad_check.state(("!alternate", "selected"))
        self.vad_check.pack(side="left", padx=(0, 8))

        self.para_check = ttk.Checkbutton(options_frame, text="¶", onvalue=True, offvalue=False)
        self.para_check.state(("!alternate", "selected"))
        self.para_check.pack(side="left", padx=(0, 8))

        ttk.Label(options_frame, text="⌨:").pack(side="left", padx=(0, 2))
        self.autotype_mode = ttk.Combobox(options_frame, values=["Off", "Whisper", "Translation", "AI"],
                                          state="readonly", width=10)
        self.autotype_mode.current(0)  # Default to "Off"
        self.autotype_mode.pack(side="left", padx=(0, 8))

        ttk.Label(options_frame, text="Dev:").pack(side="left", padx=(0, 2))
        self.device_combo = ttk.Combobox(options_frame, values=core.devices, state="readonly", width=6)
        self.device_combo.current(1)
        self.device_combo.pack(side="left")

        # === MEMORY, PATIENCE, TIMEOUT ===
        params_frame = ttk.Frame(self.controls_frame)
        params_frame.grid(row=row, column=0, sticky="ew", pady=(0, 5))
        row += 1

        ttk.Label(params_frame, text="Mem:").pack(side="left", padx=(0, 2))
        self.memory_spin = ttk.Spinbox(params_frame, from_=1, to=10, increment=1, state="readonly", width=4)
        self.memory_spin.set(3)
        self.memory_spin.pack(side="left", padx=(0, 8))

        ttk.Label(params_frame, text="Pat:").pack(side="left", padx=(0, 2))
        self.patience_spin = ttk.Spinbox(params_frame, from_=1.0, to=20.0, increment=0.5, state="readonly", width=4)
        self.patience_spin.set(5.0)
        self.patience_spin.pack(side="left", padx=(0, 8))

        ttk.Label(params_frame, text="Time:").pack(side="left", padx=(0, 2))
        self.timeout_spin = ttk.Spinbox(params_frame, from_=1.0, to=20.0, increment=0.5, state="readonly", width=4)
        self.timeout_spin.set(5.0)
        self.timeout_spin.pack(side="left")

        # Whisper output Copy/Cut buttons with count
        whisper_buttons_frame = ttk.Frame(self.controls_frame)
        whisper_buttons_frame.grid(row=row, column=0, sticky="ew", pady=(5, 0))
        row += 1

        ttk.Button(whisper_buttons_frame, text="Copy Whisper", command=self.copy_whisper_text, width=15).pack(side="left", padx=(0, 5))
        ttk.Button(whisper_buttons_frame, text="Cut Whisper", command=self.cut_whisper_text, width=15).pack(side="left", padx=(0, 5))
        self.whisper_count_button = ttk.Label(whisper_buttons_frame, text="0c, 0w", foreground="blue", font=('TkDefaultFont', 8))
        self.whisper_count_button.pack(side="left")

        # === TRANSLATE/PROOFREAD SECTION ===
        ttk.Separator(self.controls_frame, orient="horizontal").grid(row=row, column=0, sticky="ew", pady=(5, 5))
        row += 1

        # Section header with help button
        translate_header = ttk.Frame(self.controls_frame)
        translate_header.grid(row=row, column=0, sticky="ew", pady=(0, 3))
        ttk.Label(translate_header, text="Translation", font=('TkDefaultFont', 9, 'bold')).pack(side="left")
        help_btn = ttk.Button(translate_header, text="?", width=2, command=lambda: HelpDialog.show(self, "translate"))
        help_btn.pack(side="right")
        row += 1

        lang_frame = ttk.Frame(self.controls_frame)
        lang_frame.grid(row=row, column=0, sticky="ew", pady=(0, 5))
        row += 1

        ttk.Label(lang_frame, text="Source:").pack(side="left", padx=(0, 2))
        self.source_combo = ttk.Combobox(lang_frame, values=["auto"] + core.sources, state="readonly", width=5)
        self.source_combo.current(0)
        self.source_combo.pack(side="left", padx=(0, 10))

        ttk.Label(lang_frame, text="Target:").pack(side="left", padx=(0, 2))
        self.target_combo = ttk.Combobox(lang_frame, values=["none"] + core.targets, state="readonly", width=5)
        self.target_combo.current(0)
        self.target_combo.bind("<<ComboboxSelected>>", self.on_target_changed)
        self.target_combo.pack(side="left")

        # Translation output Copy/Cut buttons with count
        translation_buttons_frame = ttk.Frame(self.controls_frame)
        translation_buttons_frame.grid(row=row, column=0, sticky="ew", pady=(0, 10))
        row += 1

        ttk.Button(translation_buttons_frame, text="Copy Translation", command=self.copy_translation_text, width=15).pack(side="left", padx=(0, 5))
        ttk.Button(translation_buttons_frame, text="Cut Translation", command=self.cut_translation_text, width=15).pack(side="left", padx=(0, 5))
        self.translation_count_button = ttk.Label(translation_buttons_frame, text="0c, 0w", foreground="blue", font=('TkDefaultFont', 8))
        self.translation_count_button.pack(side="left")

        # === AI SECTION ===
        ttk.Separator(self.controls_frame, orient="horizontal").grid(row=row, column=0, sticky="ew", pady=(0, 5))
        row += 1

        # Section header with help button
        ai_header = ttk.Frame(self.controls_frame)
        ai_header.grid(row=row, column=0, sticky="ew", pady=(0, 3))
        ttk.Label(ai_header, text="AI Processing", font=('TkDefaultFont', 9, 'bold')).pack(side="left")
        if self.ai_available:
            help_btn = ttk.Button(ai_header, text="?", width=2, command=lambda: HelpDialog.show(self, "ai"))
            help_btn.pack(side="right")
        row += 1

        ai_enable_frame = ttk.Frame(self.controls_frame)
        ai_enable_frame.grid(row=row, column=0, sticky="ew", pady=(0, 5))
        row += 1

        self.ai_check = ttk.Checkbutton(ai_enable_frame, text="Enable AI", onvalue=True, offvalue=False)
        if self.ai_available:
            self.ai_check.state(("!alternate",))
        else:
            self.ai_check.state(("disabled",))
        self.ai_check.pack(side="left", padx=(0, 5))

        # AI Mode
        ai_mode_frame = ttk.Frame(self.controls_frame)
        ai_mode_frame.grid(row=row, column=0, sticky="ew", pady=(0, 5))
        row += 1

        ttk.Label(ai_mode_frame, text="Mode:").pack(side="left", padx=(0, 2))
        self.ai_mode_combo = ttk.Combobox(ai_mode_frame, values=["Proofread", "Translate", "Proofread+Translate"], state="readonly", width=18)
        self.ai_mode_combo.current(0)
        if not self.ai_available:
            self.ai_mode_combo.state(("disabled",))
        self.ai_mode_combo.pack(side="left", fill="x", expand=True)
        self.ai_mode_combo.bind("<<ComboboxSelected>>", self.on_ai_mode_changed)

        # AI Model
        ai_model_frame = ttk.Frame(self.controls_frame)
        ai_model_frame.grid(row=row, column=0, sticky="ew", pady=(0, 5))
        row += 1

        ttk.Label(ai_model_frame, text="Model:").pack(side="left", padx=(0, 2))
        if self.ai_available:
            model_names = [m['name'] for m in self.ai_config.get_models()]
            default_model_id = self.ai_config.get_default_model()
            default_idx = 0
            for i, m in enumerate(self.ai_config.get_models()):
                if m['id'] == default_model_id:
                    default_idx = i
                    break
        else:
            model_names = []
            default_idx = 0

        self.ai_model_combo = ttk.Combobox(ai_model_frame, values=model_names, state="readonly", width=15)
        if model_names:
            self.ai_model_combo.current(default_idx)
        if not self.ai_available:
            self.ai_model_combo.state(("disabled",))
        self.ai_model_combo.pack(side="left", fill="x", expand=True)

        # AI Trigger
        ai_trigger_frame = ttk.Frame(self.controls_frame)
        ai_trigger_frame.grid(row=row, column=0, sticky="ew", pady=(0, 5))
        row += 1

        ttk.Label(ai_trigger_frame, text="Trigger:").pack(side="left", padx=(0, 2))
        self.ai_trigger_combo = ttk.Combobox(ai_trigger_frame, values=["Time", "Words"], state="readonly", width=7)
        self.ai_trigger_combo.current(0)
        self.ai_trigger_combo.bind("<<ComboboxSelected>>", self.on_trigger_changed)
        if not self.ai_available:
            self.ai_trigger_combo.state(("disabled",))
        self.ai_trigger_combo.pack(side="left")

        # AI Interval/Words (same row, toggled)
        self.ai_interval_label = ttk.Label(ai_trigger_frame, text=" min:")
        self.ai_interval_label.pack(side="left", padx=(5, 2))
        interval_values = [str(i) for i in range(1, 11)]
        self.ai_interval_combo = ttk.Combobox(ai_trigger_frame, values=interval_values, state="readonly", width=5)
        self.ai_interval_combo.current(0)  # Default to 1 minute
        if not self.ai_available:
            self.ai_interval_combo.state(("disabled",))
        self.ai_interval_combo.pack(side="left")

        self.ai_words_label = ttk.Label(ai_trigger_frame, text=" words:")
        self.ai_words_spin = ttk.Spinbox(ai_trigger_frame, from_=50, to=500, increment=50, state="readonly", width=5)
        self.ai_words_spin.set(150)
        if not self.ai_available:
            self.ai_words_spin.state(("disabled",))

        # AI Proofread output Copy/Cut buttons with count
        ai_proofread_buttons_frame = ttk.Frame(self.controls_frame)
        ai_proofread_buttons_frame.grid(row=row, column=0, sticky="ew", pady=(5, 5))
        row += 1

        ttk.Button(ai_proofread_buttons_frame, text="Copy Proofread", command=self.copy_proofread_text, width=15).pack(side="left", padx=(0, 5))
        ttk.Button(ai_proofread_buttons_frame, text="Cut Proofread", command=self.cut_proofread_text, width=15).pack(side="left", padx=(0, 5))
        self.proofread_count_button = ttk.Label(ai_proofread_buttons_frame, text="0c, 0w", foreground="blue", font=('TkDefaultFont', 8))
        self.proofread_count_button.pack(side="left")

        # Store ref to show/hide when needed
        self.ai_proofread_buttons_frame = ai_proofread_buttons_frame
        # Hide by default (only show when AI proofread or proofread+translate is active)
        ai_proofread_buttons_frame.grid_remove()

        # === PROMPT ===
        prompt_frame = ttk.Frame(self.controls_frame)
        prompt_frame.grid(row=row, column=0, sticky="ew", pady=(0, 5))
        row += 1

        ttk.Label(prompt_frame, text="Prompt:").pack(side="top", anchor="w", pady=(0, 2))
        self.prompt_entry = ttk.Entry(prompt_frame, state="normal")
        self.prompt_entry.pack(side="top", fill="x")

        # === TTS SECTION ===
        ttk.Separator(self.controls_frame, orient="horizontal").grid(row=row, column=0, sticky="ew", pady=(10, 5))
        row += 1

        # Section header with help button
        tts_header = ttk.Frame(self.controls_frame)
        tts_header.grid(row=row, column=0, sticky="ew", pady=(0, 3))
        ttk.Label(tts_header, text="Text-to-Speech", font=('TkDefaultFont', 9, 'bold')).pack(side="left")
        if self.tts_available:
            help_btn = ttk.Button(tts_header, text="?", width=2, command=lambda: HelpDialog.show(self, "tts"))
            help_btn.pack(side="right")
        row += 1

        tts_enable_frame = ttk.Frame(self.controls_frame)
        tts_enable_frame.grid(row=row, column=0, sticky="ew", pady=(0, 5))
        row += 1

        self.tts_check = ttk.Checkbutton(tts_enable_frame, text="Enable TTS", onvalue=True, offvalue=False)
        if self.tts_available:
            self.tts_check.state(("!alternate",))
        else:
            self.tts_check.state(("disabled",))
        self.tts_check.pack(side="left", padx=(0, 5))

        # Voice reference
        tts_voice_frame = ttk.Frame(self.controls_frame)
        tts_voice_frame.grid(row=row, column=0, sticky="ew", pady=(0, 5))
        row += 1

        ttk.Label(tts_voice_frame, text="Voice:").pack(side="left", padx=(0, 2))
        self.tts_voice_label = ttk.Label(tts_voice_frame, text="Default", foreground="gray", width=15, anchor="w")
        self.tts_voice_label.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.tts_browse_button = ttk.Button(tts_voice_frame, text="Browse", width=8, command=self.browse_voice)
        if not self.tts_available:
            self.tts_browse_button.state(("disabled",))
        self.tts_browse_button.pack(side="left", padx=(0, 5))

        self.tts_clear_button = ttk.Button(tts_voice_frame, text="Clear", width=6, command=self.clear_voice)
        if not self.tts_available:
            self.tts_clear_button.state(("disabled",))
        self.tts_clear_button.pack(side="left")

        # File output options
        tts_output_frame = ttk.Frame(self.controls_frame)
        tts_output_frame.grid(row=row, column=0, sticky="ew", pady=(0, 5))
        row += 1

        ttk.Label(tts_output_frame, text="Output:").pack(side="left", padx=(0, 2))
        self.tts_save_check = ttk.Checkbutton(tts_output_frame, text="Save to file", onvalue=True, offvalue=False)
        if self.tts_available:
            self.tts_save_check.state(("!alternate",))
        else:
            self.tts_save_check.state(("disabled",))
        self.tts_save_check.pack(side="left", padx=(0, 10))

        self.tts_format_combo = ttk.Combobox(tts_output_frame, values=["wav", "ogg"], state="readonly", width=5)
        self.tts_format_combo.current(0)
        if not self.tts_available:
            self.tts_format_combo.state(("disabled",))
        self.tts_format_combo.pack(side="left")

        # TTS status
        self.tts_status_label = ttk.Label(self.controls_frame, text="", foreground="blue",
                                         wraplength=330, font=('TkDefaultFont', 8))
        self.tts_status_label.grid(row=row, column=0, sticky="ew", pady=(0, 5))
        row += 1

        # === CONTROL BUTTON & LEVEL ===
        control_frame = ttk.Frame(self.controls_frame)
        control_frame.grid(row=row, column=0, sticky="ew", pady=(0, 5))
        row += 1

        self.control_button = ttk.Button(control_frame, text="Start", command=self.start, state="normal")
        self.control_button.pack(side="top", fill="x", pady=(0, 5))

        level_frame = ttk.Frame(control_frame)
        level_frame.pack(side="top", fill="x")
        ttk.Label(level_frame, text="Level:").pack(side="left", padx=(0, 5))
        self.level_bar = ttk.Progressbar(level_frame, length=100, mode='determinate', maximum=100)
        self.level_bar.pack(side="left", fill="x", expand=True)

        # === STATUS ===
        self.status_label = ttk.Label(self.controls_frame, text="", foreground="red", wraplength=330)
        self.status_label.grid(row=row, column=0, sticky="ew")
        row += 1

        # State variables
        self.ready = [None]
        self.error = [None]
        self.level = [0]
        self.autotype_error_shown = False

        # TTS session tracking
        self.tts_session_text = ""  # Accumulate text for TTS
        self.tts_session_id = None  # Current session ID

        # Apply loaded text visibility state
        if not self.text_visible:
            # Hide text frame and update button for minimal mode
            self.text_frame.grid_remove()
            self.hide_text_button.config(text="Show Text ▶")

        # Load and apply TTS settings
        if self.tts_available:
            tts_enabled = self.settings.get("tts_enabled", False)
            tts_save_file = self.settings.get("tts_save_file", False)

            if tts_enabled:
                self.tts_check.state(("selected",))
            if tts_save_file:
                self.tts_save_check.state(("selected",))

        # Load and apply AI settings
        if self.ai_available:
            ai_enabled = self.settings.get("ai_enabled", False)
            if ai_enabled:
                self.ai_check.state(("selected",))

        # Save settings on window close
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_new_transcription(self, text):
        """Called when NEW transcription text arrives. Auto-types if enabled."""
        # Accumulate for TTS (capture ALL speech, not just proofread)
        if self.tts_available and "selected" in self.tts_check.state():
            self.tts_session_text += text + " "

        # Show waiting indicator if we're in Translation or AI mode
        if self.autotype_mode_active == "Translation" and text:
            self.status_label.config(text="⏳ Waiting for translation...", foreground="blue")
        elif self.autotype_mode_active == "AI" and text:
            self.status_label.config(text="⏳ Waiting for AI processing...", foreground="blue")

        # Auto-type Whisper output if that mode is selected
        if self.autotype_mode_active == "Whisper" and text:
            try:
                import autotype
                # Type immediately in a thread
                def do_type():
                    if not autotype.type_text(text, restore_clipboard=False):
                        if not self.autotype_error_shown:
                            self.autotype_error_shown = True
                            # Show error in status (thread-safe via after)
                            self.after(0, lambda: self.status_label.config(
                                text="Auto-type failed. Run: python autotype.py --check"))
                threading.Thread(target=do_type, daemon=True).start()
            except ImportError:
                if not self.autotype_error_shown:
                    self.autotype_error_shown = True
                    self.status_label.config(text="autotype.py not found")

    def on_new_translation(self, text):
        """Called when NEW translated/proofread text arrives. Auto-types if Translation or AI mode selected."""
        # Auto-type Translation or AI output if those modes are selected
        if self.autotype_mode_active in ("Translation", "AI") and text:
            # Clear waiting message and show auto-typing indicator
            mode_name = "translation" if self.autotype_mode_active == "Translation" else "AI output"
            self.status_label.config(text=f"⌨ Auto-typing {mode_name}...", foreground="green")

            try:
                import autotype
                # Type immediately in a thread
                def do_type():
                    if not autotype.type_text(text, restore_clipboard=False):
                        if not self.autotype_error_shown:
                            self.autotype_error_shown = True
                            # Show error in status (thread-safe via after)
                            self.after(0, lambda: self.status_label.config(
                                text="Auto-type failed. Run: python autotype.py --check"))
                    else:
                        # Success - clear status after a moment
                        self.after(1000, lambda: self.status_label.config(text=""))
                threading.Thread(target=do_type, daemon=True).start()
            except ImportError:
                if not self.autotype_error_shown:
                    self.autotype_error_shown = True
                    self.status_label.config(text="autotype.py not found")

    def update_ts_count(self):
        """Update character and word count for Whisper output."""
        text = self.ts_text.get("1.0", "end-1c").strip()
        char_count = len(text)
        word_count = len(text.split()) if text else 0
        self.ts_count_label.config(text=f"{char_count} chars, {word_count} words")
        # Update control panel button count (blue)
        self.whisper_count_button.config(text=f"{char_count}c, {word_count}w")

    def update_pr_count(self):
        """Update character and word count for Proofread output."""
        text = self.pr_text.get("1.0", "end-1c").strip()
        char_count = len(text)
        word_count = len(text.split()) if text else 0
        self.pr_count_label.config(text=f"{char_count} chars, {word_count} words")
        # Update control panel button count (blue)
        self.proofread_count_button.config(text=f"{char_count}c, {word_count}w")

    def update_tl_count(self):
        """Update character and word count for Translation output."""
        text = self.tl_text.get("1.0", "end-1c").strip()
        char_count = len(text)
        word_count = len(text.split()) if text else 0
        self.tl_count_label.config(text=f"{char_count} chars, {word_count} words")
        # Update control panel button count (blue)
        self.translation_count_button.config(text=f"{char_count}c, {word_count}w")

    def on_new_proofread(self, text):
        """Called when NEW proofread text arrives. Auto-types if AI mode selected."""
        # Auto-type proofread output if AI mode is selected
        if self.autotype_mode_active == "AI" and text:
            # Clear waiting message and show auto-typing indicator
            self.status_label.config(text="⌨ Auto-typing AI proofread...", foreground="green")

            try:
                import autotype
                # Type immediately in a thread
                def do_type():
                    if not autotype.type_text(text, restore_clipboard=False):
                        if not self.autotype_error_shown:
                            self.autotype_error_shown = True
                            self.after(0, lambda: self.status_label.config(
                                text="Auto-type failed. Run: python autotype.py --check"))
                    else:
                        # Success - clear status after a moment
                        self.after(1000, lambda: self.status_label.config(text=""))
                threading.Thread(target=do_type, daemon=True).start()
            except ImportError:
                if not self.autotype_error_shown:
                    self.autotype_error_shown = True
                    self.status_label.config(text="autotype.py not found")

    def copy_whisper_text(self):
        """Copy Whisper output text to clipboard."""
        text = self.ts_text.get("1.0", "end-1c").strip()
        if text:
            self._copy_to_clipboard(text)
            self.status_label.config(text="✓ Copied Whisper text to clipboard", foreground="green")
        else:
            self.status_label.config(text="No text to copy", foreground="orange")

    def cut_whisper_text(self):
        """Cut Whisper output text (copy and clear)."""
        text = self.ts_text.get("1.0", "end-1c").strip()
        if text:
            self._copy_to_clipboard(text)
            self.ts_text.clear()
            self.status_label.config(text="✓ Cut Whisper text to clipboard", foreground="green")
        else:
            self.status_label.config(text="No text to cut", foreground="orange")

    def copy_proofread_text(self):
        """Copy Proofread output text to clipboard."""
        text = self.pr_text.get("1.0", "end-1c").strip()
        if text:
            self._copy_to_clipboard(text)
            self.status_label.config(text="✓ Copied proofread text to clipboard", foreground="green")
        else:
            self.status_label.config(text="No text to copy", foreground="orange")

    def cut_proofread_text(self):
        """Cut Proofread output text (copy and clear)."""
        text = self.pr_text.get("1.0", "end-1c").strip()
        if text:
            self._copy_to_clipboard(text)
            self.pr_text.clear()
            self.status_label.config(text="✓ Cut proofread text to clipboard", foreground="green")
        else:
            self.status_label.config(text="No text to cut", foreground="orange")

    def copy_translation_text(self):
        """Copy Translation output text to clipboard."""
        text = self.tl_text.get("1.0", "end-1c").strip()
        if text:
            self._copy_to_clipboard(text)
            self.status_label.config(text="✓ Copied translation to clipboard", foreground="green")
        else:
            self.status_label.config(text="No text to copy", foreground="orange")

    def cut_translation_text(self):
        """Cut Translation/Proofread output text (copy and clear)."""
        text = self.tl_text.get("1.0", "end-1c").strip()
        if text:
            self._copy_to_clipboard(text)
            self.tl_text.clear()
            self.status_label.config(text="✓ Cut translation to clipboard", foreground="green")
        else:
            self.status_label.config(text="No text to cut", foreground="orange")

    def _copy_to_clipboard(self, text):
        """Copy text to system clipboard using tkinter."""
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.update()  # Required for clipboard to persist
            return True
        except Exception as e:
            self.status_label.config(text=f"Clipboard error: {e}", foreground="red")
            return False

    def on_ai_mode_changed(self, event=None):
        """Validate AI mode selection - Proofread+Translate requires target language."""
        mode = self.ai_mode_combo.get()
        if mode == "Proofread+Translate":
            target = self.target_combo.get()
            if target == "none":
                self.status_label.config(
                    text="⚠ Proofread+Translate requires a Target language. Please select one.",
                    foreground="orange"
                )
                # Revert to Proofread mode
                self.ai_mode_combo.current(0)
                return

    def finalize_tts_session(self):
        """Generate TTS audio from accumulated session text."""
        if not self.tts_session_text.strip() or not self.tts_available:
            return

        # Check if we should save to file
        save_to_file = "selected" in self.tts_save_check.state()

        if save_to_file and self.tts_session_id:
            file_format = self.tts_format_combo.get()
            filename = f"tts_session_{self.tts_session_id}"

            # Synthesize accumulated text to single file
            self.tts_controller.synthesize_to_file(
                text=self.tts_session_text.strip(),
                output_filename=filename,
                file_format=file_format,
                async_mode=True
            )

        # Reset session
        self.tts_session_text = ""

    def on_model_changed(self, event=None):
        """Update VRAM label when model changes."""
        model = self.model_combo.get()
        vram_info = MODEL_VRAM.get(model, "")
        self.vram_label.config(text=vram_info)

    def on_target_changed(self, event=None):
        """Update AI mode options based on target language selection."""
        target = self.target_combo.get()

        if target == "none":
            # No translation - only show Proofread option
            self.ai_mode_combo.config(values=["Proofread"])
            self.ai_mode_combo.current(0)
        else:
            # Translation enabled - show all options
            self.ai_mode_combo.config(values=["Proofread", "Translate", "Proofread+Translate"])
            # Default to Proofread+Translate when translation is enabled
            self.ai_mode_combo.current(2)

    def on_trigger_changed(self, event=None):
        """Update visible controls based on trigger mode selection."""
        trigger_mode = self.ai_trigger_combo.get()

        if trigger_mode == "Time":
            # Show time controls, hide word controls
            self.ai_words_label.pack_forget()
            self.ai_words_spin.pack_forget()
            if not self.ai_interval_label.winfo_ismapped():
                self.ai_interval_label.pack(side="left", padx=(5, 2))
                self.ai_interval_combo.pack(side="left")
        else:  # Words
            # Show word controls, hide time controls
            self.ai_interval_label.pack_forget()
            self.ai_interval_combo.pack_forget()
            if not self.ai_words_label.winfo_ismapped():
                self.ai_words_label.pack(side="left", padx=(5, 2))
                self.ai_words_spin.pack(side="left")

    def browse_voice(self):
        """Browse and select a reference voice audio file."""
        filename = filedialog.askopenfilename(
            title="Select Reference Voice Audio",
            filetypes=[
                ("Audio Files", "*.wav *.mp3 *.ogg *.flac *.m4a"),
                ("All Files", "*.*")
            ]
        )
        if filename:
            try:
                self.tts_controller.set_reference_voice(filename)
                # Show shortened filename
                short_name = filename.split("/")[-1]
                if len(short_name) > 20:
                    short_name = short_name[:17] + "..."
                self.tts_voice_label.config(text=short_name, foreground="black")
                self.tts_status_label.config(text=f"Voice loaded: {short_name}")
            except Exception as e:
                self.tts_status_label.config(text=f"Error loading voice: {e}", foreground="red")

    def clear_voice(self):
        """Clear the reference voice and use default."""
        if self.tts_controller:
            self.tts_controller.set_reference_voice(None)
            self.tts_voice_label.config(text="Default", foreground="gray")
            self.tts_status_label.config(text="Using default voice")

    def on_tts_progress(self, message: str):
        """Called during TTS synthesis progress."""
        if not self.is_shutting_down:
            self.after(0, lambda: self.tts_status_label.config(text=message, foreground="blue"))

    def on_tts_complete(self, filepath: str):
        """Called when TTS synthesis completes."""
        if not self.is_shutting_down:
            filename = filepath.split("/")[-1]
            self.after(0, lambda: self.tts_status_label.config(
                text=f"✓ Saved: {filename}", foreground="green"))

    def on_tts_error(self, error_msg: str):
        """Called when TTS synthesis fails."""
        if not self.is_shutting_down:
            self.after(0, lambda: self.tts_status_label.config(
                text=f"TTS error: {error_msg}", foreground="red"))

    def toggle_text_display(self):
        """Toggle visibility of text panes."""
        if self.text_visible:
            # MINIMAL MODE: Hide text frame
            self.text_frame.grid_remove()
            self.hide_text_button.config(text="Show Text ▶")
            self.text_visible = False

            # Reconfigure grid: controls column expands to fill window
            self.columnconfigure(0, weight=1, minsize=350)
            self.columnconfigure(1, weight=0)  # Text column won't expand

            # Adjust minimum size for minimal mode (never below 400x850)
            self.minsize(400, 850)

            # Resize window to minimal width
            self.geometry("400x850")
        else:
            # FULL MODE: Show text frame
            self.text_frame.grid()
            self.hide_text_button.config(text="Hide Text ◀")
            self.text_visible = True

            # Reconfigure grid: restore original layout
            self.columnconfigure(0, weight=0, minsize=350)  # Controls fixed
            self.columnconfigure(1, weight=1)  # Text column expands

            # Restore minimum size for full mode
            self.minsize(900, 850)

            # Resize window to show both columns
            self.geometry("900x850")

        # Save state to settings
        self.settings.set("text_visible", self.text_visible)
        self.settings.save()

    def on_closing(self):
        """Save settings before closing the window."""
        # Set shutdown flag to prevent TTS thread crashes
        self.is_shutting_down = True

        # Stop any ongoing transcription first
        if hasattr(self, 'ready') and self.ready[0] is not None:
            self.ready[0] = False
            # Give threads a moment to notice the flag
            self.after(100, self._continue_closing)
        else:
            self._continue_closing()

    def _continue_closing(self):
        """Continue with cleanup after stopping transcription."""
        # Save text visibility (already saved in toggle, but ensure it's current)
        self.settings.set("text_visible", self.text_visible)

        # Save TTS settings
        if self.tts_available:
            try:
                tts_enabled = "selected" in self.tts_check.state()
                tts_save_file = "selected" in self.tts_save_check.state()
                self.settings.set("tts_enabled", tts_enabled)
                self.settings.set("tts_save_file", tts_save_file)
            except Exception as e:
                print(f"Error saving TTS settings: {e}")

        # Save AI settings
        if self.ai_available:
            try:
                ai_enabled = "selected" in self.ai_check.state()
                self.settings.set("ai_enabled", ai_enabled)
            except Exception as e:
                print(f"Error saving AI settings: {e}")

        # Persist to disk
        self.settings.save()

        # Clean up TTS controller gracefully
        if self.tts_controller is not None:
            try:
                # Clear callbacks to prevent accessing destroyed widgets
                self.tts_controller.on_progress = None
                self.tts_controller.on_complete = None
                self.tts_controller.on_error = None
                self.tts_controller = None
            except Exception as e:
                print(f"Error cleaning up TTS: {e}")

        # Close the window
        self.destroy()

    def refresh_mics(self):
        current = self.mic_combo.get()
        self.mic_list = core.get_mic_names()
        mic_display = ["(system default)"] + [name for idx, name in self.mic_list]
        self.mic_combo.config(values=mic_display)
        # Try to keep current selection
        if current in mic_display:
            self.mic_combo.set(current)
        else:
            self.mic_combo.current(0)

    def start(self):
        self.ready[0] = False
        self.error[0] = None
        self.status_label.config(text="")
        self.autotype_error_shown = False  # Reset error flag
        self.control_button.config(text="Starting...", command=None, state="disabled")

        # Start new TTS session
        import time
        self.tts_session_id = time.strftime("%Y%m%d_%H%M%S")
        self.tts_session_text = ""
        # Get mic index: use smart default or stored index
        combo_idx = self.mic_combo.current()
        if combo_idx == 0:
            index = core.get_default_device_index()  # Smart default (pipewire/pulse)
        else:
            # mic_list is [(device_index, name), ...], combo index 1 = mic_list[0]
            index = self.mic_list[combo_idx - 1][0]
        model = self.model_combo.get()
        vad = self.vad_check.instate(("selected",))
        para_detect = self.para_check.instate(("selected",))
        self.autotype_mode_active = self.autotype_mode.get()  # Capture autotype mode
        memory = int(self.memory_spin.get())
        patience = float(self.patience_spin.get())
        timeout = float(self.timeout_spin.get())
        prompt = self.prompt_entry.get()
        source = None if self.source_combo.get() == "auto" else self.source_combo.get()
        target = None if self.target_combo.get() == "none" else self.target_combo.get()
        device = self.device_combo.get()
        self.level[0] = 0

        # Create AI processor if enabled
        ai_processor = None
        if self.ai_available and self.ai_check.instate(("selected",)):
            try:
                from ai_provider import AITextProcessor

                # Get selected model
                model_idx = self.ai_model_combo.current()
                models = self.ai_config.get_models()
                selected_model_id = models[model_idx]['id']

                # Determine mode based on selection and target language
                mode_text = self.ai_mode_combo.get()
                if target is None:
                    # No target language - force proofread mode
                    mode = "proofread"
                else:
                    # Map UI text to mode
                    mode_map = {
                        "Proofread": "proofread",
                        "Translate": "translate",
                        "Proofread+Translate": "proofread_translate"
                    }
                    mode = mode_map.get(mode_text, "proofread")

                # Create AI processor
                ai_processor = AITextProcessor(
                    config=self.ai_config,
                    model_id=selected_model_id,
                    mode=mode,
                    source_lang=source,
                    target_lang=target
                )

                mode_display = mode.replace('_', '+').title()
                self.status_label.config(text=f"AI: {models[model_idx]['name']} ({mode_display})", foreground="green")
            except Exception as e:
                self.status_label.config(text=f"AI Error: {str(e)[:50]}", foreground="red")
                print(f"Failed to initialize AI processor: {e}")
                ai_processor = None

        # Get AI processing parameters
        ai_process_interval = int(self.ai_interval_combo.get()) if self.ai_available else 2
        ai_trigger_mode = self.ai_trigger_combo.get().lower() if self.ai_available else "time"
        ai_process_words = int(self.ai_words_spin.get()) if self.ai_available and ai_trigger_mode == "words" else None

        # Check if we need to show proofread window (for AI proofread+translate mode)
        prres_queue = None
        if ai_processor and ai_processor.mode == "proofread_translate":
            prres_queue = self.pr_text.res_queue
            # Show proofread window and buttons
            self.pr_header.grid()
            self.pr_text.grid()
            self.ai_proofread_buttons_frame.grid()
        elif ai_processor and ai_processor.mode == "proofread":
            # Show only buttons for proofread mode (no separate window)
            self.pr_header.grid_remove()
            self.pr_text.grid_remove()
            self.ai_proofread_buttons_frame.grid()
        else:
            # Hide proofread window and buttons
            self.pr_header.grid_remove()
            self.pr_text.grid_remove()
            self.ai_proofread_buttons_frame.grid_remove()

        threading.Thread(target=core.proc, args=(index, model, vad, memory, patience, timeout, prompt, source, target, self.ts_text.res_queue, self.tl_text.res_queue, self.ready, device, self.error, self.level, para_detect), kwargs={'ai_processor': ai_processor, 'ai_process_interval': ai_process_interval, 'ai_process_words': ai_process_words, 'ai_trigger_mode': ai_trigger_mode, 'prres_queue': prres_queue}, daemon=True).start()
        self.starting()
        self.update_level()

    def starting(self):
        if self.ready[0] is True:
            self.control_button.config(text="Stop", command=self.stop, state="normal")
            return
        if self.ready[0] is None:
            if self.error[0]:
                self.status_label.config(text=f"Error: {self.error[0]}")
            self.control_button.config(text="Start", command=self.start, state="normal")
            return
        self.after(100, self.starting)

    def stop(self):
        self.autotype_mode_active = "Off"  # Disable autotype when stopping
        self.ready[0] = False
        self.control_button.config(text="Stopping...", command=None, state="disabled")
        self.stopping()

    def stopping(self):
        if self.ready[0] is None:
            self.control_button.config(text="Start", command=self.start, state="normal")
            self.level_bar['value'] = 0

            # Finalize TTS session when stopping completes
            self.finalize_tts_session()
            return
        self.after(100, self.stopping)

    def update_level(self):
        if self.ready[0] is None:
            self.level_bar['value'] = 0
            return
        # Update level bar with current audio level
        self.level_bar['value'] = min(100, self.level[0])
        self.after(50, self.update_level)


if __name__ == "__main__":
    try:
        App().mainloop()
    except KeyboardInterrupt:
        # Graceful exit on Ctrl+C
        pass

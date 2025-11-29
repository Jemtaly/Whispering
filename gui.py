#!/usr/bin/env python3


import threading
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import filedialog

import core
from cmque import PairDeque, Queue
from settings import Settings


class ToolTip:
    """Simple tooltip helper."""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip = None
        self.widget.bind("<Enter>", self.show)
        self.widget.bind("<Leave>", self.hide)

    def show(self, event=None):
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25

        self.tooltip = tk.Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")

        label = tk.Label(self.tooltip, text=self.text, background="#ffffe0",
                        relief="solid", borderwidth=1, font=("TkDefaultFont", 9))
        label.pack()

    def hide(self, event=None):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None


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
    def __init__(self, master, on_new_text=None):
        super().__init__(master)
        self.res_queue = Queue(PairDeque())
        self.on_new_text = on_new_text  # Callback for NEW text only
        self.tag_config("done", foreground="black")
        self.tag_config("curr", foreground="blue", underline=True)
        self.insert("end", "  ", "done")
        self.record = self.index("end-1c")
        self.prev_done = ""  # Track what we've already processed
        self.see("end")
        # Keep text editable! No state="disabled"
        self.poll()

    def poll(self):
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
        self.after(100, self.poll)

    def clear(self):
        """Clear all text and reset state."""
        self.delete("1.0", "end")
        self.insert("end", "  ", "done")
        self.record = self.index("end-1c")
        self.prev_done = ""


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Whispering")
        self.autotype_enabled = False  # Track autotype state

        # Load settings first
        self.settings = Settings()

        # Load text visibility state from settings (default: True)
        self.text_visible = self.settings.get("text_visible", True)

        # Set minimum window size - will adjust based on mode
        if self.text_visible:
            self.minsize(900, 600)  # Full mode
        else:
            self.minsize(380, 600)  # Minimal mode

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

        # Whisper output (top)
        ts_label = ttk.Label(self.text_frame, text="Whisper Output", font=('TkDefaultFont', 9, 'bold'))
        ts_label.grid(row=0, column=0, sticky="w", padx=5, pady=(0, 2))
        self.ts_text = Text(self.text_frame, on_new_text=self.on_new_transcription)
        self.ts_text.grid(row=1, column=0, sticky="nsew")

        # Translated/Proofread output (bottom)
        tl_label = ttk.Label(self.text_frame, text="Translated/Proofread Output", font=('TkDefaultFont', 9, 'bold'))
        tl_label.grid(row=2, column=0, sticky="w", padx=5, pady=(5, 2))
        self.tl_text = Text(self.text_frame, on_new_text=self.on_new_translation)
        self.tl_text.grid(row=3, column=0, sticky="nsew")

        # Configure text_frame grid
        self.text_frame.columnconfigure(0, weight=1)
        self.text_frame.rowconfigure(1, weight=1)
        self.text_frame.rowconfigure(3, weight=1)

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
        ToolTip(self.mic_button, "Refresh microphone list")

        # === TOGGLE BUTTON ===
        self.hide_text_button = ttk.Button(self.controls_frame, text="Hide Text ◀", command=self.toggle_text_display)
        self.hide_text_button.grid(row=row, column=0, sticky="ew", pady=(0, 10))
        row += 1
        ToolTip(self.hide_text_button, "Hide/show text display panels")

        # === MODEL SECTION ===
        ttk.Separator(self.controls_frame, orient="horizontal").grid(row=row, column=0, sticky="ew", pady=(0, 5))
        row += 1

        model_frame = ttk.Frame(self.controls_frame)
        model_frame.grid(row=row, column=0, sticky="ew", pady=(0, 3))
        row += 1

        ttk.Label(model_frame, text="Model:").pack(side="left", padx=(0, 5))
        self.model_combo = ttk.Combobox(model_frame, values=core.models, state="normal", width=15)
        self.model_combo.set("large-v3")
        self.model_combo.pack(side="left", fill="x", expand=True)
        self.model_combo.bind("<<ComboboxSelected>>", self.on_model_changed)
        ToolTip(self.model_combo, "Whisper model size (larger = more accurate)")

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
        ToolTip(self.vad_check, "Voice Activity Detection filter")

        self.para_check = ttk.Checkbutton(options_frame, text="¶", onvalue=True, offvalue=False)
        self.para_check.state(("!alternate", "selected"))
        self.para_check.pack(side="left", padx=(0, 8))
        ToolTip(self.para_check, "Adaptive paragraph detection")

        self.type_check = ttk.Checkbutton(options_frame, text="⌨", onvalue=True, offvalue=False)
        self.type_check.state(("!alternate",))
        self.type_check.pack(side="left", padx=(0, 8))
        ToolTip(self.type_check, "Auto-type to focused window")

        ttk.Label(options_frame, text="Dev:").pack(side="left", padx=(0, 2))
        self.device_combo = ttk.Combobox(options_frame, values=core.devices, state="readonly", width=6)
        self.device_combo.current(1)
        self.device_combo.pack(side="left")
        ToolTip(self.device_combo, "Inference device (CUDA/CPU)")

        # === MEMORY, PATIENCE, TIMEOUT ===
        params_frame = ttk.Frame(self.controls_frame)
        params_frame.grid(row=row, column=0, sticky="ew", pady=(0, 10))
        row += 1

        ttk.Label(params_frame, text="Mem:").pack(side="left", padx=(0, 2))
        self.memory_spin = ttk.Spinbox(params_frame, from_=1, to=10, increment=1, state="readonly", width=4)
        self.memory_spin.set(3)
        self.memory_spin.pack(side="left", padx=(0, 8))
        ToolTip(self.memory_spin, "Previous segments as context")

        ttk.Label(params_frame, text="Pat:").pack(side="left", padx=(0, 2))
        self.patience_spin = ttk.Spinbox(params_frame, from_=1.0, to=20.0, increment=0.5, state="readonly", width=4)
        self.patience_spin.set(5.0)
        self.patience_spin.pack(side="left", padx=(0, 8))
        ToolTip(self.patience_spin, "Seconds before finalizing segment")

        ttk.Label(params_frame, text="Time:").pack(side="left", padx=(0, 2))
        self.timeout_spin = ttk.Spinbox(params_frame, from_=1.0, to=20.0, increment=0.5, state="readonly", width=4)
        self.timeout_spin.set(5.0)
        self.timeout_spin.pack(side="left")
        ToolTip(self.timeout_spin, "Translation timeout (seconds)")

        # === TRANSLATE/PROOFREAD SECTION ===
        ttk.Separator(self.controls_frame, orient="horizontal").grid(row=row, column=0, sticky="ew", pady=(0, 5))
        row += 1

        ttk.Label(self.controls_frame, text="Translate/Proofread", font=('TkDefaultFont', 9, 'bold')).grid(
            row=row, column=0, sticky="w", pady=(0, 3))
        row += 1

        lang_frame = ttk.Frame(self.controls_frame)
        lang_frame.grid(row=row, column=0, sticky="ew", pady=(0, 10))
        row += 1

        ttk.Label(lang_frame, text="Src:").pack(side="left", padx=(0, 2))
        self.source_combo = ttk.Combobox(lang_frame, values=["auto"] + core.sources, state="readonly", width=5)
        self.source_combo.current(0)
        self.source_combo.pack(side="left", padx=(0, 10))
        ToolTip(self.source_combo, "Source language (auto-detect)")

        ttk.Label(lang_frame, text="Tgt:").pack(side="left", padx=(0, 2))
        self.target_combo = ttk.Combobox(lang_frame, values=["none"] + core.targets, state="readonly", width=5)
        self.target_combo.current(0)
        self.target_combo.bind("<<ComboboxSelected>>", self.on_target_changed)
        self.target_combo.pack(side="left")
        ToolTip(self.target_combo, "Target language for translation")

        # === AI SECTION ===
        ttk.Separator(self.controls_frame, orient="horizontal").grid(row=row, column=0, sticky="ew", pady=(0, 5))
        row += 1

        ttk.Label(self.controls_frame, text="AI Processing", font=('TkDefaultFont', 9, 'bold')).grid(
            row=row, column=0, sticky="w", pady=(0, 3))
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
        ToolTip(self.ai_check, "Enable AI-powered proofreading/translation")

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
        self.ai_interval_combo.current(1)
        if not self.ai_available:
            self.ai_interval_combo.state(("disabled",))
        self.ai_interval_combo.pack(side="left")

        self.ai_words_label = ttk.Label(ai_trigger_frame, text=" words:")
        self.ai_words_spin = ttk.Spinbox(ai_trigger_frame, from_=50, to=500, increment=50, state="readonly", width=5)
        self.ai_words_spin.set(150)
        if not self.ai_available:
            self.ai_words_spin.state(("disabled",))

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

        ttk.Label(self.controls_frame, text="Text-to-Speech", font=('TkDefaultFont', 9, 'bold')).grid(
            row=row, column=0, sticky="w", pady=(0, 3))
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
        ToolTip(self.tts_check, "Enable text-to-speech for proofread output")

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
        ToolTip(self.tts_browse_button, "Upload reference voice audio for cloning")

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
        ToolTip(self.tts_format_combo, "Audio file format")

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
        if self.autotype_enabled and text:
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
        """Called when NEW translated/proofread text arrives. Triggers TTS if enabled."""
        if not text or not self.tts_available or not self.tts_controller:
            return

        # Check if TTS is enabled
        if "selected" not in self.tts_check.state():
            return

        # Check if we should save to file
        save_to_file = "selected" in self.tts_save_check.state()

        if save_to_file:
            # Generate unique filename with timestamp
            import time
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"tts_{timestamp}"
            file_format = self.tts_format_combo.get()

            # Synthesize and save to file in background thread
            self.tts_controller.synthesize_to_file(
                text=text,
                output_filename=filename,
                file_format=file_format,
                async_mode=True
            )
        else:
            # Just synthesize for playback (don't save)
            # For now, we still save to temp file since we don't have audio playback yet
            # TODO: Add audio playback functionality
            import time
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"tts_temp_{timestamp}"

            # Still save for now (future: add sounddevice playback)
            self.tts_controller.synthesize_to_file(
                text=text,
                output_filename=filename,
                file_format="wav",
                async_mode=True
            )

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
        self.after(0, lambda: self.tts_status_label.config(text=message, foreground="blue"))

    def on_tts_complete(self, filepath: str):
        """Called when TTS synthesis completes."""
        filename = filepath.split("/")[-1]
        self.after(0, lambda: self.tts_status_label.config(
            text=f"✓ Saved: {filename}", foreground="green"))

    def on_tts_error(self, error_msg: str):
        """Called when TTS synthesis fails."""
        self.after(0, lambda: self.tts_status_label.config(
            text=f"TTS error: {error_msg}", foreground="red"))

    def toggle_text_display(self):
        """Toggle visibility of text panes."""
        if self.text_visible:
            # MINIMAL MODE: Hide text frame
            self.text_frame.grid_remove()
            self.hide_text_button.config(text="Show Text ▶")
            self.text_visible = False
            # Adjust minimum size for minimal mode (narrow column)
            self.minsize(380, 600)
        else:
            # FULL MODE: Show text frame
            self.text_frame.grid()
            self.hide_text_button.config(text="Hide Text ◀")
            self.text_visible = True
            # Restore minimum size for full mode (two columns)
            self.minsize(900, 600)

        # Save state to settings
        self.settings.set("text_visible", self.text_visible)
        self.settings.save()

    def on_closing(self):
        """Save settings before closing the window."""
        # Save text visibility (already saved in toggle, but ensure it's current)
        self.settings.set("text_visible", self.text_visible)

        # Save TTS settings
        if self.tts_available:
            tts_enabled = "selected" in self.tts_check.state()
            tts_save_file = "selected" in self.tts_save_check.state()
            self.settings.set("tts_enabled", tts_enabled)
            self.settings.set("tts_save_file", tts_save_file)

        # Save AI settings
        if self.ai_available:
            ai_enabled = "selected" in self.ai_check.state()
            self.settings.set("ai_enabled", ai_enabled)

        # Persist to disk
        self.settings.save()

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
        self.autotype_enabled = self.type_check.instate(("selected",))  # Capture autotype state
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

        threading.Thread(target=core.proc, args=(index, model, vad, memory, patience, timeout, prompt, source, target, self.ts_text.res_queue, self.tl_text.res_queue, self.ready, device, self.error, self.level, para_detect), kwargs={'ai_processor': ai_processor, 'ai_process_interval': ai_process_interval, 'ai_process_words': ai_process_words, 'ai_trigger_mode': ai_trigger_mode}, daemon=True).start()
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
        self.autotype_enabled = False  # Disable autotype when stopping
        self.ready[0] = False
        self.control_button.config(text="Stopping...", command=None, state="disabled")
        self.stopping()

    def stopping(self):
        if self.ready[0] is None:
            self.control_button.config(text="Start", command=self.start, state="normal")
            self.level_bar['value'] = 0
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
    App().mainloop()

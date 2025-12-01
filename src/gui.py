#!/usr/bin/env python3


import threading
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import filedialog, messagebox

import core
from settings import Settings
from gui_parts.help_dialog import HelpDialog, MODEL_VRAM
from gui_parts.text_widget import Text





class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Whispering")
        self.autotype_mode_active = "Off"  # Track autotype mode: Off, Whisper, Translation, AI

        # Load settings first
        self.settings = Settings()

        # Load debug mode from settings (default: False)
        self.debug_enabled = self.settings.get("debug_enabled", False)

        # Load text visibility state from settings (default: False - start in minimal mode)
        self.text_visible = self.settings.get("text_visible", False)

        # Flag to track if we're shutting down (prevent TTS crashes)
        self.is_shutting_down = False

        # Set minimum window size - will adjust based on mode
        # For minimal mode: calculate based on controls, for full mode add space for text
        # Minimal mode: 400x1000 minimum (never go below this)
        # Full mode: 900x1000 gives space for text panels
        if self.text_visible:
            self.minsize(900, 1000)  # Full mode - more vertical space for text
            self.maxsize(10000, 1000)  # Limit max height to 1000px
        else:
            self.minsize(400, 1000)  # Minimal mode - never below 400x1000
            self.maxsize(10000, 1000)  # Limit max height to 1000px

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

        # Create frame for text widget and scrollbar
        ts_frame = ttk.Frame(self.text_frame)
        ts_frame.grid(row=1, column=0, sticky="nsew")
        ts_frame.columnconfigure(0, weight=1)
        ts_frame.rowconfigure(0, weight=1)

        self.ts_text = Text(ts_frame, on_new_text=self.on_new_transcription, on_text_changed=self.update_ts_count)
        self.ts_text.grid(row=0, column=0, sticky="nsew")

        ts_scrollbar = ttk.Scrollbar(ts_frame, command=self.ts_text.yview)
        ts_scrollbar.grid(row=0, column=1, sticky="ns")
        self.ts_text.config(yscrollcommand=ts_scrollbar.set)

        # AI processed output (middle) - header frame with label and count
        pr_header = ttk.Frame(self.text_frame)
        pr_header.grid(row=2, column=0, sticky="ew", padx=5, pady=(5, 2))
        pr_label = ttk.Label(pr_header, text="AI Output", font=('TkDefaultFont', 9, 'bold'))
        pr_label.pack(side="left")
        self.pr_count_label = ttk.Label(pr_header, text="0 chars, 0 words", font=('TkDefaultFont', 8), foreground="gray")
        self.pr_count_label.pack(side="right")

        # Create frame for text widget and scrollbar
        pr_frame = ttk.Frame(self.text_frame)
        pr_frame.grid(row=3, column=0, sticky="nsew")
        pr_frame.columnconfigure(0, weight=1)
        pr_frame.rowconfigure(0, weight=1)

        self.pr_text = Text(pr_frame, on_new_text=self.on_new_proofread, on_text_changed=self.update_pr_count)
        self.pr_text.grid(row=0, column=0, sticky="nsew")

        pr_scrollbar = ttk.Scrollbar(pr_frame, command=self.pr_text.yview)
        pr_scrollbar.grid(row=0, column=1, sticky="ns")
        self.pr_text.config(yscrollcommand=pr_scrollbar.set)

        # Disable proofread window by default (enable when AI proofread+translate is active)
        # Keep visible but grayed out
        self.pr_text.config(state="disabled", background="#f0f0f0")

        # Translation output (bottom) - header frame with label and count
        tl_header = ttk.Frame(self.text_frame)
        tl_header.grid(row=4, column=0, sticky="ew", padx=5, pady=(5, 2))
        tl_label = ttk.Label(tl_header, text="Translation Output", font=('TkDefaultFont', 9, 'bold'))
        tl_label.pack(side="left")
        self.tl_count_label = ttk.Label(tl_header, text="0 chars, 0 words", font=('TkDefaultFont', 8), foreground="gray")
        self.tl_count_label.pack(side="right")

        # Create frame for text widget and scrollbar
        tl_frame = ttk.Frame(self.text_frame)
        tl_frame.grid(row=5, column=0, sticky="nsew")
        tl_frame.columnconfigure(0, weight=1)
        tl_frame.rowconfigure(0, weight=1)

        self.tl_text = Text(tl_frame, on_new_text=self.on_new_translation, on_text_changed=self.update_tl_count)
        self.tl_text.grid(row=0, column=0, sticky="nsew")

        tl_scrollbar = ttk.Scrollbar(tl_frame, command=self.tl_text.yview)
        tl_scrollbar.grid(row=0, column=1, sticky="ns")
        self.tl_text.config(yscrollcommand=tl_scrollbar.set)

        # Store references to show/hide proofread window dynamically
        self.pr_header = pr_header

        # Configure text_frame grid
        self.text_frame.columnconfigure(0, weight=1)
        self.text_frame.rowconfigure(1, weight=1)  # Whisper
        self.text_frame.rowconfigure(3, weight=1)  # Proofread
        self.text_frame.rowconfigure(5, weight=1)  # Translation

        # Grid layout: controls in column 0, text frame in column 1
        self.controls_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        # Hide or show text frame based on initial state
        if self.text_visible:
            self.text_frame.grid(row=0, column=1, sticky="nsew")
        # else: don't grid it (starts hidden in minimal mode)

        # Configure grid weights based on initial mode
        if self.text_visible:
            self.columnconfigure(0, weight=0, minsize=350)  # Controls column - fixed width
            self.columnconfigure(1, weight=1)  # Text column - expandable
        else:
            self.columnconfigure(0, weight=1, minsize=350)  # Controls column expands in minimal mode
            self.columnconfigure(1, weight=0)  # Text column hidden

        self.rowconfigure(0, weight=1)  # Main row for both frames

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
        # Set initial button text based on visibility state
        button_text = "Hide Text ◀" if self.text_visible else "Show Text ▶"
        self.hide_text_button = ttk.Button(self.controls_frame, text=button_text, command=self.toggle_text_display)
        self.hide_text_button.grid(row=row, column=0, sticky="ew", pady=(0, 10))
        row += 1

        # === MODEL SECTION ===
        ttk.Separator(self.controls_frame, orient="horizontal").grid(row=row, column=0, sticky="ew", pady=(0, 5))
        row += 1

        # Section header with help button
        model_header = ttk.Frame(self.controls_frame)
        model_header.grid(row=row, column=0, sticky="ew", pady=(0, 3))
        ttk.Label(model_header, text="Model Settings Speech-to-Text", font=('TkDefaultFont', 9, 'bold')).pack(side="left")
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

        # AI Persona/Task
        ai_persona_frame = ttk.Frame(self.controls_frame)
        ai_persona_frame.grid(row=row, column=0, sticky="ew", pady=(0, 5))
        row += 1

        ttk.Label(ai_persona_frame, text="Task:").pack(side="left", padx=(0, 2))
        if self.ai_available:
            personas = self.ai_config.get_personas()
            persona_names = [p['name'] for p in personas]
            self.persona_ids = [p['id'] for p in personas]  # Store IDs for mapping
        else:
            persona_names = ["Proofread"]
            self.persona_ids = ["proofread"]

        self.ai_persona_combo = ttk.Combobox(ai_persona_frame, values=persona_names, state="readonly", width=18)
        self.ai_persona_combo.current(0)
        if not self.ai_available:
            self.ai_persona_combo.state(("disabled",))
        self.ai_persona_combo.pack(side="left", fill="x", expand=True)

        # AI Translate controls
        ai_translate_frame = ttk.Frame(self.controls_frame)
        ai_translate_frame.grid(row=row, column=0, sticky="ew", pady=(0, 5))
        row += 1

        self.ai_translate_check = ttk.Checkbutton(ai_translate_frame, text="Translate output", onvalue=True, offvalue=False, command=self.on_translate_mode_changed)
        if self.ai_available:
            self.ai_translate_check.state(("!alternate",))
        else:
            self.ai_translate_check.state(("disabled",))
        self.ai_translate_check.pack(side="left", padx=(0, 10))

        self.ai_translate_only_check = ttk.Checkbutton(ai_translate_frame, text="Translate Only (1:1)", onvalue=True, offvalue=False, command=self.on_translate_mode_changed)
        if self.ai_available:
            self.ai_translate_only_check.state(("!alternate",))
        else:
            self.ai_translate_only_check.state(("disabled",))
        self.ai_translate_only_check.pack(side="left")

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

        # AI Trigger - Split into left (manual) and right (automatic)
        ai_trigger_frame = ttk.Frame(self.controls_frame)
        ai_trigger_frame.grid(row=row, column=0, sticky="ew", pady=(0, 5))
        row += 1

        # LEFT SIDE: Manual mode
        manual_frame = ttk.Frame(ai_trigger_frame)
        manual_frame.pack(side="left", fill="x", expand=False)

        self.ai_manual_mode_check = ttk.Checkbutton(manual_frame, text="Manual mode", onvalue=True, offvalue=False, command=self.on_trigger_mode_changed)
        if self.ai_available:
            self.ai_manual_mode_check.state(("!alternate",))
        else:
            self.ai_manual_mode_check.state(("disabled",))
        self.ai_manual_mode_check.pack(side="top", anchor="w")

        self.ai_manual_button = ttk.Button(manual_frame, text="⚡ Process Now", width=12, command=self.manual_ai_trigger)
        if not self.ai_available:
            self.ai_manual_button.state(("disabled",))
        else:
            self.ai_manual_button.state(("disabled",))  # Disabled by default (enable when manual mode is checked)
        self.ai_manual_button.pack(side="top", anchor="w", pady=(2, 0))

        # RIGHT SIDE: Automatic triggers
        auto_frame = ttk.Frame(ai_trigger_frame)
        auto_frame.pack(side="right", fill="x", expand=True)

        trigger_row = ttk.Frame(auto_frame)
        trigger_row.pack(side="top", fill="x", anchor="e")
        ttk.Label(trigger_row, text="Trigger:").pack(side="left", padx=(0, 2))
        self.ai_trigger_combo = ttk.Combobox(trigger_row, values=["Time", "Words"], state="readonly", width=7)
        self.ai_trigger_combo.current(0)
        self.ai_trigger_combo.bind("<<ComboboxSelected>>", self.on_trigger_changed)
        if not self.ai_available:
            self.ai_trigger_combo.state(("disabled",))
        self.ai_trigger_combo.pack(side="left")

        interval_row = ttk.Frame(auto_frame)
        interval_row.pack(side="top", fill="x", pady=(2, 0), anchor="e")
        self.ai_interval_label = ttk.Label(interval_row, text="Interval:")
        self.ai_interval_label.pack(side="left", padx=(0, 2))
        # Intervals: 5, 10, 15, 20, 25, 30, 45 seconds, 60 (1min), 90 (1.5min), 120 (2min)
        interval_values = ["5", "10", "15", "20", "25", "30", "45", "60", "90", "120"]
        interval_labels = ["5s", "10s", "15s", "20s", "25s", "30s", "45s", "1m", "1.5m", "2m"]
        self.ai_interval_combo = ttk.Combobox(interval_row, values=interval_labels, state="readonly", width=6)
        self.ai_interval_combo.current(3)  # Default to 20 seconds
        self.ai_interval_values_map = dict(zip(interval_labels, interval_values))  # Map display to actual values
        if not self.ai_available:
            self.ai_interval_combo.state(("disabled",))
        self.ai_interval_combo.pack(side="left")

        self.ai_words_label = ttk.Label(interval_row, text=" words:")
        self.ai_words_spin = ttk.Spinbox(interval_row, from_=50, to=500, increment=50, state="readonly", width=5)
        self.ai_words_spin.set(150)
        if not self.ai_available:
            self.ai_words_spin.state(("disabled",))
        self.ai_words_spin.pack(side="left")

        # Store references for enable/disable
        self.auto_trigger_widgets = [self.ai_trigger_combo, self.ai_interval_combo, self.ai_words_spin, self.ai_interval_label, self.ai_words_label]

        # AI output Copy/Cut buttons with count
        ai_output_buttons_frame = ttk.Frame(self.controls_frame)
        ai_output_buttons_frame.grid(row=row, column=0, sticky="ew", pady=(5, 5))
        row += 1

        ttk.Button(ai_output_buttons_frame, text="Copy AI Output", command=self.copy_proofread_text, width=15).pack(side="left", padx=(0, 5))
        ttk.Button(ai_output_buttons_frame, text="Cut AI Output", command=self.cut_proofread_text, width=15).pack(side="left", padx=(0, 5))
        self.proofread_count_button = ttk.Label(ai_output_buttons_frame, text="0c, 0w", foreground="blue", font=('TkDefaultFont', 8))
        self.proofread_count_button.pack(side="left")

        # Store ref to show/hide when needed
        self.ai_output_buttons_frame = ai_output_buttons_frame
        # Hide by default (only show when AI is active)
        ai_output_buttons_frame.grid_remove()

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

        # TTS Source selection (mutually exclusive)
        tts_source_frame = ttk.Frame(self.controls_frame)
        tts_source_frame.grid(row=row, column=0, sticky="ew", pady=(0, 5))
        row += 1

        ttk.Label(tts_source_frame, text="Source:").pack(side="left", padx=(0, 5))

        self.tts_source_whisper = ttk.Checkbutton(tts_source_frame, text="W", onvalue=True, offvalue=False,
                                                   command=lambda: self.on_tts_source_changed("whisper"))
        if self.tts_available:
            self.tts_source_whisper.state(("!alternate", "selected"))  # Default to Whisper
        else:
            self.tts_source_whisper.state(("disabled",))
        self.tts_source_whisper.pack(side="left", padx=(0, 5))

        self.tts_source_ai = ttk.Checkbutton(tts_source_frame, text="A", onvalue=True, offvalue=False,
                                             command=lambda: self.on_tts_source_changed("ai"))
        if self.tts_available:
            self.tts_source_ai.state(("!alternate",))
        else:
            self.tts_source_ai.state(("disabled",))
        self.tts_source_ai.pack(side="left", padx=(0, 5))

        self.tts_source_translation = ttk.Checkbutton(tts_source_frame, text="T", onvalue=True, offvalue=False,
                                                      command=lambda: self.on_tts_source_changed("translation"))
        if self.tts_available:
            self.tts_source_translation.state(("!alternate",))
        else:
            self.tts_source_translation.state(("disabled",))
        self.tts_source_translation.pack(side="left", padx=(0, 5))

        # Track current TTS source
        self.tts_source_active = "whisper"  # Default to Whisper

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
                                         wraplength=340, font=('TkDefaultFont', 8))
        self.tts_status_label.grid(row=row, column=0, sticky="ew", pady=(0, 5), padx=5)
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

        # Auto-stop controls
        autostop_frame = ttk.Frame(control_frame)
        autostop_frame.pack(side="top", fill="x", pady=(5, 0))

        self.autostop_check = ttk.Checkbutton(autostop_frame, text="Auto-stop after", onvalue=True, offvalue=False)
        self.autostop_check.pack(side="left", padx=(0, 2))

        self.autostop_spin = ttk.Spinbox(autostop_frame, from_=1, to=60, increment=1, state="normal", width=4)
        self.autostop_spin.set(5)  # Default 5 minutes
        self.autostop_spin.pack(side="left", padx=(0, 2))

        ttk.Label(autostop_frame, text="min of inactivity").pack(side="left")

        # === STATUS ===
        self.status_label = ttk.Label(self.controls_frame, text="", foreground="red", wraplength=340)
        self.status_label.grid(row=row, column=0, sticky="ew", padx=5)
        row += 1

        # State variables
        self.ready = [None]
        self.error = [None]
        self.level = [0]
        self.autotype_error_shown = False
        self.manual_trigger_requested = [False]  # Flag for manual AI processing

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
            tts_source = self.settings.get("tts_source", "whisper")

            if tts_enabled:
                self.tts_check.state(("selected",))
            if tts_save_file:
                self.tts_save_check.state(("selected",))

            # Restore TTS source selection
            self.tts_source_active = tts_source
            if tts_source == "whisper":
                self.tts_source_whisper.state(("selected",))
            elif tts_source == "ai":
                self.tts_source_ai.state(("selected",))
            elif tts_source == "translation":
                self.tts_source_translation.state(("selected",))

        # Load and apply AI settings
        if self.ai_available:
            ai_enabled = self.settings.get("ai_enabled", False)
            if ai_enabled:
                self.ai_check.state(("selected",))

            # Load AI persona/task
            ai_persona_index = self.settings.get("ai_persona_index", 0)
            try:
                if 0 <= ai_persona_index < len(self.ai_persona_combo.cget("values")):
                    self.ai_persona_combo.current(ai_persona_index)
            except:
                pass

            # Load AI translate checkbox
            ai_translate = self.settings.get("ai_translate", False)
            if ai_translate:
                self.ai_translate_check.state(("selected",))

            # Load AI translate-only checkbox
            ai_translate_only = self.settings.get("ai_translate_only", False)
            if ai_translate_only:
                self.ai_translate_only_check.state(("selected",))
                # Trigger the mode changed handler to disable task controls
                self.on_translate_mode_changed()

            # Load AI manual mode checkbox
            ai_manual_mode = self.settings.get("ai_manual_mode", False)
            if ai_manual_mode:
                self.ai_manual_mode_check.state(("selected",))
                # Trigger the mode changed handler to enable/disable controls
                self.on_trigger_mode_changed()

            # Load AI model selection
            ai_model_index = self.settings.get("ai_model_index", 0)
            try:
                if 0 <= ai_model_index < len(self.ai_model_combo.cget("values")):
                    self.ai_model_combo.current(ai_model_index)
            except:
                pass

            # Load AI trigger mode
            ai_trigger_mode = self.settings.get("ai_trigger_mode", "time")
            try:
                trigger_values = self.ai_trigger_combo.cget("values")
                trigger_display = ai_trigger_mode.capitalize()
                if trigger_display in trigger_values:
                    self.ai_trigger_combo.set(trigger_display)
            except:
                pass

            # Load AI interval (convert seconds to label)
            ai_process_interval = self.settings.get("ai_process_interval", 20)
            try:
                # Find the label that matches this interval value
                for label, value in self.ai_interval_values_map.items():
                    if int(value) == ai_process_interval:
                        self.ai_interval_combo.set(label)
                        break
            except:
                pass

            # Load AI words
            ai_process_words = self.settings.get("ai_process_words", 150)
            try:
                self.ai_words_spin.set(ai_process_words)
            except:
                pass

        # Load auto-stop settings
        auto_stop_enabled = self.settings.get("auto_stop_enabled", False)
        auto_stop_minutes = self.settings.get("auto_stop_minutes", 5)
        if auto_stop_enabled:
            self.autostop_check.state(("selected",))
        try:
            self.autostop_spin.set(auto_stop_minutes)
        except:
            pass

        # Load translation language settings
        try:
            source_lang = self.settings.get("source_language", "auto")
            target_lang = self.settings.get("target_language", "none")

            # Set source language
            source_values = self.source_combo.cget("values")
            if source_lang in source_values:
                self.source_combo.set(source_lang)

            # Set target language
            target_values = self.target_combo.cget("values")
            if target_lang in target_values:
                self.target_combo.set(target_lang)
        except Exception as e:
            print(f"Error loading language settings: {e}")

        # Set initial trigger field visibility based on trigger mode
        if self.ai_available:
            self.on_trigger_changed()

        # Set initial window geometry based on mode
        if self.text_visible:
            self.geometry("900x1000")  # Full mode
        else:
            self.geometry("400x1000")  # Minimal mode (default)

        # Save settings on window close
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_new_transcription(self, text):
        """Called when NEW transcription text arrives. Auto-types if enabled."""
        # Accumulate for TTS if Whisper source is selected
        if self.tts_available and "selected" in self.tts_check.state() and self.tts_source_active == "whisper":
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
        # Accumulate for TTS if Translation source is selected
        if self.tts_available and "selected" in self.tts_check.state() and self.tts_source_active == "translation":
            self.tts_session_text += text + " "

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
        # Accumulate for TTS if AI source is selected
        if self.tts_available and "selected" in self.tts_check.state() and self.tts_source_active == "ai":
            self.tts_session_text += text + " "

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

    def on_trigger_mode_changed(self):
        """Handle Manual mode checkbox - enable/disable manual vs automatic triggers."""
        if not self.ai_available:
            return

        manual_mode = "selected" in self.ai_manual_mode_check.state()

        if manual_mode:
            # Manual mode: enable Process Now button, disable automatic triggers
            self.ai_manual_button.state(("!disabled",))
            for widget in self.auto_trigger_widgets:
                try:
                    widget.state(("disabled",))
                except:
                    widget.config(state="disabled")  # For Label widgets
        else:
            # Automatic mode: disable Process Now button, enable automatic triggers
            self.ai_manual_button.state(("disabled",))
            for widget in self.auto_trigger_widgets:
                try:
                    widget.state(("!disabled",))
                except:
                    widget.config(state="normal")  # For Label widgets

    def on_translate_mode_changed(self):
        """Handle Translate Only checkbox - disable/enable task controls and auto-enable AI."""
        if not self.ai_available:
            return

        translate_only = "selected" in self.ai_translate_only_check.state()
        translate_output = "selected" in self.ai_translate_check.state()

        # Validate target language is set before allowing translation
        target = self.target_combo.get()
        if (translate_only or translate_output) and (target is None or target == "none"):
            # Uncheck the option and show warning
            if translate_only:
                self.ai_translate_only_check.state(("!selected",))
            if translate_output:
                self.ai_translate_check.state(("!selected",))
            self.status_label.config(text="⚠ Please select translation target language first", foreground="red")
            return

        # Auto-enable AI if translation features are used
        if translate_only or translate_output:
            self.ai_check.state(("selected",))

        if translate_only:
            # Translate Only mode: disable task and translate output checkbox
            self.ai_persona_combo.state(("disabled",))
            self.ai_translate_check.state(("disabled",))
        else:
            # Normal mode: enable task and translate output checkbox
            self.ai_persona_combo.state(("!disabled",))
            self.ai_translate_check.state(("!disabled",))

    def manual_ai_trigger(self):
        """Manual trigger for AI processing - process accumulated text immediately."""
        if not self.ready[0]:
            # Not running, can't trigger
            return

        # Set flag to request manual processing
        self.manual_trigger_requested[0] = True
        if self.debug_enabled:
            print("[GUI] Manual AI processing requested", flush=True)

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
        """Handle target language changes - turn off Translate Output if target is none."""
        if not self.ai_available:
            return

        target = self.target_combo.get()
        if target == "none" or target is None:
            # Turn off Translate Output checkbox if target is none
            self.ai_translate_check.state(("!selected",))

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

    def on_tts_source_changed(self, source):
        """Handle TTS source selection - make checkboxes mutually exclusive."""
        if not self.tts_available:
            return

        # Update active source
        self.tts_source_active = source

        # Uncheck all others
        if source == "whisper":
            self.tts_source_whisper.state(("selected",))
            self.tts_source_ai.state(("!selected",))
            self.tts_source_translation.state(("!selected",))
        elif source == "ai":
            self.tts_source_whisper.state(("!selected",))
            self.tts_source_ai.state(("selected",))
            self.tts_source_translation.state(("!selected",))
        else:  # translation
            self.tts_source_whisper.state(("!selected",))
            self.tts_source_ai.state(("!selected",))
            self.tts_source_translation.state(("selected",))

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

            # Adjust minimum size for minimal mode (never below 400x1000)
            self.minsize(400, 1000)
            self.maxsize(10000, 1000)  # Limit max height to 1000px

            # Resize window to minimal width
            self.geometry("400x1000")
        else:
            # FULL MODE: Show text frame
            self.text_frame.grid()
            self.hide_text_button.config(text="Hide Text ◀")
            self.text_visible = True

            # Reconfigure grid: restore original layout
            self.columnconfigure(0, weight=0, minsize=350)  # Controls fixed
            self.columnconfigure(1, weight=1)  # Text column expands

            # Restore minimum size for full mode
            self.minsize(900, 1000)
            self.maxsize(10000, 1000)  # Limit max height to 1000px

            # Resize window to show both columns (max height 1000px)
            self.geometry("900x1000")

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
                self.settings.set("tts_source", self.tts_source_active)
            except Exception as e:
                print(f"Error saving TTS settings: {e}")

        # Save AI settings
        if self.ai_available:
            try:
                ai_enabled = "selected" in self.ai_check.state()
                self.settings.set("ai_enabled", ai_enabled)

                # Save AI translate checkbox
                ai_translate = "selected" in self.ai_translate_check.state()
                self.settings.set("ai_translate", ai_translate)

                # Save AI translate-only checkbox
                ai_translate_only = "selected" in self.ai_translate_only_check.state()
                self.settings.set("ai_translate_only", ai_translate_only)

                # Save AI manual mode checkbox
                ai_manual_mode = "selected" in self.ai_manual_mode_check.state()
                self.settings.set("ai_manual_mode", ai_manual_mode)

                # Save AI persona selection
                persona_idx = self.ai_persona_combo.current()
                self.settings.set("ai_persona_index", persona_idx)

                # Save AI model selection
                ai_model_index = self.ai_model_combo.current()
                self.settings.set("ai_model_index", ai_model_index)

                # Save AI trigger mode and interval/words
                ai_trigger_mode = self.ai_trigger_combo.get().lower()
                self.settings.set("ai_trigger_mode", ai_trigger_mode)

                # Save interval value (convert from label to seconds)
                interval_label = self.ai_interval_combo.get()
                ai_process_interval = int(self.ai_interval_values_map.get(interval_label, "20"))
                self.settings.set("ai_process_interval", ai_process_interval)

                # Save words value
                ai_process_words = int(self.ai_words_spin.get())
                self.settings.set("ai_process_words", ai_process_words)
            except Exception as e:
                print(f"Error saving AI settings: {e}")

        # Save translation language settings
        try:
            source_lang = self.source_combo.get()
            target_lang = self.target_combo.get()
            self.settings.set("source_language", source_lang)
            self.settings.set("target_language", target_lang)
        except Exception as e:
            print(f"Error saving language settings: {e}")

        # Save auto-stop settings
        try:
            auto_stop_enabled = "selected" in self.autostop_check.state()
            auto_stop_minutes = int(self.autostop_spin.get())
            self.settings.set("auto_stop_enabled", auto_stop_enabled)
            self.settings.set("auto_stop_minutes", auto_stop_minutes)
        except Exception as e:
            print(f"Error saving auto-stop settings: {e}")

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
        # Validation: Check if target language is required but not set
        target = self.target_combo.get()

        # Check if translation is needed
        needs_translation = False
        if self.ai_available:
            translate_only = self.ai_translate_only_check.instate(("selected",))
            translate_output = self.ai_translate_check.instate(("selected",))
            ai_enabled = self.ai_check.instate(("selected",))

            if translate_only or (ai_enabled and translate_output):
                needs_translation = True

        # Validate target language
        if needs_translation and (target is None or target == "none"):
            self.status_label.config(text="⚠ Please select a target language for translation", foreground="red")
            return

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
        prompt = ""  # Removed prompt entry - using custom tasks instead
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

                # Get persona and translate settings
                translate_only = self.ai_translate_only_check.instate(("selected",))

                # Determine mode based on translate-only or task mode
                if translate_only:
                    # Translate Only mode: direct 1:1 AI translation (no processing)
                    mode = "translate"
                    persona_name = "Translate Only"
                else:
                    # Task mode: get persona and translate settings
                    persona_idx = self.ai_persona_combo.current()
                    persona_id = self.persona_ids[persona_idx]
                    translate_enabled = self.ai_translate_check.instate(("selected",))

                    # Map persona + translate to mode
                    if persona_id == "proofread":
                        # Built-in proofread persona
                        if translate_enabled and target is not None:
                            mode = "proofread_translate"
                        else:
                            mode = "proofread"
                    else:
                        # Custom persona - for now, treat as proofread
                        # TODO: Add custom persona support to ai_provider.py
                        if translate_enabled and target is not None:
                            mode = "proofread_translate"
                        else:
                            mode = "proofread"

                    persona_name = self.ai_persona_combo.get()

                # Create AI processor
                ai_processor = AITextProcessor(
                    config=self.ai_config,
                    model_id=selected_model_id,
                    mode=mode,
                    source_lang=source,
                    target_lang=target
                )

                # Display status
                if translate_only:
                    self.status_label.config(text=f"AI: {models[model_idx]['name']} (Translate Only)", foreground="green")
                else:
                    translate_status = " + Translate" if translate_enabled and target else ""
                    self.status_label.config(text=f"AI: {models[model_idx]['name']} ({persona_name}{translate_status})", foreground="green")
            except Exception as e:
                self.status_label.config(text=f"AI Error: {str(e)[:50]}", foreground="red")
                print(f"Failed to initialize AI processor: {e}")
                ai_processor = None

        # Get AI processing parameters
        manual_mode = "selected" in self.ai_manual_mode_check.state() if self.ai_available else False

        if manual_mode:
            # Manual mode: set trigger to "manual" to skip automatic processing
            ai_trigger_mode = "manual"
            ai_process_interval = 999999  # Large value (won't be used)
            ai_process_words = None
            if self.debug_enabled:
                print(f"[GUI] AI Trigger Mode: Manual", flush=True)
        else:
            # Automatic mode: use configured trigger settings
            if self.ai_available:
                interval_label = self.ai_interval_combo.get()
                ai_process_interval = int(self.ai_interval_values_map.get(interval_label, "20"))  # seconds
            else:
                ai_process_interval = 20  # Default 20 seconds
            ai_trigger_mode = self.ai_trigger_combo.get().lower() if self.ai_available else "time"
            ai_process_words = int(self.ai_words_spin.get()) if self.ai_available and ai_trigger_mode == "words" else None

            # Debug logging
            if self.debug_enabled:
                if ai_trigger_mode == "time":
                    print(f"[GUI] AI Trigger Mode: Time, Interval: {ai_process_interval}s", flush=True)
                else:
                    print(f"[GUI] AI Trigger Mode: Words, Word Count: {ai_process_words}", flush=True)

        # Get auto-stop parameters from GUI
        auto_stop_enabled = "selected" in self.autostop_check.state()
        auto_stop_minutes = int(self.autostop_spin.get())

        # Check if we need to enable proofread window (for AI proofread+translate or proofread-only modes)
        prres_queue = None
        if ai_processor and ai_processor.mode == "proofread_translate":
            prres_queue = self.pr_text.res_queue
            # Enable proofread window and show buttons
            if self.debug_enabled:
                print(f"[GUI] Enabling proofread window (mode: {ai_processor.mode})", flush=True)
                print(f"[GUI] prres_queue ID: {id(prres_queue)}", flush=True)
                print(f"[GUI] self.pr_text.res_queue ID: {id(self.pr_text.res_queue)}", flush=True)
            self.pr_text.config(state="normal", background="white")
            self.ai_output_buttons_frame.grid()
        elif ai_processor and ai_processor.mode == "proofread":
            # Enable proofread window for proofread-only mode, show buttons
            prres_queue = self.pr_text.res_queue  # FIX: Set queue for proofread-only mode
            if self.debug_enabled:
                print(f"[GUI] Enabling proofread window (mode: {ai_processor.mode})", flush=True)
                print(f"[GUI] prres_queue ID: {id(prres_queue)}", flush=True)
            self.pr_text.config(state="normal", background="white")
            self.ai_output_buttons_frame.grid()
        else:
            # Disable proofread window and hide buttons (keep visible but grayed)
            if self.debug_enabled:
                print(f"[GUI] Disabling proofread window (mode: {ai_processor.mode if ai_processor else 'None'})", flush=True)
            self.pr_text.config(state="disabled", background="#f0f0f0")
            self.ai_output_buttons_frame.grid_remove()

        threading.Thread(target=core.proc, args=(index, model, vad, memory, patience, timeout, prompt, source, target, self.ts_text.res_queue, self.tl_text.res_queue, self.ready, device, self.error, self.level, para_detect), kwargs={'ai_processor': ai_processor, 'ai_process_interval': ai_process_interval, 'ai_process_words': ai_process_words, 'ai_trigger_mode': ai_trigger_mode, 'prres_queue': prres_queue, 'auto_stop_enabled': auto_stop_enabled, 'auto_stop_minutes': auto_stop_minutes, 'manual_trigger': self.manual_trigger_requested}, daemon=True).start()
        self.starting()
        self.update_level()

    def lock_ui_controls(self):
        """Lock UI controls that shouldn't be changed while running."""
        # Lock model settings
        self.model_combo.state(("disabled",))
        self.device_combo.state(("disabled",))
        self.autotype_mode.state(("disabled",))

        # Lock translation language dropdowns
        self.source_combo.state(("disabled",))
        self.target_combo.state(("disabled",))

        # Lock AI settings
        if self.ai_available:
            # Get current AI state
            ai_enabled = "selected" in self.ai_check.state()

            # Lock Enable AI checkbox
            self.ai_check.state(("disabled",))

            # Lock AI controls
            self.ai_translate_only_check.state(("disabled",))
            self.ai_translate_check.state(("disabled",))
            self.ai_persona_combo.state(("disabled",))
            self.ai_model_combo.state(("disabled",))
            self.ai_manual_mode_check.state(("disabled",))

            # Lock trigger controls
            self.ai_trigger_combo.state(("disabled",))
            self.ai_interval_combo.state(("disabled",))

        # Lock TTS controls
        if self.tts_available:
            # Lock Enable TTS checkbox
            self.tts_check.state(("disabled",))

            # Lock all TTS source checkboxes
            self.tts_source_whisper.state(("disabled",))
            self.tts_source_ai.state(("disabled",))
            self.tts_source_translation.state(("disabled",))

            # Lock TTS output controls
            self.tts_save_check.state(("disabled",))
            self.tts_format_combo.state(("disabled",))
            self.tts_browse_button.state(("disabled",))
            self.tts_clear_button.state(("disabled",))

    def unlock_ui_controls(self):
        """Unlock UI controls after stopping."""
        # Unlock model settings
        self.model_combo.state(("!disabled",))

        # Explicitly remove disabled state before setting readonly
        self.device_combo.state(("!disabled",))
        self.device_combo.state(("readonly",))

        self.autotype_mode.state(("!disabled",))
        self.autotype_mode.state(("readonly",))

        # Unlock translation language dropdowns
        self.source_combo.state(("!disabled",))
        self.source_combo.state(("readonly",))

        self.target_combo.state(("!disabled",))
        self.target_combo.state(("readonly",))

        # Unlock AI settings
        if self.ai_available:
            # Unlock Enable AI checkbox
            self.ai_check.state(("!disabled",))

            # Re-enable based on current state
            translate_only = "selected" in self.ai_translate_only_check.state()
            self.ai_translate_only_check.state(("!disabled",))

            # If Translate Only is selected, keep Translate Output disabled
            if translate_only:
                self.ai_translate_check.state(("disabled",))
            else:
                self.ai_translate_check.state(("!disabled",))

            self.ai_manual_mode_check.state(("!disabled",))

            # Re-apply translate-only logic for task combo
            if translate_only:
                self.ai_persona_combo.state(("disabled",))
            else:
                self.ai_persona_combo.state(("!disabled",))

            self.ai_model_combo.state(("!disabled",))

            # Unlock trigger controls
            self.ai_trigger_combo.state(("!disabled",))
            self.ai_interval_combo.state(("!disabled",))

        # Unlock TTS controls
        if self.tts_available:
            # Unlock Enable TTS checkbox
            self.tts_check.state(("!disabled",))

            # Unlock all TTS source checkboxes
            self.tts_source_whisper.state(("!disabled",))
            self.tts_source_ai.state(("!disabled",))
            self.tts_source_translation.state(("!disabled",))

            # Unlock TTS output controls
            self.tts_save_check.state(("!disabled",))
            self.tts_format_combo.state(("!disabled",))
            self.tts_browse_button.state(("!disabled",))
            self.tts_clear_button.state(("!disabled",))

    def starting(self):
        if self.ready[0] is True:
            self.control_button.config(text="Stop", command=self.stop, state="normal")
            # Lock UI controls when started
            self.lock_ui_controls()
            return
        if self.ready[0] is None:
            if self.error[0]:
                self.status_label.config(text=f"Error: {self.error[0]}")
            self.control_button.config(text="Start", command=self.start, state="normal")
            return
        self.after(100, self.starting)

    def stop(self):
        # Check if already stopped (auto-stop case)
        if self.ready[0] is None:
            # Already stopped - just update UI immediately
            self.autotype_mode_active = "Off"
            self.control_button.config(text="Start", command=self.start, state="normal")
            self.level_bar['value'] = 0
            self.unlock_ui_controls()
            self.finalize_tts_session()
            return

        # Normal stop - signal core thread to stop
        self.autotype_mode_active = "Off"  # Disable autotype when stopping
        self.ready[0] = False
        self.control_button.config(text="Stopping...", command=None, state="disabled")
        self.stopping()

    def stopping(self):
        if self.ready[0] is None:
            self.control_button.config(text="Start", command=self.start, state="normal")
            self.level_bar['value'] = 0

            # Unlock UI controls when stopped
            self.unlock_ui_controls()

            # Finalize TTS session when stopping completes
            self.finalize_tts_session()
            return
        self.after(100, self.stopping)

    def update_level(self):
        if self.ready[0] is None:
            self.level_bar['value'] = 0
            # Check if we need to trigger stopping cleanup (auto-stop case)
            # If button shows "Stop", it means auto-stop happened and we need to update UI
            if self.control_button['text'] == "Stop":
                # Auto-stop detected - trigger stopping cleanup
                self.autotype_mode_active = "Off"  # Disable autotype
                self.control_button.config(text="Start", command=self.start, state="normal")
                self.unlock_ui_controls()
                self.finalize_tts_session()
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

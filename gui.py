#!/usr/bin/env python3


import threading
import tkinter as tk
import tkinter.ttk as ttk

import core
from cmque import PairDeque, Queue
from settings import Settings


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
        self.text_visible = True  # Track text display visibility

        # Set minimum window size - will adjust based on mode
        self.minsize(900, 600)  # Wide for two-column layout

        # Load settings
        self.settings = Settings()

        # Try to load AI configuration
        self.ai_config = None
        self.ai_available = False
        try:
            from ai_config import load_ai_config
            self.ai_config = load_ai_config()
            self.ai_available = self.ai_config is not None
        except Exception as e:
            print(f"AI features not available: {e}")

        # Create frames - two column layout
        self.controls_frame = ttk.Frame(self, padding="5")
        self.ts_text = Text(self, on_new_text=self.on_new_transcription)
        self.tl_text = Text(self)

        # Grid layout: controls in column 0, text panes in column 1
        self.controls_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        self.ts_text.grid(row=0, column=1, sticky="nsew")
        self.tl_text.grid(row=1, column=1, sticky="nsew")

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
        self.hide_text_button.grid(row=row, column=0, sticky="ew", pady=(0, 5))
        row += 1

        # === MODEL SECTION ===
        model_frame = ttk.Frame(self.controls_frame)
        model_frame.grid(row=row, column=0, sticky="ew", pady=(0, 5))
        row += 1

        ttk.Label(model_frame, text="Model:").pack(side="left", padx=(0, 5))
        self.model_combo = ttk.Combobox(model_frame, values=core.models, state="normal", width=15)
        self.model_combo.set("large-v3")
        self.model_combo.pack(side="left", fill="x", expand=True)

        # === CHECKBOXES ===
        checks_frame = ttk.Frame(self.controls_frame)
        checks_frame.grid(row=row, column=0, sticky="w", pady=(0, 5))
        row += 1

        self.vad_check = ttk.Checkbutton(checks_frame, text="VAD", onvalue=True, offvalue=False)
        self.vad_check.state(("!alternate", "selected"))
        self.vad_check.pack(side="left", padx=(0, 10))

        self.para_check = ttk.Checkbutton(checks_frame, text="¶", onvalue=True, offvalue=False)
        self.para_check.state(("!alternate", "selected"))
        self.para_check.pack(side="left", padx=(0, 10))

        self.type_check = ttk.Checkbutton(checks_frame, text="⌨", onvalue=True, offvalue=False)
        self.type_check.state(("!alternate",))
        self.type_check.pack(side="left")

        # === DEVICE ===
        device_frame = ttk.Frame(self.controls_frame)
        device_frame.grid(row=row, column=0, sticky="ew", pady=(0, 5))
        row += 1

        ttk.Label(device_frame, text="Device:").pack(side="left", padx=(0, 5))
        self.device_combo = ttk.Combobox(device_frame, values=core.devices, state="readonly", width=6)
        self.device_combo.current(1)
        self.device_combo.pack(side="left")

        # === MEMORY, PATIENCE, TIMEOUT ===
        params_frame = ttk.Frame(self.controls_frame)
        params_frame.grid(row=row, column=0, sticky="ew", pady=(0, 5))
        row += 1

        ttk.Label(params_frame, text="Mem:").pack(side="left", padx=(0, 2))
        self.memory_spin = ttk.Spinbox(params_frame, from_=1, to=10, increment=1, state="readonly", width=4)
        self.memory_spin.set(3)
        self.memory_spin.pack(side="left", padx=(0, 10))

        ttk.Label(params_frame, text="Pat:").pack(side="left", padx=(0, 2))
        self.patience_spin = ttk.Spinbox(params_frame, from_=1.0, to=20.0, increment=0.5, state="readonly", width=4)
        self.patience_spin.set(5.0)
        self.patience_spin.pack(side="left", padx=(0, 10))

        ttk.Label(params_frame, text="Timeout:").pack(side="left", padx=(0, 2))
        self.timeout_spin = ttk.Spinbox(params_frame, from_=1.0, to=20.0, increment=0.5, state="readonly", width=4)
        self.timeout_spin.set(5.0)
        self.timeout_spin.pack(side="left")

        # === SOURCE & TARGET ===
        lang_frame = ttk.Frame(self.controls_frame)
        lang_frame.grid(row=row, column=0, sticky="ew", pady=(0, 5))
        row += 1

        ttk.Label(lang_frame, text="Src:").pack(side="left", padx=(0, 2))
        self.source_combo = ttk.Combobox(lang_frame, values=["auto"] + core.sources, state="readonly", width=5)
        self.source_combo.current(0)
        self.source_combo.pack(side="left", padx=(0, 10))

        ttk.Label(lang_frame, text="Tgt:").pack(side="left", padx=(0, 2))
        self.target_combo = ttk.Combobox(lang_frame, values=["none"] + core.targets, state="readonly", width=5)
        self.target_combo.current(0)
        self.target_combo.bind("<<ComboboxSelected>>", self.on_target_changed)
        self.target_combo.pack(side="left")

        # === AI CONTROLS ===
        ai_frame = ttk.Frame(self.controls_frame)
        ai_frame.grid(row=row, column=0, sticky="ew", pady=(0, 5))
        row += 1

        self.ai_check = ttk.Checkbutton(ai_frame, text="AI", onvalue=True, offvalue=False)
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

    def toggle_text_display(self):
        """Toggle visibility of text panes."""
        if self.text_visible:
            # MINIMAL MODE: Hide text panes
            self.ts_text.grid_remove()
            self.tl_text.grid_remove()
            self.hide_text_button.config(text="Show Text ▶")
            self.text_visible = False
            # Adjust minimum size for minimal mode (narrow column)
            self.minsize(380, 600)
        else:
            # FULL MODE: Show text panes
            self.ts_text.grid()
            self.tl_text.grid()
            self.hide_text_button.config(text="Hide Text ◀")
            self.text_visible = True
            # Restore minimum size for full mode (two columns)
            self.minsize(900, 600)

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

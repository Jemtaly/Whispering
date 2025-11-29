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

        self.ts_text = Text(self, on_new_text=self.on_new_transcription)
        self.tl_text = Text(self)
        self.top_frame = ttk.Frame(self)
        self.bot_frame = ttk.Frame(self)
        self.ts_text.grid(row=1, column=0, sticky="nsew")
        self.tl_text.grid(row=1, column=1, sticky="nsew")
        self.top_frame.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.bot_frame.grid(row=2, column=0, columnspan=2, sticky="ew")
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)
        self.mic_label = ttk.Label(self.top_frame, text="Mic:")
        self.mic_list = core.get_mic_names()  # List of (index, name) tuples
        mic_display = ["(system default)"] + [name for idx, name in self.mic_list]
        self.mic_combo = ttk.Combobox(self.top_frame, values=mic_display, state="readonly", width=40)
        self.mic_combo.current(0)
        self.mic_button = ttk.Button(self.top_frame, text="↻", width=2, command=self.refresh_mics)
        self.model_label = ttk.Label(self.top_frame, text="Model size or path:")
        self.model_combo = ttk.Combobox(self.top_frame, values=core.models, state="normal")
        self.model_combo.set("large-v3")  # default to large-v3
        self.vad_check = ttk.Checkbutton(self.top_frame, text="VAD", onvalue=True, offvalue=False)
        self.vad_check.state(("!alternate", "selected"))
        self.para_check = ttk.Checkbutton(self.top_frame, text="¶", onvalue=True, offvalue=False)  # Pilcrow symbol for paragraph
        self.para_check.state(("!alternate", "selected"))  # enabled by default
        self.type_check = ttk.Checkbutton(self.top_frame, text="⌨", onvalue=True, offvalue=False)  # Keyboard symbol for auto-type
        self.type_check.state(("!alternate",))  # disabled by default
        self.device_label = ttk.Label(self.top_frame, text="Device:")
        self.device_combo = ttk.Combobox(self.top_frame, values=core.devices, state="readonly", width=6)
        self.device_combo.current(1)  # default to CUDA
        self.memory_label = ttk.Label(self.top_frame, text="Memory:")
        self.memory_spin = ttk.Spinbox(self.top_frame, from_=1, to=10, increment=1, state="readonly")
        self.memory_spin.set(3)
        self.patience_label = ttk.Label(self.top_frame, text="Patience:")
        self.patience_spin = ttk.Spinbox(self.top_frame, from_=1.0, to=20.0, increment=0.5, state="readonly")
        self.patience_spin.set(5.0)
        self.timeout_label = ttk.Label(self.top_frame, text="Timeout:")
        self.timeout_spin = ttk.Spinbox(self.top_frame, from_=1.0, to=20.0, increment=0.5, state="readonly")
        self.timeout_spin.set(5.0)
        self.mic_label.pack(side="left", padx=(5, 5))
        self.mic_combo.pack(side="left", padx=(0, 5))
        self.mic_button.pack(side="left", padx=(0, 5))
        self.model_label.pack(side="left", padx=(5, 5))
        self.model_combo.pack(side="left", padx=(0, 5), fill="x", expand=True)
        self.vad_check.pack(side="left", padx=(0, 5))
        self.para_check.pack(side="left", padx=(0, 5))
        self.type_check.pack(side="left", padx=(0, 5))
        self.device_label.pack(side="left", padx=(5, 5))
        self.device_combo.pack(side="left", padx=(0, 5))
        self.memory_label.pack(side="left", padx=(5, 5))
        self.memory_spin.pack(side="left", padx=(0, 5))
        self.patience_label.pack(side="left", padx=(5, 5))
        self.patience_spin.pack(side="left", padx=(0, 5))
        self.timeout_label.pack(side="left", padx=(5, 5))
        self.timeout_spin.pack(side="left", padx=(0, 5))
        self.source_label = ttk.Label(self.bot_frame, text="Source:")
        self.source_combo = ttk.Combobox(self.bot_frame, values=["auto"] + core.sources, state="readonly")
        self.source_combo.current(0)
        self.target_label = ttk.Label(self.bot_frame, text="Target:")
        self.target_combo = ttk.Combobox(self.bot_frame, values=["none"] + core.targets, state="readonly")
        self.target_combo.current(0)
        self.target_combo.bind("<<ComboboxSelected>>", self.on_target_changed)
        self.prompt_label = ttk.Label(self.bot_frame, text="Prompt:")
        self.prompt_entry = ttk.Entry(self.bot_frame, state="normal")

        # AI Controls
        self.ai_check = ttk.Checkbutton(self.bot_frame, text="AI", onvalue=True, offvalue=False)
        if self.ai_available:
            self.ai_check.state(("!alternate",))  # disabled by default, but available
        else:
            self.ai_check.state(("disabled",))

        self.ai_mode_label = ttk.Label(self.bot_frame, text="Mode:")
        self.ai_mode_combo = ttk.Combobox(self.bot_frame, values=["Proofread", "Translate", "Proofread+Translate"], state="readonly", width=18)
        self.ai_mode_combo.current(0)  # Default to Proofread only
        if not self.ai_available:
            self.ai_mode_combo.state(("disabled",))

        self.ai_model_label = ttk.Label(self.bot_frame, text="Model:")
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

        self.ai_model_combo = ttk.Combobox(self.bot_frame, values=model_names, state="readonly", width=20)
        if model_names:
            self.ai_model_combo.current(default_idx)
        if not self.ai_available:
            self.ai_model_combo.state(("disabled",))

        # AI Processing Interval
        self.ai_interval_label = ttk.Label(self.bot_frame, text="Interval (min):")
        interval_values = [str(i) for i in range(1, 11)]  # 1-10 minutes
        self.ai_interval_combo = ttk.Combobox(self.bot_frame, values=interval_values, state="readonly", width=5)
        self.ai_interval_combo.current(1)  # Default to 2 minutes
        if not self.ai_available:
            self.ai_interval_combo.state(("disabled",))

        self.control_button = ttk.Button(self.bot_frame, text="Start", command=self.start, state="normal")

        self.source_label.pack(side="left", padx=(5, 5))
        self.source_combo.pack(side="left", padx=(0, 5))
        self.target_label.pack(side="left", padx=(5, 5))
        self.target_combo.pack(side="left", padx=(0, 5))
        self.ai_check.pack(side="left", padx=(5, 5))
        self.ai_mode_label.pack(side="left", padx=(0, 2))
        self.ai_mode_combo.pack(side="left", padx=(0, 5))
        self.ai_model_label.pack(side="left", padx=(5, 2))
        self.ai_model_combo.pack(side="left", padx=(0, 5))
        self.ai_interval_label.pack(side="left", padx=(5, 2))
        self.ai_interval_combo.pack(side="left", padx=(0, 5))
        self.prompt_label.pack(side="left", padx=(5, 5))
        self.prompt_entry.pack(side="left", padx=(0, 5), fill="x", expand=True)
        self.control_button.pack(side="left", padx=(5, 5))
        self.level_label = ttk.Label(self.bot_frame, text="Level:")
        self.level_label.pack(side="left", padx=(5, 0))
        self.level_bar = ttk.Progressbar(self.bot_frame, length=100, mode='determinate', maximum=100)
        self.level_bar.pack(side="left", padx=(2, 5))
        self.status_label = ttk.Label(self.bot_frame, text="", foreground="red")
        self.status_label.pack(side="left", padx=(5, 5), fill="x", expand=True)
        self.ready = [None]
        self.error = [None]
        self.level = [0]  # Audio level indicator
        self.autotype_error_shown = False  # Only show error once
    
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

        # Get AI processing interval
        ai_process_interval = int(self.ai_interval_combo.get()) if self.ai_available else 2

        threading.Thread(target=core.proc, args=(index, model, vad, memory, patience, timeout, prompt, source, target, self.ts_text.res_queue, self.tl_text.res_queue, self.ready, device, self.error, self.level, para_detect), kwargs={'ai_processor': ai_processor, 'ai_process_interval': ai_process_interval}, daemon=True).start()
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

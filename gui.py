#!/usr/bin/env python3

import tkinter as tk
import tkinter.ttk as ttk

import core
from que import Queue, Pair


class Text(tk.Text):
    def __init__(self, master):
        super().__init__(master)
        self.res_queue = Queue[Pair]()
        self.tag_config("done", foreground="black")
        self.tag_config("curr", foreground="blue", underline=True)
        self.insert("end", "  ", "done")
        self.record = self.index("end-1c")
        self.see("end")
        self.config(state="disabled")
        self.update()

    def update(self):
        while self.res_queue:
            self.config(state="normal")
            if res := self.res_queue.get():
                done = res.done
                curr = res.curr
                self.delete(self.record, "end")
                self.insert("end", done, "done")
                self.record = self.index("end-1c")
                self.insert("end", curr, "curr")
            else:
                done = self.get(self.record, "end-1c")
                self.delete(self.record, "end")
                self.insert("end", done, "done")
                self.insert("end", "\n", "done")
                self.insert("end", "  ", "done")
                self.record = self.index("end-1c")
            self.see("end")
            self.config(state="disabled")
        self.after(100, self.update)  # avoid busy waiting


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Whispering")
        self.ts_text = Text(self)
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
        self.mic_combo = ttk.Combobox(self.top_frame, values=["default"], state="readonly")
        self.mic_combo.current(0)
        self.mic_button = ttk.Button(self.top_frame, text="Refresh", command=lambda: self.mic_combo.config(values=["default"] + core.get_mic_names()))
        self.model_label = ttk.Label(self.top_frame, text="Model size or path:")
        self.model_combo = ttk.Combobox(self.top_frame, values=core.MODELS, state="normal")
        self.model_combo.set("")
        self.device_label = ttk.Label(self.top_frame, text="Device:")
        self.device_combo = ttk.Combobox(self.top_frame, values=core.DEVICES, state="readonly")
        self.device_combo.current(0)
        self.vad_check = ttk.Checkbutton(self.top_frame, text="VAD", onvalue=True, offvalue=False)
        self.vad_check.state(("!alternate", "selected"))
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
        self.device_label.pack(side="left", padx=(5, 5))
        self.device_combo.pack(side="left", padx=(0, 5))
        self.vad_check.pack(side="left", padx=(0, 5))
        self.memory_label.pack(side="left", padx=(5, 5))
        self.memory_spin.pack(side="left", padx=(0, 5))
        self.patience_label.pack(side="left", padx=(5, 5))
        self.patience_spin.pack(side="left", padx=(0, 5))
        self.timeout_label.pack(side="left", padx=(5, 5))
        self.timeout_spin.pack(side="left", padx=(0, 5))
        self.source_label = ttk.Label(self.bot_frame, text="Source:")
        self.source_combo = ttk.Combobox(self.bot_frame, values=["auto"] + core.LANGS, state="readonly")
        self.source_combo.current(0)
        self.target_label = ttk.Label(self.bot_frame, text="Target:")
        self.target_combo = ttk.Combobox(self.bot_frame, values=["none"] + core.LANGS, state="readonly")
        self.target_combo.current(0)
        self.prompt_label = ttk.Label(self.bot_frame, text="Prompt:")
        self.prompt_entry = ttk.Entry(self.bot_frame, state="normal")
        self.control_button = ttk.Button(self.bot_frame)
        self.on_stopped()
        self.source_label.pack(side="left", padx=(5, 5))
        self.source_combo.pack(side="left", padx=(0, 5))
        self.target_label.pack(side="left", padx=(5, 5))
        self.target_combo.pack(side="left", padx=(0, 5))
        self.prompt_label.pack(side="left", padx=(5, 5))
        self.prompt_entry.pack(side="left", padx=(0, 5), fill="x", expand=True)
        self.control_button.pack(side="left", padx=(5, 5))

    def on_started(self, proc: core.Processor):
        def stop():
            self.control_button.config(text="Stopping...", state="disabled")
            proc.stop(self.on_stopped)

        self.control_button.config(text="Stop", command=stop, state="normal")

    def on_stopped(self, err: Exception | None = None):
        if err:
            print(err)

        def start():
            self.control_button.config(text="Starting...", state="disabled")
            core.start(
                index=None if self.mic_combo.current() == 0 else self.mic_combo.current() - 1,
                model=self.model_combo.get(),
                device=self.device_combo.get(),
                vad=self.vad_check.instate(("selected",)),
                prompts=[self.prompt_entry.get()],
                memory=int(self.memory_spin.get()),
                patience=float(self.patience_spin.get()),
                timeout=float(self.timeout_spin.get()),
                source=None if self.source_combo.get() == "auto" else self.source_combo.get(),
                target=None if self.target_combo.get() == "none" else self.target_combo.get(),
                tsres_queue=self.ts_text.res_queue,
                tlres_queue=self.tl_text.res_queue,
                on_success=self.on_started,
                on_failure=self.on_stopped,
                log_cc_errors=print,
                log_ts_errors=print,
                log_tl_errors=print,
            )

        self.control_button.config(text="Start", command=start, state="normal")


if __name__ == "__main__":
    App().mainloop()

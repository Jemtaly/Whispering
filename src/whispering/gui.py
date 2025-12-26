#!/usr/bin/env python3

import tkinter as tk
import tkinter.ttk as ttk

from whispering.core.utils import MergingQueue, Pair
from whispering.core.interfaces import LANGS
from whispering.core.engine import Processor
from whispering.services.audio.soundcard_impl import SoundcardMicFactory, SoundcardMicManager
from whispering.services.transcription.whisper_impl import MODELS, DEVICES, WhisperTranscriptionFactory
from whispering.services.translation.google_impl import GoogleTranslationFactory


class Text(tk.Text):
    def __init__(self, master):
        super().__init__(master)
        self.res_queue = MergingQueue[Pair]()
        self.tag_config("cnfm", foreground="black")
        self.tag_config("drft", foreground="blue", underline=True)
        self.insert("end", "  ", "cnfm")
        self.boundary = self.index("end-1c")
        self.see("end")
        self.config(state="disabled")
        self.update()

    def update(self):
        while self.res_queue:
            self.config(state="normal")
            if res := self.res_queue.get():
                cnfm = res.cnfm
                drft = res.drft
                self.delete(self.boundary, "end")
                self.insert("end", cnfm, "cnfm")
                self.boundary = self.index("end-1c")
                self.insert("end", drft, "drft")
            else:
                cnfm = self.get(self.boundary, "end-1c")
                self.delete(self.boundary, "end")
                self.insert("end", cnfm, "cnfm")
                self.insert("end", "\n", "cnfm")
                self.insert("end", "  ", "cnfm")
                self.boundary = self.index("end-1c")
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
        self.mic_manager = SoundcardMicManager()
        self.mic_label = ttk.Label(self.top_frame, text="Mic:")
        self.mic_combo = ttk.Combobox(self.top_frame, values=self.mic_manager.list_microphones(), state="readonly")
        self.mic_combo.current(0)
        self.mic_button = ttk.Button(self.top_frame, text="Refresh", command=lambda: self.mic_combo.config(values=self.mic_manager.refresh().list_microphones()))
        self.model_label = ttk.Label(self.top_frame, text="Model size or path:")
        self.model_combo = ttk.Combobox(self.top_frame, values=MODELS, state="normal")
        self.model_combo.set("")
        self.device_label = ttk.Label(self.top_frame, text="Device:")
        self.device_combo = ttk.Combobox(self.top_frame, values=DEVICES, state="readonly")
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
        self.source_combo = ttk.Combobox(self.bot_frame, values=["auto"] + LANGS, state="readonly")
        self.source_combo.current(0)
        self.target_label = ttk.Label(self.bot_frame, text="Target:")
        self.target_combo = ttk.Combobox(self.bot_frame, values=["none"] + LANGS, state="readonly")
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

    def on_started(self, proc: Processor):
        def stop():
            self.control_button.config(text="Stopping...", state="disabled")
            proc.stop()

        self.control_button.config(text="Stop", command=stop, state="normal")

    def on_stopped(self, err: Exception | None = None):
        if err:
            print(err)

        def start():
            self.control_button.config(text="Starting...", state="disabled")
            mic_factory = SoundcardMicFactory(
                mic_id=self.mic_manager.get_microphone_by_index(self.mic_combo.current()),
            )
            ts_factory = WhisperTranscriptionFactory(
                model=self.model_combo.get(),  # type: ignore
                device=self.device_combo.get(),  # type: ignore
                vad=self.vad_check.instate(("selected",)),
                prompts=[self.prompt_entry.get()],
                memory=int(self.memory_spin.get()),
                patience=float(self.patience_spin.get()),
            )
            tl_factory = GoogleTranslationFactory(
                timeout=float(self.timeout_spin.get()),
            )
            Processor.start(
                mic_factory=mic_factory,
                sample_time=0.1,
                ts_factory=ts_factory,
                tl_factory=tl_factory,
                source_lang=None if self.source_combo.get() == "auto" else self.source_combo.get(),  # type: ignore
                target_lang=None if self.target_combo.get() == "none" else self.target_combo.get(),  # type: ignore
                tsres_queue=self.ts_text.res_queue,
                tlres_queue=self.tl_text.res_queue,
                on_failure=self.on_stopped,
                on_success=self.on_started,
                on_stopped=self.on_stopped,
                on_cc_error=print,
                on_ts_error=print,
                on_tl_error=print,
            )

        self.control_button.config(text="Start", command=start, state="normal")


def main() -> None:
    App().mainloop()

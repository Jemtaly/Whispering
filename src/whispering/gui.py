import tkinter as tk
import tkinter.ttk as ttk

from whispering.core.utils import MergingQueue, Pair
from whispering.core.interfaces import LANGS
from whispering.core.engine import STTEngine
from whispering.services.audio.soundcard_impl import (
    SoundcardMicrophoneInfo,
    SoundcardRecordingServiceFactory,
)
from whispering.services.transcription.whisper_impl import (
    MODELS,
    DEVICES,
    WhisperTranscriptionFactory,
)
from whispering.services.translation.google_impl import (
    GoogleTranslationServiceFactory,
)


class Text(tk.Text):
    def __init__(self, master: tk.Misc | None = None):
        super().__init__(master)
        self.result_queue = MergingQueue[Pair]()
        self.tag_config("cnfm", foreground="black")
        self.tag_config("drft", foreground="blue", underline=True)
        self.insert("end", "  ", "cnfm")
        self.boundary = self.index("end-1c")
        self.see("end")
        self.config(state="disabled")
        self.update()

    def update(self):
        while self.result_queue:
            self.config(state="normal")
            if result := self.result_queue.get():
                cnfm = result.cnfm
                drft = result.drft
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
        self.head_frame = ttk.Frame(self)
        self.body_frame = ttk.Frame(self)
        self.foot_frame = ttk.Frame(self)
        self.head_frame.pack(side="top", fill="x")
        self.body_frame.pack(side="top", fill="both", expand=True)
        self.foot_frame.pack(side="top", fill="x")
        self.transc_text = Text(self.body_frame)
        self.transl_text = Text(self.body_frame)
        self.transc_text.pack(side="left", fill="both", expand=True)
        self.transl_text.pack(side="left", fill="both", expand=True)
        self.mic_label = ttk.Label(self.head_frame, text="Mic:")
        self.mic_combo = ttk.Combobox(self.head_frame, state="readonly")
        self.mic_combo_refresh()
        self.mic_button = ttk.Button(self.head_frame, text="Refresh", command=self.mic_combo_refresh)
        self.model_label = ttk.Label(self.head_frame, text="Model size or path:")
        self.model_combo = ttk.Combobox(self.head_frame, values=MODELS, state="normal")
        self.model_combo.set("")
        self.device_label = ttk.Label(self.head_frame, text="Device:")
        self.device_combo = ttk.Combobox(self.head_frame, values=DEVICES, state="readonly")
        self.device_combo.current(0)
        self.vad_check = ttk.Checkbutton(self.head_frame, text="VAD", onvalue=True, offvalue=False)
        self.vad_check.state(("!alternate", "selected"))
        self.memory_label = ttk.Label(self.head_frame, text="Memory:")
        self.memory_spin = ttk.Spinbox(self.head_frame, from_=1, to=10, increment=1, state="readonly")
        self.memory_spin.set(3)
        self.patience_label = ttk.Label(self.head_frame, text="Patience:")
        self.patience_spin = ttk.Spinbox(self.head_frame, from_=1.0, to=20.0, increment=0.5, state="readonly")
        self.patience_spin.set(5.0)
        self.timeout_label = ttk.Label(self.head_frame, text="Timeout:")
        self.timeout_spin = ttk.Spinbox(self.head_frame, from_=1.0, to=20.0, increment=0.5, state="readonly")
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
        self.source_label = ttk.Label(self.foot_frame, text="Source:")
        self.source_combo = ttk.Combobox(self.foot_frame, values=["auto"] + LANGS, state="readonly")
        self.source_combo.current(0)
        self.target_label = ttk.Label(self.foot_frame, text="Target:")
        self.target_combo = ttk.Combobox(self.foot_frame, values=["none"] + LANGS, state="readonly")
        self.target_combo.current(0)
        self.prompt_label = ttk.Label(self.foot_frame, text="Prompt:")
        self.prompt_entry = ttk.Entry(self.foot_frame, state="normal")
        self.control_button = ttk.Button(self.foot_frame)
        self.on_stopped()
        self.source_label.pack(side="left", padx=(5, 5))
        self.source_combo.pack(side="left", padx=(0, 5))
        self.target_label.pack(side="left", padx=(5, 5))
        self.target_combo.pack(side="left", padx=(0, 5))
        self.prompt_label.pack(side="left", padx=(5, 5))
        self.prompt_entry.pack(side="left", padx=(0, 5), fill="x", expand=True)
        self.control_button.pack(side="left", padx=(5, 5))

    def mic_combo_refresh(self):
        self.mics = SoundcardMicrophoneInfo.list_microphones()
        self.mic_combo.config(values=[f"[{mic.kind}] {mic.name}" for mic in self.mics])
        self.mic_combo.current(0)

    def on_started(self, eng: STTEngine):
        def stop():
            self.control_button.config(text="Stopping...", state="disabled")
            eng.stop()

        self.control_button.config(text="Stop", command=stop, state="normal")

    def on_stopped(self, err: Exception | None = None):
        if err:
            print(err)

        def start():
            self.control_button.config(text="Starting...", state="disabled")
            mic_factory = SoundcardRecordingServiceFactory(
                mic_info=self.mics[self.mic_combo.current()],
            )
            transc_factory = WhisperTranscriptionFactory(
                model=self.model_combo.get(),  # type: ignore
                device=self.device_combo.get(),  # type: ignore
                vad=self.vad_check.instate(["selected"]),
                prompts=[self.prompt_entry.get()],
                memory=int(self.memory_spin.get()),
                patience=float(self.patience_spin.get()),
            )
            transl_factory = GoogleTranslationServiceFactory(
                timeout=float(self.timeout_spin.get()),
            )
            STTEngine.start(
                record_factory=mic_factory,
                sample_time=0.1,
                transc_factory=transc_factory,
                transl_factory=transl_factory,
                source_lang=None if self.source_combo.get() == "auto" else self.source_combo.get(),  # type: ignore
                target_lang=None if self.target_combo.get() == "none" else self.target_combo.get(),  # type: ignore
                transc_result_queue=self.transc_text.result_queue,
                transl_result_queue=self.transl_text.result_queue,
                on_failure=self.on_stopped,
                on_success=self.on_started,
                on_stopped=self.on_stopped,
                on_record_error=print,
                on_transc_error=print,
                on_transl_error=print,
            )

        self.control_button.config(text="Start", command=start, state="normal")


def main() -> None:
    App().mainloop()

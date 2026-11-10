import tkinter as tk
import tkinter.ttk as ttk
import time

from threading import Event

from whispering.core.utils import MergingQueue, Pair
from whispering.core.engine import (
    STTEngine,
    RecordingConfig,
    TranscriptionConfig,
    TranslationConfig,
)
from whispering.services.audio.soundcard_impl import (
    SoundcardMicrophoneInfo,
    SoundcardRecordingServiceFactory,
)
from whispering.services.transcription.whisper_impl import (
    WHISPER_MODEL_NAMES,
    WHISPER_DEVICE_NAMES,
    WHISPER_LANGUAGE_CODES,
    WhisperTranscriptionFactory,
)
from whispering.services.translation.google_impl import (
    GOOGLE_SOURCE_LANGUAGE_CODES,
    GOOGLE_TARGET_LANGUAGE_CODES,
    GoogleTranslationServiceFactory,
)


SOURCE_LANGUAGE_CODES = sorted(GOOGLE_SOURCE_LANGUAGE_CODES & WHISPER_LANGUAGE_CODES)
TARGET_LANGUAGE_CODES = sorted(GOOGLE_TARGET_LANGUAGE_CODES)


class Text(tk.Text):
    def __init__(self, master: tk.Misc | None = None):
        super().__init__(master)
        self.tag_config("cnfm", foreground="black")
        self.tag_config("drft", foreground="blue", underline=True)
        self.tag_config("info", foreground="gray")

    def start(self):
        result_queue = MergingQueue[Pair]()
        finished = Event()
        self.config(state="normal")
        ctag = time.strftime("[%H:%M:%S]")
        self.insert("end", ctag, "info")
        self.insert("end", "\n", "info")
        self.insert("end", "  ", "info")
        boundary = self.index("end-1c")
        self.see("end")
        self.config(state="disabled")

        def update():
            nonlocal boundary
            if result_queue:
                result = result_queue.get()
                self.config(state="normal")
                if result is None:
                    self.insert("end", "\n", "info")
                else:
                    cnfm = result.cnfm
                    drft = result.drft
                    self.delete(boundary, "end")
                    self.insert("end", cnfm, "cnfm")
                    boundary = self.index("end-1c")
                    self.insert("end", drft, "drft")
                self.see("end")
                self.config(state="disabled")
                if result is None:
                    finished.set()
                    return
            self.after(100, update)

        self.after(100, update)
        return result_queue, finished.wait


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
        self.model_combo = ttk.Combobox(self.head_frame, values=WHISPER_MODEL_NAMES, state="normal")
        self.model_combo.set("")
        self.device_label = ttk.Label(self.head_frame, text="Device:")
        self.device_combo = ttk.Combobox(self.head_frame, values=WHISPER_DEVICE_NAMES, state="readonly")
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
        self.source_combo = ttk.Combobox(self.foot_frame, values=["auto"] + SOURCE_LANGUAGE_CODES, state="readonly")
        self.source_combo.current(0)
        self.target_label = ttk.Label(self.foot_frame, text="Target:")
        self.target_combo = ttk.Combobox(self.foot_frame, values=["none"] + TARGET_LANGUAGE_CODES, state="readonly")
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
            STTEngine.start(
                record_cfg=RecordingConfig(
                    factory=SoundcardRecordingServiceFactory(
                        mic_info=self.mics[self.mic_combo.current()],
                        sample_time=0.1,
                    ),
                    on_error=print,
                ),
                transc_cfg=TranscriptionConfig(
                    factory=WhisperTranscriptionFactory(
                        model=self.model_combo.get(),  # type: ignore
                        device=self.device_combo.get(),  # type: ignore
                        vad=self.vad_check.instate(["selected"]),
                        prompts=[self.prompt_entry.get()],
                        memory=int(self.memory_spin.get()),
                        patience=float(self.patience_spin.get()),
                    ),
                    result_queue_fn=self.transc_text.start,
                    on_error=print,
                ),
                transl_cfg=TranslationConfig(
                    factory=GoogleTranslationServiceFactory(
                        timeout=float(self.timeout_spin.get()),
                        lang=None
                        if self.target_combo.get() == "none"
                        else self.target_combo.get(),
                    ),
                    result_queue_fn=self.transl_text.start,
                    on_error=print,
                ),
                lang=None
                if self.source_combo.get() == "auto"
                else self.source_combo.get(),
                on_failure=self.on_stopped,
                on_success=self.on_started,
                on_stopped=self.on_stopped,
            )

        self.control_button.config(text="Start", command=start, state="normal")


def main() -> None:
    App().mainloop()

import tkinter as tk
import tkinter.ttk as ttk
import time

from threading import Event
from typing import Callable, Literal

from whispering.core.utils import MergingQueue, Pair
from whispering.core.engine import STTEngine, STEngine
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
    def __init__(self, master: tk.Misc | None = None) -> None:
        super().__init__(master, state="disabled", wrap="word")
        self.tag_config("cnfm", foreground="black")
        self.tag_config("drft", foreground="blue", underline=True)
        self.bind("<Configure>", self.fit_height)
        self.bind("<Map>", self.fit_height)
        self.boundary = "1.0"
        self.queue = MergingQueue[Pair]()

    def fit_height(self, event: tk.Event | None = None) -> None:
        lines = self.count("1.0", "end-1c", "displaylines")
        self.config(height=(lines[0] if lines else 0) + 1)

    def refresh(self) -> Literal["updated", "stopped"] | None:
        if not self.queue:
            return None
        result = self.queue.get()
        if result is None:
            return "stopped"
        self.config(state="normal")
        self.delete(self.boundary, "end")
        self.insert("end", result.cnfm, "cnfm")
        self.boundary = self.index("end-1c")
        self.insert("end", result.drft, "drft")
        self.config(state="disabled")
        self.fit_height()
        return "updated"


class History(tk.Canvas):
    """Scrollable session layout; Text widgets only display the actual transcripts."""

    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master, background="white", highlightthickness=0, yscrollincrement=20)
        self.content = tk.Frame(self, background="white")
        self.content_window = self.create_window(0, 0, window=self.content, anchor="nw")
        self.region: tuple[int, int, int, int] | None = None
        self.bind("<Configure>", self.resize)
        self.content.bind("<Configure>", self.fit_content)
        self.bind_scroll(self)
        self.bind_scroll(self.content)

    def resize(self, event: tk.Event) -> None:
        self.itemconfigure(self.content_window, width=event.width)

    def fit_content(self, event: tk.Event) -> None:
        region = self.bbox("all")
        if region != self.region:
            self.region = region
            self.config(scrollregion=region)
            self.yview_moveto(1)

    def bind_scroll(self, widget: tk.Misc) -> None:
        # Keep Tk's platform-specific event handling, changing only the target.
        for sequence in self.bind_class("TtkScrollable"):
            script = self.bind_class("TtkScrollable", sequence).replace("%W", str(self))
            widget.bind(sequence, f"{script}\nbreak")

    def create_block(self, title: str, columns: int) -> list[Text]:
        block = tk.Frame(self.content, background="white")
        block.pack(fill="x", padx=4, pady=(4, 8))
        heading = tk.Label(block, text=title, foreground="gray", background="white")
        heading.grid(row=0, column=0, columnspan=columns, sticky="w", pady=(0, 4))
        texts = [Text(block) for _ in range(columns)]
        for index, text in enumerate(texts):
            block.columnconfigure(index, weight=1, uniform="text")
            text.config(width=1, height=1)
            text.grid(row=1, column=index, sticky="nsew")
        for widget in (block, heading, *texts):
            self.bind_scroll(widget)
        return texts

    def start_block(self, title: str, columns: int) -> tuple[Callable[[], bool], list[MergingQueue[Pair]]]:
        texts = self.create_block(title, columns)
        finished = Event()

        def update() -> None:
            nonlocal texts
            nexts: list[Text] = []
            for text in texts:
                state = text.refresh()
                if state != "stopped":
                    nexts.append(text)
                if state == "updated":
                    self.after_idle(lambda: self.yview_moveto(1))
            texts = nexts
            if texts:
                self.after(100, update)
            else:
                finished.set()

        self.after(100, update)
        return finished.wait, [text.queue for text in texts]


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
        self.history = History(self.body_frame)
        self.history.pack(fill="both", expand=True)
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

    def on_started(self, stopper: "Callable[[], None]"):
        def stop():
            self.control_button.config(text="Stopping...", state="disabled")
            stopper()

        self.control_button.config(text="Stop", command=stop, state="normal")

    def on_started_with_transl(
        self,
        stopper: "Callable[[], None]",
        source_lang: str | None,
        target_lang: str,
    ):
        self.on_started(stopper)

        source_lang = source_lang or "auto"
        current_time = time.strftime("[%H:%M:%S]")
        title = f"{current_time} {source_lang} -> {target_lang}"
        join, (
            transc_result_queue,
            transl_result_queue,
        ) = self.history.start_block(title, 2)

        def on_stopped():
            join()
            self.on_stopped()

        return (
            on_stopped,
            transc_result_queue,
            transl_result_queue,
        )

    def on_started_without_transl(
        self,
        stopper: "Callable[[], None]",
        source_lang: str | None,
    ):
        self.on_started(stopper)

        source_lang = source_lang or "auto"
        current_time = time.strftime("[%H:%M:%S]")
        title = f"{current_time} {source_lang}"
        join, (
            transc_result_queue,
        ) = self.history.start_block(title, 1)

        def on_stopped():
            join()
            self.on_stopped()

        return (
            on_stopped,
            transc_result_queue,
        )

    def on_stopped(self, err: Exception | None = None):
        if err:
            print(err)

        def start():
            self.control_button.config(text="Starting...", state="disabled")
            record_cfg = SoundcardRecordingServiceFactory(
                mic_info=self.mics[self.mic_combo.current()],
                sample_time=0.1,
            )
            transc_cfg = WhisperTranscriptionFactory(
                model=self.model_combo.get(),  # type: ignore
                device=self.device_combo.get(),  # type: ignore
                vad=self.vad_check.instate(["selected"]),
                prompts=[self.prompt_entry.get()],
                memory=int(self.memory_spin.get()),
                patience=float(self.patience_spin.get()),
            )
            source_lang = None if self.source_combo.get() == "auto" else self.source_combo.get()
            target_lang = None if self.target_combo.get() == "none" else self.target_combo.get()
            if target_lang is None:
                STEngine.start(
                    record_cfg=record_cfg,
                    transc_cfg=transc_cfg,
                    lang=source_lang,
                    on_failure=self.on_stopped,
                    on_success=lambda stopper: self.on_started_without_transl(stopper, source_lang),
                )
            else:
                transl_cfg = GoogleTranslationServiceFactory(
                    timeout=float(self.timeout_spin.get()),
                    lang=target_lang,
                )
                STTEngine.start(
                    record_cfg=record_cfg,
                    transc_cfg=transc_cfg,
                    transl_cfg=transl_cfg,
                    lang=source_lang,
                    on_failure=self.on_stopped,
                    on_success=lambda stopper: self.on_started_with_transl(stopper, source_lang, target_lang),
                )

        self.control_button.config(text="Start", command=start, state="normal")


def main() -> None:
    App().mainloop()

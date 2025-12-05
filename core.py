from collections import deque
from dataclasses import dataclass
from threading import Thread
from typing import Callable, Self

from urllib.parse import quote
import requests

import numpy as np
import soundcard as sc
from faster_whisper import WhisperModel

from que import ConflatingQueue, Pair, Data

import os

os.environ["KMP_DUPLICATE_LIB_OK"] = "True"

LANGS = ["af", "am", "ar", "as", "az", "ba", "be", "bg", "bn", "bo", "br", "bs", "ca", "cs", "cy", "da", "de", "el", "en", "es", "et", "eu", "fa", "fi", "fo", "fr", "gl", "gu", "ha", "haw", "he", "hi", "hr", "ht", "hu", "hy", "id", "is", "it", "ja", "jw", "ka", "kk", "km", "kn", "ko", "la", "lb", "ln", "lo", "lt", "lv", "mg", "mi", "mk", "ml", "mn", "mr", "ms", "mt", "my", "ne", "nl", "nn", "no", "oc", "pa", "pl", "ps", "pt", "ro", "ru", "sa", "sd", "si", "sk", "sl", "sn", "so", "sq", "sr", "su", "sv", "sw", "ta", "te", "tg", "th", "tk", "tl", "tr", "tt", "uk", "ur", "uz", "vi", "yi", "yo", "yue", "zh"]
MODELS = ["tiny", "base", "small", "medium", "large-v1", "large-v2", "large-v3", "large"]
DEVICES = ["auto", "cpu", "cuda"]


class SoundcardMicManager:
    def __init__(self):
        self.microphones = [None, *sc.all_microphones(include_loopback=True)]

    def refresh(self) -> Self:
        self.microphones = [None, *sc.all_microphones(include_loopback=True)]
        return self

    def list_microphones(self) -> list[str]:
        result = []
        for mic in self.microphones:
            if mic is None:
                kind = "default"
                name = "Default Microphone"
            else:
                kind = "loopback" if mic.isloopback else "microphone"
                name = mic.name
            result.append(f"[{kind}] {name}")
        return result

    def get_microphone_by_index(self, index: int) -> str | None:
        mic = self.microphones[index]
        return mic.id if mic is not None else None


class SoundcardMicProcessor:
    def __init__(
        self,
        mic_id: str | None = None,
        sample_chunk: int = 1024,
    ):
        if mic_id is None:
            self.mic = sc.default_microphone()
        else:
            self.mic = sc.get_microphone(id=mic_id, include_loopback=True)
        self.rec = self.mic.recorder(samplerate=16000, channels=self.mic.channels)
        self.sample_chunk = sample_chunk

    def __enter__(self) -> None:
        self.rec.__enter__()

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.rec.__exit__(exc_type, exc_value, traceback)

    def read(self) -> Data:
        audio = self.rec.record(numframes=self.sample_chunk).mean(axis=1)
        return bytearray(audio.tobytes())

    @property
    def sample_rate(self) -> int:
        return self.rec.samplerate

    @property
    def frame_dtype(self) -> np.dtype:
        return np.dtype(np.float32)


class TranscriptionProcessor:
    def __init__(
        self,
        model: str,
        device: str,
        vad: bool,
        lang: str | None,
        prompts: list[str],
        memory: int,
        patience: float,
        sample_rate: int,
        frame_dtype: np.dtype,
    ):
        self.model = WhisperModel(model, device)
        self.vad = vad
        self.lang = lang
        self.prompts = deque(prompts, memory)
        self.window = Data()
        self.patience = patience
        self.sample_rate = sample_rate
        self.frame_dtype = frame_dtype

    def update(self, frame: Data) -> Pair:
        self.window.extend(frame)
        audio = np.frombuffer(bytes(self.window), dtype=self.frame_dtype)
        segments, info = self.model.transcribe(audio, language=self.lang, initial_prompt="".join(self.prompts), vad_filter=self.vad)
        segments = list(segments)
        start = max(len(self.window) // self.frame_dtype.itemsize / self.sample_rate - self.patience, 0.0)
        i = 0
        for segment in segments:
            if segment.end >= start:
                if segment.start < start:
                    start = segment.start
                break
            i += 1
        done_src = "".join(segment.text for segment in segments[:i])
        curr_src = "".join(segment.text for segment in segments[i:])
        self.prompts.extend(segment.text for segment in segments[:i])
        del self.window[: int(start * self.sample_rate) * self.frame_dtype.itemsize]
        return Pair(done_src, curr_src)


@dataclass
class TranslationResult:
    source: str
    target: str


class TranslationProcessor:
    def __init__(
        self,
        source: str | None,
        target: str | None,
        timeout: float,
    ):
        self.source = source
        self.target = target
        self.timeout = timeout
        self.src = ""

    def translate(self, text: str) -> list[TranslationResult]:
        if self.target is None:
            return [TranslationResult(text, "Target language is not specified.")]
        try:
            url = "https://translate.googleapis.com/translate_a/single?client=gtx&sl={}&tl={}&dt=t&q={}".format(self.source or "auto", self.target, quote(text))
            ans = requests.get(url, timeout=self.timeout).json()[0] or []
            return [TranslationResult(s, t) for t, s, *infos in ans]
        except Exception:
            return [TranslationResult(text, "Translation service is unavailable.")]

    def update(self, src: Pair) -> Pair:
        done_src = src.done
        curr_src = src.curr
        if done_src or self.src:
            done_src = self.src + done_src
            done_res = self.translate(done_src)
            self.src = done_res.pop().source
            done_tgt = "".join(r.target for r in done_res)
        else:
            done_tgt = ""
        curr_src = self.src + curr_src
        curr_res = self.translate(curr_src)
        curr_tgt = "".join(r.target for r in curr_res)
        return Pair(done_tgt, curr_tgt)


class Processor:
    def __init__(
        self,
        id: str | None,
        model: str,
        device: str,
        vad: bool,
        prompts: list[str],
        memory: int,
        patience: float,
        timeout: float,
        source: str | None,
        target: str | None,
        tsres_queue: ConflatingQueue[Pair],
        tlres_queue: ConflatingQueue[Pair],
        on_cc_error: Callable[[Exception], None] = lambda _: None,
        on_ts_error: Callable[[Exception], None] = lambda _: None,
        on_tl_error: Callable[[Exception], None] = lambda _: None,
    ):
        self.mic = SoundcardMicProcessor(mic_id=id)
        self.ts_proc = TranscriptionProcessor(
            model=model,
            device=device,
            vad=vad,
            lang=source,
            prompts=prompts,
            memory=memory,
            patience=patience,
            sample_rate=self.mic.sample_rate,
            frame_dtype=self.mic.frame_dtype,
        )
        self.tl_proc = TranslationProcessor(
            source=source,
            target=target,
            timeout=timeout,
        )
        self.is_running = False
        self.tsres_queue = tsres_queue
        self.tlres_queue = tlres_queue
        self.frame_queue = ConflatingQueue[Data]()
        self.ts2tl_queue = ConflatingQueue[Pair]()
        self.on_cc_error = on_cc_error
        self.on_ts_error = on_ts_error
        self.on_tl_error = on_tl_error

    def stop(self):
        self.is_running = False

    def run(self, on_stopped: Callable[[], None]):
        self.is_running = True
        cc_thread = Thread(target=self.cc_task)
        ts_thread = Thread(target=self.ts_task)
        tl_thread = Thread(target=self.tl_task)
        cc_thread.start()
        ts_thread.start()
        tl_thread.start()
        cc_thread.join()
        ts_thread.join()
        tl_thread.join()
        on_stopped()

    def cc_task(self):
        try:
            with self.mic:
                while self.is_running:
                    self.frame_queue.put(Data(self.mic.read()))
        except Exception as err:
            self.on_cc_error(err)
        finally:
            self.frame_queue.put(None)

    def ts_task(self):
        try:
            while frame := self.frame_queue.get():
                src = self.ts_proc.update(frame)
                self.ts2tl_queue.put(src)
                self.tsres_queue.put(src)
        except Exception as err:
            self.on_ts_error(err)
        finally:
            self.ts2tl_queue.put(None)
            self.tsres_queue.put(None)

    def tl_task(self):
        try:
            while ts2tl := self.ts2tl_queue.get():
                tgt = self.tl_proc.update(ts2tl)
                self.tlres_queue.put(tgt)
        except Exception as err:
            self.on_tl_error(err)
        finally:
            self.tlres_queue.put(None)


def start(
    id: str | None,
    model: str,
    device: str,
    vad: bool,
    prompts: list[str],
    memory: int,
    patience: float,
    timeout: float,
    source: str | None,
    target: str | None,
    tsres_queue: ConflatingQueue[Pair],
    tlres_queue: ConflatingQueue[Pair],
    on_failure: Callable[[Exception], None],
    on_success: Callable[[Processor], None],
    on_stopped: Callable[[], None],
    on_cc_error: Callable[[Exception], None] = lambda _: None,
    on_ts_error: Callable[[Exception], None] = lambda _: None,
    on_tl_error: Callable[[Exception], None] = lambda _: None,
):
    def task():
        try:
            proc = Processor(
                id=id,
                model=model,
                device=device,
                vad=vad,
                prompts=prompts,
                memory=memory,
                patience=patience,
                timeout=timeout,
                source=source,
                target=target,
                tsres_queue=tsres_queue,
                tlres_queue=tlres_queue,
                on_cc_error=on_cc_error,
                on_ts_error=on_ts_error,
                on_tl_error=on_tl_error,
            )
        except Exception as err:
            on_failure(err)
        else:
            on_success(proc)
            proc.run(on_stopped)

    Thread(target=task, daemon=True).start()

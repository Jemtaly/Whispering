from collections import deque
from io import BytesIO
from threading import Thread
from urllib.parse import quote

import requests
import speech_recognition as sr
from que import DataQueue, PairQueue
from faster_whisper import WhisperModel

import os

os.environ["KMP_DUPLICATE_LIB_OK"] = "True"

LANGS = ["af", "am", "ar", "as", "az", "ba", "be", "bg", "bn", "bo", "br", "bs", "ca", "cs", "cy", "da", "de", "el", "en", "es", "et", "eu", "fa", "fi", "fo", "fr", "gl", "gu", "ha", "haw", "he", "hi", "hr", "ht", "hu", "hy", "id", "is", "it", "ja", "jw", "ka", "kk", "km", "kn", "ko", "la", "lb", "ln", "lo", "lt", "lv", "mg", "mi", "mk", "ml", "mn", "mr", "ms", "mt", "my", "ne", "nl", "nn", "no", "oc", "pa", "pl", "ps", "pt", "ro", "ru", "sa", "sd", "si", "sk", "sl", "sn", "so", "sq", "sr", "su", "sv", "sw", "ta", "te", "tg", "th", "tk", "tl", "tr", "tt", "uk", "ur", "uz", "vi", "yi", "yo", "yue", "zh"]
MODELS = ["tiny", "base", "small", "medium", "large-v1", "large-v2", "large-v3", "large"]


def get_mic_names() -> list[str]:
    return sr.Microphone.list_microphone_names()


def get_mic_index(mic: str | None) -> int | None:
    if mic is None:
        return None
    for index, name in enumerate(sr.Microphone.list_microphone_names()):
        if mic in name:
            return index
    raise ValueError("Microphone device not found.")


def translate(text: str, source: str | None, target: str | None, timeout: float):
    if target is None:
        return [(text, "Target language is not specified.")]
    try:
        url = "https://translate.googleapis.com/translate_a/single?client=gtx&sl={}&tl={}&dt=t&q={}".format(source or "auto", target, quote(text))
        ans = requests.get(url, timeout=timeout).json()[0] or []
        return [(s, t) for t, s, *infos in ans]
    except Exception:
        return [(text, "Translation service is unavailable.")]


class TranscriptionProcessor:
    def __init__(self, model: str, vad: bool, lang: str | None, prompt: str, memory: int, patience: float, sample_rate: int, sample_width: int):
        self.model = WhisperModel(model)
        self.vad = vad
        self.lang = lang
        self.prompts = deque([prompt], memory)
        self.window = bytearray()
        self.patience = patience
        self.sample_rate = sample_rate
        self.sample_width = sample_width

    def update(self, frame: bytes) -> tuple[str, str]:
        self.window.extend(frame)
        audio = sr.AudioData(self.window, self.sample_rate, self.sample_width)
        with BytesIO(audio.get_wav_data()) as audio_file:
            segments, info = self.model.transcribe(audio_file, language=self.lang, initial_prompt="".join(self.prompts), vad_filter=self.vad)
        segments = list(segments)
        start = max(len(self.window) // self.sample_width / self.sample_rate - self.patience, 0.0)
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
        del self.window[: int(start * self.sample_rate) * self.sample_width]
        return done_src, curr_src


class TranslationProcessor:
    def __init__(self, source: str | None, target: str | None, timeout: float):
        self.source = source
        self.target = target
        self.timeout = timeout
        self.src = ""

    def update(self, done_src: str, curr_src: str) -> tuple[str, str]:
        if done_src or self.src:
            done_src = self.src + done_src
            done_res = translate(done_src, self.source, self.target, self.timeout)
            self.src = done_res.pop()[0]
            done_tgt = "".join(t for s, t in done_res)
        else:
            done_tgt = ""
        curr_src = self.src + curr_src
        curr_res = translate(curr_src, self.source, self.target, self.timeout)
        curr_tgt = "".join(t for s, t in curr_res)
        return done_tgt, curr_tgt


class Processor:
    def __init__(self, index: int | None, model: str, vad: bool, memory: int, patience: float, timeout: float, prompt: str, source: str | None, target: str | None, tsres_queue: PairQueue, tlres_queue: PairQueue, controller: list[bool]):
        self.mic = sr.Microphone(index)
        self.ts_proc = TranscriptionProcessor(model, vad, source, prompt, memory, patience, self.mic.SAMPLE_RATE, self.mic.SAMPLE_WIDTH)
        self.tl_proc = TranslationProcessor(source, target, timeout)
        self.controller = controller
        self.tsres_queue = tsres_queue
        self.tlres_queue = tlres_queue
        self.frame_queue = DataQueue()
        self.ts2tl_queue = PairQueue()

    def cc_task(self):
        try:
            with self.mic:
                while self.controller[0]:
                    self.frame_queue.put(self.mic.stream.read(self.mic.CHUNK))
        finally:
            self.frame_queue.put(None)

    def ts_task(self):
        try:
            while frame := self.frame_queue.get():
                done_src, curr_src = self.ts_proc.update(frame)
                self.ts2tl_queue.put((done_src, curr_src))
                self.tsres_queue.put((done_src, curr_src))
        finally:
            self.ts2tl_queue.put(None)
            self.tsres_queue.put(None)

    def tl_task(self):
        try:
            while ts2tl := self.ts2tl_queue.get():
                done_src, curr_src = ts2tl
                done_tgt, curr_tgt = self.tl_proc.update(done_src, curr_src)
                self.tlres_queue.put((done_tgt, curr_tgt))
        finally:
            self.tlres_queue.put(None)

    def run(self):
        cc_thread = Thread(target=self.cc_task)
        ts_thread = Thread(target=self.ts_task)
        tl_thread = Thread(target=self.tl_task)
        cc_thread.start()
        ts_thread.start()
        tl_thread.start()
        cc_thread.join()
        ts_thread.join()
        tl_thread.join()


def proc(index: int | None, model: str, vad: bool, memory: int, patience: float, timeout: float, prompt: str, source: str | None, target: str | None, tsres_queue: PairQueue, tlres_queue: PairQueue, controller: list[bool], feedback: list[bool | None]):
    def task():
        try:
            proc = Processor(index, model, vad, memory, patience, timeout, prompt, source, target, tsres_queue, tlres_queue, controller)
        except Exception:
            feedback[0] = False
        else:
            feedback[0] = True
            proc.run()
            feedback[0] = False

    Thread(target=task, daemon=True).start()

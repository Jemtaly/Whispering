#!/usr/bin/env python3


import collections
import io
import threading
from urllib.parse import quote

import requests
import speech_recognition as sr
from cmque import DataDeque, PairDeque, Queue
from faster_whisper import WhisperModel


models = ["tiny", "base", "small", "medium", "large-v1", "large-v2", "large-v3", "large"]
sources = ["af", "am", "ar", "as", "az", "ba", "be", "bg", "bn", "bo", "br", "bs", "ca", "cs", "cy", "da", "de", "el", "en", "es", "et", "eu", "fa", "fi", "fo", "fr", "gl", "gu", "ha", "haw", "he", "hi", "hr", "ht", "hu", "hy", "id", "is", "it", "ja", "jw", "ka", "kk", "km", "kn", "ko", "la", "lb", "ln", "lo", "lt", "lv", "mg", "mi", "mk", "ml", "mn", "mr", "ms", "mt", "my", "ne", "nl", "nn", "no", "oc", "pa", "pl", "ps", "pt", "ro", "ru", "sa", "sd", "si", "sk", "sl", "sn", "so", "sq", "sr", "su", "sv", "sw", "ta", "te", "tg", "th", "tk", "tl", "tr", "tt", "uk", "ur", "uz", "vi", "yi", "yo", "yue", "zh"]
targets = ["af", "ak", "am", "ar", "as", "ay", "az", "be", "bg", "bho", "bm", "bn", "bs", "ca", "ceb", "ckb", "co", "cs", "cy", "da", "de", "doi", "dv", "ee", "el", "en", "eo", "es", "et", "eu", "fa", "fi", "fil", "fr", "fy", "ga", "gd", "gl", "gn", "gom", "gu", "ha", "haw", "he", "hi", "hmn", "hr", "ht", "hu", "hy", "id", "ig", "ilo", "is", "it", "ja", "jw", "ka", "kk", "km", "kn", "ko", "kri", "ku", "ky", "la", "lb", "lg", "ln", "lo", "lt", "lus", "lv", "mai", "mg", "mi", "mk", "ml", "mn", "mni-Mtei", "mr", "ms", "mt", "my", "ne", "nl", "no", "nso", "ny", "om", "or", "pa", "pl", "ps", "pt", "qu", "ro", "ru", "rw", "sa", "sd", "si", "sk", "sl", "sm", "sn", "so", "sq", "sr", "st", "su", "sv", "sw", "ta", "te", "tg", "th", "ti", "tk", "tl", "tr", "ts", "tt", "ug", "uk", "ur", "uz", "vi", "xh", "yi", "yo", "zh-CN", "zh-TW", "zu"]


def get_mic_names():
    return sr.Microphone.list_microphone_names()


def get_mic_index(mic):
    if mic is None:
        return None
    for index, name in enumerate(sr.Microphone.list_microphone_names()):
        if mic in name:
            return index
    raise ValueError("Microphone device not found.")


def translate(text, source, target, timeout):
    if target is None:
        return [(text, "Target language is not specified.")]
    try:
        url = "https://translate.googleapis.com/translate_a/single?client=gtx&sl={}&tl={}&dt=t&q={}".format(source or "auto", target, quote(text))
        ans = requests.get(url, timeout=timeout).json()[0] or []
        return [(s, t) for t, s, *infos in ans]
    except:
        return [(text, "Translation service is unavailable.")]


def proc(index, model, vad, memory, patience, timeout, prompt, source, target, tsres_queue, tlres_queue, ready):
    def ts_proc():
        prompts = collections.deque([prompt], memory)
        window = bytearray()
        while frame := frame_queue.get():
            window.extend(frame)
            audio = sr.AudioData(window, mic.SAMPLE_RATE, mic.SAMPLE_WIDTH)
            with io.BytesIO(audio.get_wav_data()) as audio_file:
                segments, info = model.transcribe(audio_file, language=source, initial_prompt="".join(prompts), vad_filter=vad)
            segments = [segment for segment in segments]
            start = max(len(window) // mic.SAMPLE_WIDTH / mic.SAMPLE_RATE - patience, 0.0)
            i = 0
            for segment in segments:
                if segment.end >= start:
                    if segment.start < start:
                        start = segment.start
                    break
                i += 1
            done_src = "".join(segment.text for segment in segments[:i])
            curr_src = "".join(segment.text for segment in segments[i:])
            prompts.extend(segment.text for segment in segments[:i])
            del window[: int(start * mic.SAMPLE_RATE) * mic.SAMPLE_WIDTH]
            ts2tl_queue.put((done_src, curr_src))
            tsres_queue.put((done_src, curr_src))
        ts2tl_queue.put(None)
        tsres_queue.put(None)

    def tl_proc():
        rsrv_src = ""
        while ts2tl := ts2tl_queue.get():
            done_src, curr_src = ts2tl
            if done_src or rsrv_src:
                done_src = rsrv_src + done_src
                done_snt = translate(done_src, source, target, timeout)
                rsrv_src = done_snt.pop()[0]
                done_tgt = "".join(t for s, t in done_snt)
            else:
                done_tgt = ""
            curr_src = rsrv_src + curr_src
            curr_snt = translate(curr_src, source, target, timeout)
            curr_tgt = "".join(t for s, t in curr_snt)
            tlres_queue.put((done_tgt, curr_tgt))
        tlres_queue.put(None)

    try:
        with sr.Microphone(index) as mic:
            model = WhisperModel(model)
            frame_queue = Queue(DataDeque())
            ts2tl_queue = Queue(PairDeque())
            ts_thread = threading.Thread(target=ts_proc)
            tl_thread = threading.Thread(target=tl_proc)
            ts_thread.start()
            tl_thread.start()
            ready[0] = True
            while ready[0]:
                frame_queue.put(mic.stream.read(mic.CHUNK))
            frame_queue.put(None)
            ts_thread.join()
            tl_thread.join()
    finally:
        ready[0] = None

#!/usr/bin/env python3
import threading
import io
import collections
import requests
import speech_recognition as sr
from faster_whisper import WhisperModel
from urllib.parse import quote
from que import DataQueue, PairQueue
models = ['tiny', 'base', 'small', 'medium', 'large-v1', 'large-v2', 'large-v3', 'large']
sources = ['af', 'am', 'ar', 'as', 'az', 'ba', 'be', 'bg', 'bn', 'bo', 'br', 'bs', 'ca', 'cs', 'cy', 'da', 'de', 'el', 'en', 'es', 'et', 'eu', 'fa', 'fi', 'fo', 'fr', 'gl', 'gu', 'ha', 'haw', 'he', 'hi', 'hr', 'ht', 'hu', 'hy', 'id', 'is', 'it', 'ja', 'jw', 'ka', 'kk', 'km', 'kn', 'ko', 'la', 'lb', 'ln', 'lo', 'lt', 'lv', 'mg', 'mi', 'mk', 'ml', 'mn', 'mr', 'ms', 'mt', 'my', 'ne', 'nl', 'nn', 'no', 'oc', 'pa', 'pl', 'ps', 'pt', 'ro', 'ru', 'sa', 'sd', 'si', 'sk', 'sl', 'sn', 'so', 'sq', 'sr', 'su', 'sv', 'sw', 'ta', 'te', 'tg', 'th', 'tk', 'tl', 'tr', 'tt', 'uk', 'ur', 'uz', 'vi', 'yi', 'yo', 'yue', 'zh']
targets = ['af', 'ak', 'am', 'ar', 'as', 'ay', 'az', 'be', 'bg', 'bho', 'bm', 'bn', 'bs', 'ca', 'ceb', 'ckb', 'co', 'cs', 'cy', 'da', 'de', 'doi', 'dv', 'ee', 'el', 'en', 'eo', 'es', 'et', 'eu', 'fa', 'fi', 'fil', 'fr', 'fy', 'ga', 'gd', 'gl', 'gn', 'gom', 'gu', 'ha', 'haw', 'he', 'hi', 'hmn', 'hr', 'ht', 'hu', 'hy', 'id', 'ig', 'ilo', 'is', 'it', 'ja', 'jw', 'ka', 'kk', 'km', 'kn', 'ko', 'kri', 'ku', 'ky', 'la', 'lb', 'lg', 'ln', 'lo', 'lt', 'lus', 'lv', 'mai', 'mg', 'mi', 'mk', 'ml', 'mn', 'mni-Mtei', 'mr', 'ms', 'mt', 'my', 'ne', 'nl', 'no', 'nso', 'ny', 'om', 'or', 'pa', 'pl', 'ps', 'pt', 'qu', 'ro', 'ru', 'rw', 'sa', 'sd', 'si', 'sk', 'sl', 'sm', 'sn', 'so', 'sq', 'sr', 'st', 'su', 'sv', 'sw', 'ta', 'te', 'tg', 'th', 'ti', 'tk', 'tl', 'tr', 'ts', 'tt', 'ug', 'uk', 'ur', 'uz', 'vi', 'xh', 'yi', 'yo', 'zh-CN', 'zh-TW', 'zu']
def translate(text, source, target, timeout):
    if target is None:
        return [(text, 'Target language is not specified.')]
    try:
        url = 'https://translate.googleapis.com/translate_a/single?client=gtx&sl={}&tl={}&dt=t&q={}'.format(source or 'auto', target, quote(text))
        ans = requests.get(url, timeout = timeout).json()[0] or []
        return [(s, t) for t, s, *infos in ans]
    except requests.exceptions.RequestException:
        return [(text, 'Translation service is unavailable.')]
def prepare(mic, model):
    if mic is None:
        index = None
    else:
        for index, name in enumerate(sr.Microphone.list_microphone_names()):
            if mic in name:
                break
        else:
            raise ValueError('Microphone device not found.')
    mic = sr.Microphone(index)
    model = WhisperModel(model)
    return mic, model
def process(mic, model, memory, patience, timeout, prompt, source, target, tsres_queue, tlres_queue, listen_flag):
    frame_queue = DataQueue()
    ts2tl_queue = PairQueue()
    def ts():
        window = bytearray()
        prompts = collections.deque([prompt], memory)
        while frame := frame_queue.get():
            window.extend(frame)
            audio = sr.AudioData(window, mic.SAMPLE_RATE, mic.SAMPLE_WIDTH)
            with io.BytesIO(audio.get_wav_data()) as audio_file:
                segments, info = model.transcribe(audio_file, language = source, initial_prompt = ''.join(prompts), vad_filter = True)
            segments = list(segments)
            start = info.duration - patience
            i = 0
            for segment in segments:
                if segment.end > start:
                    if segment.start < start:
                        start = segment.start
                    break
                i += 1
            done_src = ''.join(segment.text for segment in segments[:i])
            curr_src = ''.join(segment.text for segment in segments[i:])
            window = window[max(0, int(start * mic.SAMPLE_RATE) * mic.SAMPLE_WIDTH):]
            prompts.extend(segment.text for segment in segments[:i])
            ts2tl_queue.put((done_src, curr_src))
            tsres_queue.put((done_src, curr_src))
        ts2tl_queue.put(None)
        tsres_queue.put(None)
    def tl():
        rsrv_src = ''
        while ts2tl := ts2tl_queue.get():
            done_src, curr_src = ts2tl
            if done_src or rsrv_src:
                done_src = rsrv_src + done_src
                done_snt = translate(done_src, source, target, timeout)
                rsrv_src = done_snt.pop(-1)[0]
                done_tgt = ''.join(t for s, t in done_snt)
            else:
                done_tgt = ''
            curr_src = rsrv_src + curr_src
            curr_snt = translate(curr_src, source, target, timeout)
            curr_tgt = ''.join(t for s, t in curr_snt)
            tlres_queue.put((done_tgt, curr_tgt))
        tlres_queue.put(None)
    ts_thread = threading.Thread(target = ts)
    tl_thread = threading.Thread(target = tl)
    ts_thread.start()
    tl_thread.start()
    with mic:
        while listen_flag[0]:
            frame_queue.put(mic.stream.read(mic.CHUNK))
    frame_queue.put(None)
    ts_thread.join()
    tl_thread.join()

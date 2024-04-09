#!/usr/bin/env python3
import threading
import io
import collections
import argparse
import requests
import speech_recognition as sr
from faster_whisper import WhisperModel
from urllib.parse import quote
from que import DataQueue, PairQueue
def translate(text, source, target, timeout):
    try:
        url = 'https://translate.googleapis.com/translate_a/single?client=gtx&sl={}&tl={}&dt=t&q={}'.format(source or 'auto', target, quote(text))
        ans = requests.get(url, timeout = timeout).json()[0] or []
        return [(s, t) for t, s, *infos in ans]
    except:
        return [(text, 'Cannot connect to the translation service.')]
def repeat(repeat_flag, listen_flag, tsres_queue, tlres_queue, model, mic, prompt, memory, patience, source, target, timeout):
    frame_queue = DataQueue()
    ts2tl_queue = PairQueue()
    def ts():
        window = bytearray()
        prompts = collections.deque([] if prompt is None else [prompt], memory or None)
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
        tsres_queue.put(None)
        ts2tl_queue.put(None)
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
    listen = False
    with mic:
        while repeat_flag[0]:
            if not listen and listen_flag[0]:
                ts_thread = threading.Thread(target = ts)
                tl_thread = threading.Thread(target = tl)
                ts_thread.start()
                tl_thread.start()
            if listen and not listen_flag[0]:
                frame_queue.put(None)
                ts_thread.join()
                tl_thread.join()
            listen = listen_flag[0]
            chunk = mic.stream.read(mic.CHUNK)
            if listen:
                frame_queue.put(chunk)
    if listen:
        frame_queue.put(None)
        ts_thread.join()
        tl_thread.join()
def main():
    parser = argparse.ArgumentParser(description = 'Transcribe and translate speech in real-time.')
    parser.add_argument('--model', type = str, choices = ['tiny', 'base', 'small', 'medium', 'large'], default = 'base', help = 'size of the model to use')
    parser.add_argument('--mic', type = str, default = None, help = 'microphone device name')
    parser.add_argument('--prompt', type = str, default = None, help = 'initial prompt for the first segment of each paragraph')
    parser.add_argument('--memory', type = int, default = 3, help = 'maximum number of previous segments to be used as prompt for audio in the transcribing window')
    parser.add_argument('--patience', type = float, default = 5.0, help = 'minimum time to wait for subsequent speech before move a completed segment out of the transcribing window')
    parser.add_argument('--source', type = str, default = None, help = 'source language for translation, auto-detect if not specified')
    parser.add_argument('--target', type = str, default = 'en', help = 'target language for translation, English by default')
    parser.add_argument('--timeout', type = float, default = None, help = 'timeout for the translation service')
    parser.add_argument('--tui', action = 'store_true', help = 'use text-based user interface (curses) instead of graphical user interface (tkinter)')
    args = parser.parse_args()
    if args.mic is None:
        index = None
    else:
        for index, name in enumerate(sr.Microphone.list_microphone_names()):
            if args.mic in name:
                break
        else:
            print('No such microphone device, fallback to default.')
            index = None
    mic = sr.Microphone(index)
    model = WhisperModel(args.model)
    repeat_flag = [True]
    listen_flag = [False]
    tsres_queue = PairQueue()
    tlres_queue = PairQueue()
    repeat_thread = threading.Thread(target = repeat, args = (repeat_flag, listen_flag, tsres_queue, tlres_queue, model, mic, args.prompt, args.memory, args.patience, args.source, args.target, args.timeout))
    repeat_thread.start()
    __import__('tui' if args.tui else 'gui').show(listen_flag, tsres_queue, tlres_queue)
    repeat_flag[0] = False
    repeat_thread.join()
if __name__ == '__main__':
    main()

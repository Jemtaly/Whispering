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
def transcribe(size, device, latency, patience, flush, memory, prompt, rumination, source, target, timeout, tui):
    model = WhisperModel(size)
    recognizer = sr.Recognizer()
    mic = sr.Microphone(device)
    listen_flag = [True]
    frame_queue = DataQueue()
    ts2tl_queue = PairQueue()
    tsres_queue = PairQueue()
    tlres_queue = PairQueue()
    def listen():
        frame_queue.put(True) # initialize
        with mic:
            while listen_flag[0]:
                try:
                    audio = recognizer.listen(mic, timeout = patience, phrase_time_limit = latency)
                except sr.WaitTimeoutError:
                    if flush or rumination <= 0:
                        frame_queue.put(True) # flush
                else:
                    frame_queue.put(audio.frame_data)
        frame_queue.put(False) # finalize
    def transc():
        while frame := frame_queue.get():
            if frame is True:
                window = bytearray()
                prompts = collections.deque([] if prompt is None else [prompt], memory or None)
                ts2tl_queue.put(True)
                tsres_queue.put(True)
                continue
            window.extend(frame)
            audio = sr.AudioData(window, mic.SAMPLE_RATE, mic.SAMPLE_WIDTH)
            with io.BytesIO(audio.get_wav_data()) as audio_file:
                segments, info = model.transcribe(audio_file, language = source, initial_prompt = ''.join(prompts))
            segments = list(segments)
            if len(segments) > rumination > 0:
                done_src = ''.join(segment.text for segment in segments[:-rumination])
                curr_src = ''.join(segment.text for segment in segments[-rumination:])
                window = window[int(segments[-rumination - 1].end * mic.SAMPLE_WIDTH * mic.SAMPLE_RATE):]
                prompts.extend(segment.text for segment in segments[-rumination:])
            else:
                done_src = ''
                curr_src = ''.join(segment.text for segment in segments)
            ts2tl_queue.put((done_src, curr_src))
            tsres_queue.put((done_src, curr_src))
        ts2tl_queue.put(False)
    def transl():
        while ts2tl := ts2tl_queue.get():
            if ts2tl is True:
                rsrv_src = ''
                tlres_queue.put(True)
                continue
            done_src, curr_src = ts2tl
            if done_src or rsrv_src:
                done_src = rsrv_src + done_src
                done_snt = translate(done_src, source, target, timeout)
                rsrv_src = done_snt[-1][0]
                curr_src = rsrv_src + curr_src
                curr_snt = translate(curr_src, source, target, timeout)
                temp_src = curr_snt[0][0]
                if len(curr_snt) > 1 and temp_src == rsrv_src:
                    curr_snt.pop(0)
                    rsrv_src = ''
                else:
                    done_snt.pop(-1)
                done_tgt = ''.join(t for s, t in done_snt)
                curr_tgt = ''.join(t for s, t in curr_snt)
            else:
                curr_snt = translate(curr_src, source, target, timeout)
                done_tgt = ''
                curr_tgt = ''.join(t for s, t in curr_snt)
            tlres_queue.put((done_tgt, curr_tgt))
    listen_thread = threading.Thread(target = listen, daemon = True)
    transc_thread = threading.Thread(target = transc, daemon = True)
    transl_thread = threading.Thread(target = transl, daemon = True)
    listen_thread.start()
    transc_thread.start()
    transl_thread.start()
    __import__('tui' if tui else 'gui').show(tsres_queue, tlres_queue)
    listen_flag[0] = False
    listen_thread.join()
    transc_thread.join()
    transl_thread.join()
def main():
    parser = argparse.ArgumentParser(description = 'Transcribe and translate speech in real-time.')
    parser.add_argument('--size', type = str, choices = ['tiny', 'base', 'small', 'medium', 'large'], default = 'base', help = 'size of the model to use')
    parser.add_argument('--device', type = str, default = None, help = 'microphone device name')
    parser.add_argument('--latency', type = float, default = 1.0, help = 'latency between speech and transcription')
    parser.add_argument('--patience', type = float, default = 1.0, help = 'time to wait for speech before a pause is detected')
    parser.add_argument('--flush', action = 'store_true', help = 'flush the iteration window, reset the prompt and start a new paragraph after a pause')
    parser.add_argument('--memory', action = 'store_true', type = int, default = 3, help = 'maximum number of completed segments used as prompt for the next segment, 0 for unlimited')
    parser.add_argument('--prompt', type = str, default = None, help = 'initial prompt for the first segment of each paragraph')
    parser.add_argument('--rumination', type = int, default = 1, help = 'maximum number of segments retained in the iteration window, 0 for unlimited (and flush on pause will be forcibly enabled)')
    parser.add_argument('--source', type = str, default = None, help = 'source language for translation, auto-detect if not specified')
    parser.add_argument('--target', type = str, default = 'en', help = 'target language for translation, English by default')
    parser.add_argument('--timeout', type = float, default = None, help = 'timeout for the translation service')
    parser.add_argument('--tui', action = 'store_true', help = 'use text-based user interface (curses) instead of graphical user interface (tkinter)')
    args = parser.parse_args()
    if args.device is not None:
        for device, name in enumerate(sr.Microphone.list_microphone_names()):
            if args.device in name:
                args.device = device
                break
        else:
            print('No such microphone device, fallback to default.')
            args.device = None
    transcribe(args.size, args.device, args.latency, args.patience, args.flush, args.amnesia, args.prompt, args.rumination, args.source, args.target, args.timeout, args.tui)
if __name__ == '__main__':
    main()

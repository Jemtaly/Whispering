#!/usr/bin/env python3
import queue
import threading
import collections
import io
import argparse
import requests
import speech_recognition as sr
from faster_whisper import WhisperModel
from urllib.parse import quote
class Queue:
    def __init__(self):
        self.queue = collections.deque()
        self.cond = threading.Condition()
    def put(self, item):
        with self.cond:
            if self.queue and isinstance(self.queue[-1], bytes) and isinstance(item, bytes):
                self.queue[-1] += item
            else:
                self.queue.append(item)
            self.cond.notify()
    def get(self):
        with self.cond:
            while not self.queue:
                self.cond.wait()
            return self.queue.popleft()
def translate(text, source, target):
    try:
        url = 'https://translate.googleapis.com/translate_a/single?client=gtx&sl={}&tl={}&dt=t&q={}'.format(source, target, quote(text))
        ans = requests.get(url).json()[0] or []
        return [(s, t) for t, s, *infos in ans]
    except:
        return [(text, 'Translation service is unavailable.')]
def transcribe(size, device, latency, patience, flush, amnesia, prompt, deliberation, source, target, tui):
    model = WhisperModel(size)
    recognizer = sr.Recognizer()
    mic = sr.Microphone(device)
    listen_flag = [True]
    frame_queue = Queue()
    ts2tl_queue = queue.Queue()
    tsres_queue = queue.Queue()
    tlres_queue = queue.Queue()
    def listen():
        frame_queue.put(True) # initialize
        with mic:
            while listen_flag[0]:
                try:
                    audio = recognizer.listen(mic, timeout = patience, phrase_time_limit = latency)
                except sr.WaitTimeoutError:
                    if flush:
                        frame_queue.put(True)
                else:
                    frame_queue.put(audio.frame_data)
        frame_queue.put(False) # finalize
    def ts_fun():
        while frame := frame_queue.get():
            if frame is True:
                window = bytearray()
                prev_src = prompt
                ts2tl_queue.put(True)
                tsres_queue.put(True)
                continue
            window.extend(frame)
            audio = sr.AudioData(window, mic.SAMPLE_RATE, mic.SAMPLE_WIDTH)
            with io.BytesIO(audio.get_wav_data()) as audio_file:
                segments, info = model.transcribe(audio_file, language = source, initial_prompt = prev_src)
            segments = list(segments)
            if len(segments) > deliberation:
                done_src = ''.join(segment.text for segment in segments[:-deliberation])
                curr_src = ''.join(segment.text for segment in segments[-deliberation:])
                window = window[int(segments[-deliberation - 1].end * mic.SAMPLE_WIDTH * mic.SAMPLE_RATE):]
                prev_src = segments[-deliberation - 1].text if amnesia else prev_src + done_src
            else:
                done_src = ''
                curr_src = ''.join(segment.text for segment in segments)
            ts2tl_queue.put((done_src, curr_src))
            tsres_queue.put((done_src, curr_src))
        ts2tl_queue.put(False)
    def tl_fun():
        while ts2tl := ts2tl_queue.get():
            if ts2tl is True:
                rsrv_src = ''
                tlres_queue.put(True)
                continue
            done_src, curr_src = ts2tl
            if done_src:
                done_src = rsrv_src + done_src
                done_res = translate(done_src, source or 'auto', target)
                rsrv_src = done_res[-1][1]
                curr_src = rsrv_src + curr_src
                curr_res = translate(curr_src, source or 'auto', target)
                comp_src = curr_res[0][1]
                if comp_src == rsrv_src:
                    curr_res.pop(0)
                    rsrv_src = ''
                else:
                    done_res.pop(-1)
                done_tgt = ''.join(t for s, t in done_res)
                curr_tgt = ''.join(t for s, t in curr_res)
            else:
                curr_src = rsrv_src + curr_src
                curr_res = translate(curr_src, source or 'auto', target)
                done_tgt = ''
                curr_tgt = ''.join(t for s, t in curr_res)
            tlres_queue.put((done_tgt, curr_tgt))
    listen_thread = threading.Thread(target = listen, daemon = True)
    ts_fun_thread = threading.Thread(target = ts_fun, daemon = True)
    tl_fun_thread = threading.Thread(target = tl_fun, daemon = True)
    listen_thread.start()
    ts_fun_thread.start()
    tl_fun_thread.start()
    __import__('tui' if tui else 'gui').show(tsres_queue, tlres_queue)
    listen_flag[0] = False
    listen_thread.join()
    ts_fun_thread.join()
    tl_fun_thread.join()
def main():
    parser = argparse.ArgumentParser(description = 'Transcribe and translate speech in real-time.')
    parser.add_argument('--size', type = str, choices = ['tiny', 'base', 'small', 'medium', 'large'], default = 'base', help = 'size of the model to use')
    parser.add_argument('--device', type = str, default = None, help = 'microphone device name')
    parser.add_argument('--latency', type = float, default = 1.0, help = 'latency between speech and transcription')
    parser.add_argument('--patience', type = float, default = 1.0, help = 'maximum time to wait for speech before assuming a pause')
    parser.add_argument('--flush', action = 'store_true', help = 'flush the transcribing window, reset the prompt and start a new paragraph after each pause')
    parser.add_argument('--amnesia', action = 'store_true', help = 'only use the last segment instead of the whole paragraph as the prompt for the next segment')
    parser.add_argument('--prompt', type = str, default = None, help = 'initial prompt for the first segment')
    parser.add_argument('--deliberation', type = int, default = 1, choices = range(1, 4), help = 'maximum number of segments to keep in the transcribing window')
    parser.add_argument('--source', type = str, default = None, help = 'source language for translation')
    parser.add_argument('--target', type = str, default = 'en', help = 'target language for translation')
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
    if not args.amnesia and args.prompt is None:
        args.prompt = ''
    transcribe(args.size, args.device, args.latency, args.patience, args.flush, args.amnesia, args.prompt, args.deliberation, args.source, args.target, args.tui)
if __name__ == '__main__':
    main()

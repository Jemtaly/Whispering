import queue
import threading
import collections
import tkinter as tk
import io
import speech_recognition as sr
from faster_whisper import WhisperModel
from urllib.parse import quote
import requests
import argparse
def translate(text, source, target):
    url = 'https://translate.googleapis.com/translate_a/single?client=gtx&sl={}&tl={}&dt=t&q={}'.format(source, target, quote(text))
    ans = requests.get(url).json()[0] or []
    return [(t, s) for t, s, *infos in ans]
class Text(tk.Text):
    def __init__(self, master, res_queue):
        super().__init__(master)
        self.tag_config('done', foreground = 'black')
        self.tag_config('curr', foreground = 'blue')
        self.insert(tk.END, '  ', 'done')
        self.record = self.index('end-1c')
        self.config(state = tk.DISABLED)
        self.res_queue = res_queue
        self.after(1, self.update)
    def update(self):
        while not self.res_queue.empty():
            res = self.res_queue.get()
            self.config(state = tk.NORMAL)
            if res is not True:
                done_str, curr_str = res
                self.delete(self.record, tk.END)
                if done_str is not None:
                    self.insert(tk.END, done_str, 'done')
                    self.record = self.index('end-1c')
                self.insert(tk.END, curr_str, 'curr')
            elif self.index('end-1c').split('.')[1] != '2':
                done_str = self.get(self.record, tk.END).rstrip('\n') + '\n'
                self.delete(self.record, tk.END)
                self.insert(tk.END, done_str, 'done')
                self.insert(tk.END, '  ', 'done')
                self.record = self.index('end-1c')
            self.see(tk.END)
            self.config(state = tk.DISABLED)
        self.after(1, self.update)
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
def transcribe(size, device, latency, patience, eager, amnesia, prompt, attension, source, target):
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
                    if eager:
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
            if len(segments) > attension:
                done_src = ''.join(segment.text for segment in segments[:-attension])
                curr_src = ''.join(segment.text for segment in segments[-attension:])
                window = window[int(segments[-attension].start * mic.SAMPLE_WIDTH * mic.SAMPLE_RATE):]
                prev_src = segments[-attension - 1].text if amnesia else prev_src + done_src
            else:
                done_src = None
                curr_src = ''.join(segment.text for segment in segments)
            ts2tl_queue.put((done_src, curr_src))
            tsres_queue.put((done_src, curr_src))
        ts2tl_queue.put(False)
    def tl_fun():
        while ts2tl := ts2tl_queue.get():
            if ts2tl is True:
                pref_src = ''
                tlres_queue.put(True)
                continue
            done_src, curr_src = ts2tl
            if done_src is not None:
                done_src = pref_src + done_src
                full_src = done_src + curr_src
                done_res = translate(done_src, source or 'auto', target)
                full_res = translate(full_src, source or 'auto', target)
                done_len = len(done_res) - 1
                if done_res[done_len][1] == full_res[done_len][1]:
                    done_len += 1
                    pref_src = ''
                else:
                    pref_src = done_res[done_len][1]
                done_tgt = ''.join(t for t, s in full_res[:done_len])
                curr_tgt = ''.join(t for t, s in full_res[done_len:])
            else:
                curr_src = pref_src + curr_src
                curr_res = translate(curr_src, source or 'auto', target)
                done_tgt = None
                curr_tgt = ''.join(t for t, s in curr_res)
            tlres_queue.put((done_tgt, curr_tgt))
    listen_thread = threading.Thread(target = listen, daemon = True)
    ts_fun_thread = threading.Thread(target = ts_fun, daemon = True)
    tl_fun_thread = threading.Thread(target = tl_fun, daemon = True)
    listen_thread.start()
    ts_fun_thread.start()
    tl_fun_thread.start()
    root = tk.Tk()
    Text(root, tsres_queue).pack(expand = True, fill = 'both', side = 'left')
    Text(root, tlres_queue).pack(expand = True, fill = 'both', side = 'right')
    root.mainloop()
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
    parser.add_argument('--eager', action = 'store_true', help = 'consider all segments in the transcribing window as finished once there is a pause')
    parser.add_argument('--amnesia', action = 'store_true', help = 'only use the last segment as the prompt for the next segment')
    parser.add_argument('--prompt', type = str, default = None, help = 'initial prompt for the first segment')
    parser.add_argument('--attension', type = int, default = 2, choices = range(1, 6), help = 'maximum number of segments to consider for transcription')
    parser.add_argument('--source', type = str, default = None, help = 'source language for translation')
    parser.add_argument('--target', type = str, default = 'en', help = 'target language for translation')
    args = parser.parse_args()
    if args.device is not None:
        for device, name in enumerate(sr.Microphone.list_microphone_names()):
            if args.device in name:
                args.device = device
                break
        else:
            print('No such device, fallback to default.')
            args.device = None
    if not args.amnesia and args.prompt is None:
        args.prompt = ''
    transcribe(args.size, args.device, args.latency, args.patience, args.eager, args.amnesia, args.prompt, args.attension, args.source, args.target)
if __name__ == '__main__':
    main()

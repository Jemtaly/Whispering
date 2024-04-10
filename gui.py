#!/usr/bin/env python3
import tkinter as tk
import tkinter.ttk as ttk
import threading
import argparse
import core
from que import PairQueue
class Text(tk.Text):
    def __init__(self, master):
        super().__init__(master)
        self.res_queue = PairQueue()
        self.tag_config('done', foreground = 'black')
        self.tag_config('curr', foreground = 'blue', underline = True)
        self.insert('end', '  ', 'done')
        self.record = self.index('end-1c')
        self.start = True
        self.see('end')
        self.config(state = 'disabled')
        self.update()
    def update(self):
        while not self.res_queue.empty():
            self.config(state = 'normal')
            if res := self.res_queue.get():
                done, curr = res
                self.delete(self.record, 'end')
                self.insert('end', done, 'done')
                self.record = self.index('end-1c')
                self.insert('end', curr, 'curr')
                self.start = False
            elif self.start is False:
                done = self.get(self.record, 'end-1c')
                self.delete(self.record, 'end')
                self.insert('end', done, 'done')
                self.insert('end', '\n', 'done')
                self.insert('end', '  ', 'done')
                self.record = self.index('end-1c')
                self.start = True
            self.see('end')
            self.config(state = 'disabled')
        self.after(100, self.update) # avoid busy waiting
class Show(tk.Tk):
    def __init__(self, mic, model, memory, patience, timeout):
        super().__init__()
        self.title('Whispering')
        self.frame = ttk.Frame(self)
        self.frame.grid(row = 0, column = 0, columnspan = 2, sticky = 'ew')
        self.prompt_frame = ttk.Frame(self.frame)
        self.prompt_label = ttk.Label(self.prompt_frame, text = 'Prompt: ')
        self.prompt_entry = ttk.Entry(self.prompt_frame)
        self.prompt_label.pack(side = 'left')
        self.prompt_entry.pack(side = 'left', fill = 'x', expand = True)
        self.source_frame = ttk.Frame(self.frame)
        self.source_label = ttk.Label(self.source_frame, text = 'Source: ')
        self.source_combo = ttk.Combobox(self.source_frame, values = ['auto'] + core.source_langs)
        self.source_combo.current(0)
        self.source_label.pack(side = 'left')
        self.source_combo.pack(side = 'left')
        self.target_frame = ttk.Frame(self.frame)
        self.target_label = ttk.Label(self.target_frame, text = 'Target: ')
        self.target_combo = ttk.Combobox(self.target_frame, values = ['none'] + core.target_langs)
        self.target_combo.current(0)
        self.target_label.pack(side = 'left')
        self.target_combo.pack(side = 'left')
        self.state_button = ttk.Button(self.frame)
        self.prompt_frame.pack(side = 'left', padx = 5, fill = 'x', expand = True)
        self.source_frame.pack(side = 'left', padx = 5)
        self.target_frame.pack(side = 'left', padx = 5)
        self.state_button.pack(side = 'left', padx = 5)
        self.frame.columnconfigure(0, weight = 1)
        self.ts_text = Text(self)
        self.tl_text = Text(self)
        self.ts_text.grid(row = 1, column = 0, sticky = 'nsew')
        self.tl_text.grid(row = 1, column = 1, sticky = 'nsew')
        self.columnconfigure(0, weight = 1)
        self.columnconfigure(1, weight = 1)
        self.rowconfigure(1, weight = 1)
        self.mic, self.model = core.prepare(mic, model)
        self.memory = memory
        self.patience = patience
        self.timeout = timeout
        self.listen_flag = [False]
        self.state_button.config(text = 'Listen', command = self.change)
        self.prompt_entry.config(state = 'normal')
        self.source_combo.config(state = 'readonly')
        self.target_combo.config(state = 'readonly')
    def change(self):
        if self.listen_flag[0]:
            self.listen_flag[0] = False
            self.thread.join()
            del self.thread
            self.state_button.config(text = 'Listen')
            self.prompt_entry.config(state = 'normal')
            self.source_combo.config(state = 'readonly')
            self.target_combo.config(state = 'readonly')
        else:
            self.listen_flag[0] = True
            prompt = self.prompt_entry.get()
            source = None if self.source_combo.get() == 'auto' else self.source_combo.get()
            target = None if self.target_combo.get() == 'none' else self.target_combo.get()
            self.thread = threading.Thread(target = core.process, args = (self.mic, self.model, self.memory, self.patience, self.timeout, prompt, source, target, self.ts_text.res_queue, self.tl_text.res_queue, self.listen_flag), daemon = True)
            self.thread.start()
            self.state_button.config(text = 'Pause')
            self.prompt_entry.config(state = 'disabled')
            self.source_combo.config(state = 'disabled')
            self.target_combo.config(state = 'disabled')
def main():
    parser = argparse.ArgumentParser(description = 'Transcribe and translate speech in real-time.')
    parser.add_argument('--mic', type = str, default = None, help = 'microphone device name')
    parser.add_argument('--model', type = str, choices = core.models, default = 'base', help = 'size of the model to use')
    parser.add_argument('--memory', type = int, default = 3, help = 'maximum number of previous segments to be used as prompt for audio in the transcribing window')
    parser.add_argument('--patience', type = float, default = 5.0, help = 'minimum time to wait for subsequent speech before move a completed segment out of the transcribing window')
    parser.add_argument('--timeout', type = float, default = 5.0, help = 'timeout for the translation service')
    args = parser.parse_args()
    Show(args.mic, args.model, args.memory, args.patience, args.timeout).mainloop()
if __name__ == '__main__':
    main()

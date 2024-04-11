#!/usr/bin/env python3
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import messagebox
import threading
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
            else:
                print('done')
                done = self.get(self.record, 'end-1c')
                self.delete(self.record, 'end')
                self.insert('end', done, 'done')
                self.insert('end', '\n', 'done')
                self.insert('end', '  ', 'done')
                self.record = self.index('end-1c')
            self.see('end')
            self.config(state = 'disabled')
        self.after(100, self.update) # avoid busy waiting
class Show(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Whispering')
        self.top_frame = ttk.Frame(self)
        self.top_frame.grid(row = 0, column = 0, columnspan = 2, sticky = 'ew')
        self.top_frame.columnconfigure(0, weight = 1)
        self.ts_text = Text(self)
        self.tl_text = Text(self)
        self.ts_text.grid(row = 1, column = 0, sticky = 'nsew')
        self.tl_text.grid(row = 1, column = 1, sticky = 'nsew')
        self.bot_frame = ttk.Frame(self)
        self.bot_frame.grid(row = 2, column = 0, columnspan = 2, sticky = 'ew')
        self.bot_frame.columnconfigure(0, weight = 1)
        self.columnconfigure(0, weight = 1)
        self.columnconfigure(1, weight = 1)
        self.rowconfigure(1, weight = 1)
        self.mic_frame = ttk.Frame(self.top_frame)
        self.mic_label = ttk.Label(self.mic_frame, text = 'Mic: ')
        self.mic_combo = ttk.Combobox(self.mic_frame, values = ['default'], state = 'readonly')
        self.mic_combo.current(0)
        self.mic_button = ttk.Button(self.mic_frame, text = 'Refresh', command = lambda: self.mic_combo.config(values = ['default'] + core.get_mic_names()))
        self.mic_label.pack(side = 'left')
        self.mic_combo.pack(side = 'left')
        self.mic_button.pack(side = 'left')
        self.mic_frame.pack(side = 'left', padx = 5)
        self.model_frame = ttk.Frame(self.top_frame)
        self.model_label = ttk.Label(self.model_frame, text = 'Model size or path: ')
        self.model_combo = ttk.Combobox(self.model_frame, values = core.models, state = 'normal')
        self.model_label.pack(side = 'left')
        self.model_combo.pack(side = 'left', fill = 'x', expand = True)
        self.model_frame.pack(side = 'left', fill = 'x', expand = True, padx = 5)
        self.memory_frame = ttk.Frame(self.top_frame)
        self.memory_label = ttk.Label(self.memory_frame, text = 'Memory: ')
        self.memory_spin = ttk.Spinbox(self.memory_frame, from_ = 1, to = 10, state = 'readonly')
        self.memory_spin.set(3)
        self.memory_label.pack(side = 'left')
        self.memory_spin.pack(side = 'left')
        self.memory_frame.pack(side = 'left', padx = 5)
        self.patience_frame = ttk.Frame(self.top_frame)
        self.patience_label = ttk.Label(self.patience_frame, text = 'Patience: ')
        self.patience_spin = ttk.Spinbox(self.patience_frame, from_ = 1.0, to = 20.0, increment = 0.1, state = 'readonly')
        self.patience_spin.set(5.0)
        self.patience_label.pack(side = 'left')
        self.patience_spin.pack(side = 'left')
        self.patience_frame.pack(side = 'left', padx = 5)
        self.timeout_frame = ttk.Frame(self.top_frame)
        self.timeout_label = ttk.Label(self.timeout_frame, text = 'Timeout: ')
        self.timeout_spin = ttk.Spinbox(self.timeout_frame, from_ = 1.0, to = 20.0, increment = 0.1, state = 'readonly')
        self.timeout_spin.set(5.0)
        self.timeout_label.pack(side = 'left')
        self.timeout_spin.pack(side = 'left')
        self.timeout_frame.pack(side = 'left', padx = 5)
        self.prompt_frame = ttk.Frame(self.bot_frame)
        self.prompt_label = ttk.Label(self.prompt_frame, text = 'Prompt: ')
        self.prompt_entry = ttk.Entry(self.prompt_frame, state = 'normal')
        self.prompt_label.pack(side = 'left')
        self.prompt_entry.pack(side = 'left', fill = 'x', expand = True)
        self.prompt_frame.pack(side = 'left', fill = 'x', expand = True, padx = 5)
        self.source_frame = ttk.Frame(self.bot_frame)
        self.source_label = ttk.Label(self.source_frame, text = 'Source: ')
        self.source_combo = ttk.Combobox(self.source_frame, values = ['auto'] + core.sources, state = 'readonly')
        self.source_combo.current(0)
        self.source_label.pack(side = 'left')
        self.source_combo.pack(side = 'left')
        self.source_frame.pack(side = 'left', padx = 5)
        self.target_frame = ttk.Frame(self.bot_frame)
        self.target_label = ttk.Label(self.target_frame, text = 'Target: ')
        self.target_combo = ttk.Combobox(self.target_frame, values = ['none'] + core.targets, state = 'readonly')
        self.target_combo.current(0)
        self.target_label.pack(side = 'left')
        self.target_combo.pack(side = 'left')
        self.target_frame.pack(side = 'left', padx = 5)
        self.state_button = ttk.Button(self.bot_frame, text = 'Start', command = self.start, state = 'normal')
        self.state_button.pack(side = 'left', padx = 5)
        self.controllable = [True]
    def start(self):
        self.controllable[0] = False
        self.state_button.config(text = 'Starting...', command = None, state = 'disabled')
        index = None if self.mic_combo.current() == 0 else self.mic_combo.current() - 1
        model = self.model_combo.get()
        memory = int(self.memory_spin.get())
        patience = float(self.patience_spin.get())
        timeout = float(self.timeout_spin.get())
        prompt = self.prompt_entry.get()
        source = None if self.source_combo.get() == 'auto' else self.source_combo.get()
        target = None if self.target_combo.get() == 'none' else self.target_combo.get()
        threading.Thread(target = core.process, args = (index, model, memory, patience, timeout, prompt, source, target, self.ts_text.res_queue, self.tl_text.res_queue, self.controllable), daemon = True).start()
        self.starting()
    def starting(self):
        if self.controllable[0] is True:
            self.state_button.config(text = 'Stop', command = self.stop, state = 'normal')
            return
        if isinstance(self.controllable[0], Exception):
            messagebox.showerror('Error', self.controllable[0])
            self.controllable[0] = True
            self.state_button.config(text = 'Start', command = self.start, state = 'normal')
            return
        self.after(100, self.starting)
    def stop(self):
        self.controllable[0] = False
        self.state_button.config(text = 'Stopping...', command = None, state = 'disabled')
        self.stopping()
    def stopping(self):
        if self.controllable[0] is True:
            self.state_button.config(text = 'Start', command = self.start, state = 'normal')
            return
        self.after(100, self.stopping)
if __name__ == '__main__':
    Show().mainloop()

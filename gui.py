import tkinter as tk
class Text(tk.Text):
    def __init__(self, master, res_queue):
        super().__init__(master)
        self.res_queue = res_queue
        self.tag_config('done', foreground = 'black')
        self.tag_config('curr', foreground = 'blue')
        self.insert(tk.END, '  ', 'done')
        self.record = self.index('end-1c')
        self.start = True
        self.see(tk.END)
        self.config(state = tk.DISABLED)
        self.after(100, self.update)
    def update(self):
        while not self.res_queue.empty():
            res = self.res_queue.get()
            self.config(state = tk.NORMAL)
            if res is not None:
                done, curr = res
                self.delete(self.record, tk.END)
                self.insert(tk.END, done, 'done')
                self.record = self.index('end-1c')
                self.insert(tk.END, curr, 'curr')
                self.start = False
            elif self.start is False:
                done = self.get(self.record, 'end-1c')
                self.delete(self.record, tk.END)
                self.insert(tk.END, done, 'done')
                self.insert(tk.END, '\n', 'done')
                self.insert(tk.END, '  ', 'done')
                self.record = self.index('end-1c')
                self.start = True
            self.see(tk.END)
            self.config(state = tk.DISABLED)
        self.after(100, self.update) # avoid busy waiting
def show(listen_flag, tsres_queue, tlres_queue):
    root = tk.Tk()
    Text(root, tsres_queue).grid(row = 0, column = 0, sticky = tk.NSEW)
    Text(root, tlres_queue).grid(row = 0, column = 1, sticky = tk.NSEW)
    root.columnconfigure(0, weight = 1)
    root.columnconfigure(1, weight = 1)
    root.rowconfigure(0, weight = 1)
    root.title('Whispering - Paused... Press Ctrl+R to start recording')
    root.bind('<Control-r>', lambda _: ([None for listen_flag[0] in [True]], root.title('Whispering - Recording... Press Ctrl+P to pause')))
    root.bind('<Control-p>', lambda _: ([None for listen_flag[0] in [False]], root.title('Whispering - Paused... Press Ctrl+R to resume')))
    root.mainloop()

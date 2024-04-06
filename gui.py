import tkinter as tk
class Text(tk.Text):
    def __init__(self, master, res_queue):
        super().__init__(master)
        self.res_queue = res_queue
        self.tag_config('done', foreground = 'black')
        self.tag_config('curr', foreground = 'blue')
        self.insert(tk.END, '  ', 'done')
        self.record = self.index('end-1c')
        self.last = None
        self.see(tk.END)
        self.config(state = tk.DISABLED)
        self.after(100, self.update)
    def update(self):
        while not self.res_queue.empty():
            res = self.res_queue.get()
            self.config(state = tk.NORMAL)
            if res is not True:
                done_str, curr_str = res
                self.delete(self.record, tk.END)
                self.insert(tk.END, done_str, 'done')
                self.record = self.index('end-1c')
                self.insert(tk.END, curr_str, 'curr')
                self.last = curr_str
            elif self.last is not None:
                done_str = self.last
                self.delete(self.record, tk.END)
                self.insert(tk.END, done_str, 'done')
                self.insert(tk.END, '\n', 'done')
                self.insert(tk.END, '  ', 'done')
                self.record = self.index('end-1c')
                self.last = None
            self.see(tk.END)
            self.config(state = tk.DISABLED)
        self.after(100, self.update) # avoid busy waiting
def show(tsres_queue, tlres_queue):
    root = tk.Tk()
    Text(root, tsres_queue).pack(expand = True, fill = 'both', side = 'left')
    Text(root, tlres_queue).pack(expand = True, fill = 'both', side = 'right')
    root.mainloop()

import tkinter as tk
from cmque import PairDeque, Queue
from debug import debug_print

class Text(tk.Text):
    def __init__(self, master, on_new_text=None, on_text_changed=None):
        super().__init__(master)
        self.res_queue = Queue(PairDeque())
        self.on_new_text = on_new_text  # Callback for NEW text only
        self.on_text_changed = on_text_changed  # Callback when any text changes
        self.tag_config("done", foreground="black")
        self.tag_config("curr", foreground="blue", underline=True)
        self.insert("end", "  ", "done")
        self.record = self.index("end-1c")
        self.prev_done = ""  # Track what we've already processed
        self.see("end")
        # Keep text editable! No state="disabled"
        self.poll()

    def poll(self):
        text_changed = False
        queue_name = None
        # Identify which Text widget this is for debug purposes
        try:
            if hasattr(self, 'winfo_parent'):
                parent = self.nametowidget(self.winfo_parent())
                if hasattr(parent, 'winfo_parent'):
                    grandparent = parent.nametowidget(parent.winfo_parent())
                    # Try to determine if this is the proofread text widget
                    if 'pr_text' in str(self):
                        queue_name = "PR_QUEUE"
                    elif 'tl_text' in str(self):
                        queue_name = "TL_QUEUE"
                    elif 'ts_text' in str(self):
                        queue_name = "TS_QUEUE"
        except:
            pass

        while self.res_queue:
            # Temporarily enable widget if disabled (for programmatic updates)
            was_disabled = str(self.cget("state")) == "disabled"
            if was_disabled:
                self.config(state="normal")

            if res := self.res_queue.get():
                done, curr = res
                # Calculate NEW text (what we haven't processed yet)
                new_text = ""
                if len(done) > len(self.prev_done):
                    new_text = done[len(self.prev_done):]
                self.prev_done = done

                if queue_name:
                    debug_print(f"[TEXT-{queue_name}] Received: done={done[:50]}... curr={curr[:50]}...", flush=True)
                    if new_text:
                        debug_print(f"[TEXT-{queue_name}] NEW text: {new_text[:100]}...", flush=True)

                # Update display
                self.delete(self.record, "end")
                self.insert("end", done, "done")
                self.record = self.index("end-1c")
                self.insert("end", curr, "curr")
                self.see("end")
                text_changed = True

                # Fire callback with only NEW text
                if new_text and self.on_new_text:
                    self.on_new_text(new_text)
            else:
                # Stop signal - finalize current line
                done = self.get(self.record, "end-1c")
                self.delete(self.record, "end")
                self.insert("end", done, "done")
                self.insert("end", "\n", "done")
                self.insert("end", "  ", "done")
                self.record = self.index("end-1c")
                self.prev_done = ""  # Reset for next segment
                self.see("end")
                text_changed = True

            # Restore disabled state if it was disabled
            if was_disabled:
                self.config(state="disabled")

        # Fire text changed callback if text was modified
        if text_changed and self.on_text_changed:
            self.on_text_changed()

        self.after(100, self.poll)

    def clear(self):
        """Clear all text and reset state."""
        self.delete("1.0", "end")
        self.insert("end", "  ", "done")
        self.record = self.index("end-1c")
        self.prev_done = ""
        # Fire text changed callback after clearing
        if self.on_text_changed:
            self.on_text_changed()

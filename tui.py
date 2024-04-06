import curses
import time
class Pad:
    def __init__(self, h, w, t, l, res_queue):
        self.pad = curses.newpad(h * 2, w)
        self.pad.scrollok(True)
        self.h, self.w, self.t, self.l = h, w, t, l
        self.res_queue = res_queue
        self.add_done('  ')
        self.save_pos()
        self.last = None
        self.refresh()
    def refresh(self):
        y, x = self.pad.getyx()
        if y >= self.h:
            t = y - self.h + 1
            self.pad.scroll(t)
            self.y -= t
        self.pad.refresh(0, 0, self.t, self.l, self.t + self.h - 1, self.l + self.w - 1)
    def save_pos(self):
        self.y, self.x = self.pad.getyx()
    def load_pos(self):
        self.pad.move(self.y, self.x)
        self.pad.clrtobot()
    def add_curr(self, curr_str):
        self.pad.attron(curses.A_UNDERLINE | curses.A_DIM)
        self.pad.addstr(curr_str)
        self.pad.attroff(curses.A_UNDERLINE | curses.A_DIM)
    def add_done(self, done_str):
        self.pad.addstr(done_str)
    def update(self):
        while not self.res_queue.empty():
            res = self.res_queue.get()
            if res is not True:
                done_str, curr_str = res
                self.load_pos()
                self.add_done(done_str)
                self.save_pos()
                self.add_curr(curr_str)
                self.last = curr_str
            elif self.last is not None:
                done_str = self.last
                self.load_pos()
                self.add_done(done_str)
                self.add_done('\n')
                self.add_done('  ')
                self.save_pos()
                self.last = None
            self.refresh()
def show(tsres_queue, tlres_queue):
    stdscr = curses.initscr()
    curses.curs_set(0)
    stdscr.clear()
    h, w = curses.LINES, curses.COLS
    stdscr.hline(    0,          1, curses.ACS_HLINE, w - 3)
    stdscr.hline(h - 1,          1, curses.ACS_HLINE, w - 3)
    stdscr.vline(    1,          0, curses.ACS_VLINE, h - 2)
    stdscr.vline(    1, w      - 2, curses.ACS_VLINE, h - 2)
    stdscr.vline(    1, w // 2 - 1, curses.ACS_VLINE, h - 2)
    stdscr.addch(    0,          0, curses.ACS_ULCORNER)
    stdscr.addch(h - 1,          0, curses.ACS_LLCORNER)
    stdscr.addch(    0, w      - 2, curses.ACS_URCORNER)
    stdscr.addch(h - 1, w      - 2, curses.ACS_LRCORNER)
    stdscr.addch(    0, w // 2 - 1, curses.ACS_TTEE)
    stdscr.addch(h - 1, w // 2 - 1, curses.ACS_BTEE)
    stdscr.refresh()
    ts_win = Pad(h - 2, w // 2 - 4, 1,          2, tsres_queue)
    tl_win = Pad(h - 2, w // 2 - 4, 1, w // 2 + 1, tlres_queue)
    while True:
        try:
            ts_win.update()
            tl_win.update()
            time.sleep(0.1)
        except KeyboardInterrupt:
            break
    curses.curs_set(1)
    curses.endwin()

import curses
class Pad:
    def __init__(self, h, w, t, l, res_queue):
        self.pad = curses.newpad(h * 2, w)
        self.h, self.w, self.t, self.l = h, w, t, l
        self.res_queue = res_queue
        self.add_done('> ')
        self.last = None
        self.refresh()
    def refresh(self):
        self.pad.refresh(0, 0, self.t, self.l, self.t + self.h - 1, self.l + self.w - 1)
    def load_pos(self):
        self.pad.move(self.y, self.x)
        self.pad.clrtobot()
    def add_curr(self, curr):
        self.pad.attron(curses.A_UNDERLINE | curses.A_DIM)
        self.pad.addstr(curr)
        self.pad.attroff(curses.A_UNDERLINE | curses.A_DIM)
        y, x = self.pad.getyx()
        if y >= self.h:
            t = y - self.h + 1
            self.pad.scrollok(True)
            self.pad.scroll(t)
            self.pad.scrollok(False)
            self.pad.move(y - t, x)
            self.y -= t
    def add_done(self, done):
        self.pad.scrollok(True)
        self.pad.addstr(done)
        self.pad.scrollok(False)
        y, x = self.pad.getyx()
        if y >= self.h:
            t = y - self.h + 1
            self.pad.scrollok(True)
            self.pad.scroll(t)
            self.pad.scrollok(False)
            self.pad.move(y - t, x)
        self.y, self.x = self.pad.getyx()
    def update(self):
        while not self.res_queue.empty():
            res = self.res_queue.get()
            if res is not None:
                done, curr = res
                self.load_pos()
                self.add_done(done)
                self.add_curr(curr)
                self.last = curr
            elif self.last is not None:
                done = self.last
                self.load_pos()
                self.add_done(done)
                self.add_done('\n')
                self.add_done('> ')
                self.last = None
            self.refresh()
def show(listen_flag, tsres_queue, tlres_queue):
    stdscr = curses.initscr()
    curses.setupterm()
    curses.curs_set(0)
    curses.noecho()
    stdscr.clear()
    stdscr.timeout(100)
    h, w = curses.LINES, curses.COLS
    t =          1
    b = h      - 1
    l =          0
    r = w      - 2
    m = w // 2 - 1
    stdscr.hline(t    , l + 1, curses.ACS_HLINE, r - l - 1)
    stdscr.hline(b    , l + 1, curses.ACS_HLINE, r - l - 1)
    stdscr.vline(t + 1, l    , curses.ACS_VLINE, b - t - 1)
    stdscr.vline(t + 1, r    , curses.ACS_VLINE, b - t - 1)
    stdscr.vline(t + 1, m    , curses.ACS_VLINE, b - t - 1)
    stdscr.addch(t    , l    , curses.ACS_ULCORNER)
    stdscr.addch(b    , l    , curses.ACS_LLCORNER)
    stdscr.addch(t    , r    , curses.ACS_URCORNER)
    stdscr.addch(b    , r    , curses.ACS_LRCORNER)
    stdscr.addch(t    , m    , curses.ACS_TTEE)
    stdscr.addch(b    , m    , curses.ACS_BTEE)
    stdscr.addstr(0, l, '[R]ecord [P]ause [Q]uit'.rjust(r - l + 1))
    stdscr.addstr(0, l, 'Paused...   ')
    ts_win = Pad(b - t - 1, m - l - 3, t + 1, l + 2, tsres_queue)
    tl_win = Pad(b - t - 1, r - m - 3, t + 1, m + 2, tlres_queue)
    while True:
        stdscr.refresh()
        ts_win.update()
        tl_win.update()
        key = stdscr.getch()
        if key == ord('q') or key == ord('Q'):
            break
        elif key == ord('r') or key == ord('R'):
            listen_flag[0] = True
            stdscr.addstr(0, l, 'Recording...')
        elif key == ord('p') or key == ord('P'):
            listen_flag[0] = False
            stdscr.addstr(0, l, 'Paused...   ')
    curses.endwin()

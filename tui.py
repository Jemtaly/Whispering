import curses
import time
class Text:
    def __init__(self, height, width, begin_y, begin_x, res_queue):
        self.win = curses.newwin(height, width, begin_y, begin_x)
        self.res_queue = res_queue
        self.win.addstr(0, 0, '  ')
        self.savepos()
        self.last = None
    def savepos(self):
        self.row, self.col = self.win.getyx()
    def loadpos(self):
        self.win.move(self.row, self.col)
        self.win.clrtoeol()
    def update(self):
        while not self.res_queue.empty():
            res = self.res_queue.get()
            if res is not True:
                done_str, curr_str = res
                self.loadpos()
                self.win.addstr(done_str)
                self.savepos()
                self.win.attron(curses.A_UNDERLINE | curses.A_DIM)
                self.win.addstr(curr_str)
                self.win.attroff(curses.A_UNDERLINE | curses.A_DIM)
                self.last = curr_str
            elif self.last:
                curr_str = self.last
                self.loadpos()
                self.win.addstr(curr_str)
                self.win.addstr('\n')
                self.win.addstr('  ')
                self.savepos()
                self.last = None
            self.win.refresh()
def show(tsres_queue, tlres_queue):
    stdscr = curses.initscr()
    stdscr.clear()
    nrows, ncols = curses.LINES, curses.COLS
    stdscr.clear()
    stdscr.hline(        0,              1, curses.ACS_HLINE, ncols // 2 - 2)
    stdscr.hline(        0, ncols // 2    , curses.ACS_HLINE, ncols // 2 - 2)
    stdscr.vline(        1,              0, curses.ACS_VLINE, nrows      - 2)
    stdscr.vline(        1, ncols // 2 - 1, curses.ACS_VLINE, nrows      - 2)
    stdscr.vline(        1, ncols      - 2, curses.ACS_VLINE, nrows      - 2)
    stdscr.hline(nrows - 1,              1, curses.ACS_HLINE, ncols // 2 - 2)
    stdscr.hline(nrows - 1, ncols // 2    , curses.ACS_HLINE, ncols // 2 - 2)
    stdscr.addch(        0, ncols // 2 - 1, curses.ACS_TTEE)
    stdscr.addch(nrows - 1, ncols // 2 - 1, curses.ACS_BTEE)
    stdscr.addch(        0,              0, curses.ACS_ULCORNER)
    stdscr.addch(        0, ncols      - 2, curses.ACS_URCORNER)
    stdscr.addch(nrows - 1,              0, curses.ACS_LLCORNER)
    stdscr.addch(nrows - 1, ncols      - 2, curses.ACS_LRCORNER)
    stdscr.refresh()
    ts_win = Text(nrows - 2, ncols // 2 - 4, 1,              2, tsres_queue)
    tl_win = Text(nrows - 2, ncols // 2 - 4, 1, ncols // 2 + 1, tlres_queue)
    while True:
        try:
            ts_win.update()
            tl_win.update()
            time.sleep(0.1)
        except KeyboardInterrupt:
            break
    curses.endwin()

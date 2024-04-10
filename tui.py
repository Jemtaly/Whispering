#!/usr/bin/env python3
import curses
import threading
import argparse
import core
from que import PairQueue
class Pad:
    def __init__(self, h, w, t, l):
        self.pad = curses.newpad(h * 2, w)
        self.h, self.w, self.t, self.l = h, w, t, l
        self.res_queue = PairQueue()
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
def show(mic, model, memory, patience, timeout, prompt, source, target):
    mic, model = core.prepare(mic, model)
    listen_flag = [False]
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
    stdscr.addstr(0, l, '<Space> to start/stop, <Q> to quit'.rjust(r - l + 1))
    stdscr.addstr(0, l, 'Paused...    ')
    stdscr.refresh()
    ts_win = Pad(b - t - 1, m - l - 3, t + 1, l + 2)
    tl_win = Pad(b - t - 1, r - m - 3, t + 1, m + 2)
    while True:
        key = stdscr.getch()
        ts_win.update()
        tl_win.update()
        if key == ord(' '):
            if listen_flag[0]:
                stdscr.addstr(0, l, 'Pausing...   ')
                stdscr.refresh()
                listen_flag[0] = False
                thread.join()
                del thread
                stdscr.addstr(0, l, 'Paused...    ')
                stdscr.refresh()
            else:
                listen_flag[0] = True
                thread = threading.Thread(target = core.process, args = (mic, model, memory, patience, timeout, prompt, source, target, ts_win.res_queue, tl_win.res_queue, listen_flag), daemon = True)
                thread.start()
                stdscr.addstr(0, l, 'Listening... ')
                stdscr.refresh()
        elif key == ord('q') or key == ord('Q'):
            break
    curses.endwin()
def main():
    parser = argparse.ArgumentParser(description = 'Transcribe and translate speech in real-time.')
    parser.add_argument('--mic', type = str, default = None, help = 'microphone device name')
    parser.add_argument('--model', type = str, choices = ['tiny', 'base', 'small', 'medium', 'large'], default = 'base', help = 'size of the model to use')
    parser.add_argument('--memory', type = int, default = 3, help = 'maximum number of previous segments to be used as prompt for audio in the transcribing window')
    parser.add_argument('--patience', type = float, default = 5.0, help = 'minimum time to wait for subsequent speech before move a completed segment out of the transcribing window')
    parser.add_argument('--timeout', type = float, default = None, help = 'timeout for the translation service')
    parser.add_argument('--prompt', type = str, default = '', help = 'initial prompt for the first segment of each paragraph')
    parser.add_argument('--source', type = str, default = None, help = 'source language for translation, auto-detect if not specified')
    parser.add_argument('--target', type = str, default = None, help = 'target language for translation, no translation if not specified')
    args = parser.parse_args()
    show(args.mic, args.model, args.memory, args.patience, args.timeout, args.prompt, args.source, args.target)
if __name__ == '__main__':
    main()

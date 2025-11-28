#!/usr/bin/env python3


import argparse
import curses
import threading

import core
from cmque import PairDeque, Queue


class Pad:
    def __init__(self, h, w, t, l):
        self.pad = curses.newpad(h * 2, w)
        self.h, self.w, self.t, self.l = h, w, t, l
        self.res_queue = Queue(PairDeque())
        self.add_done("> ")
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
        self.last += curr

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
        self.last = ""

    def update(self):
        while self.res_queue:
            res = self.res_queue.get()
            if res is not None:
                done, curr = res
                self.load_pos()
                self.add_done(done)
                self.add_curr(curr)
            else:
                done = self.last
                self.load_pos()
                self.add_done(done)
                self.add_done("\n")
                self.add_done("> ")
        self.refresh()


def show(mic, model, vad, memory, patience, timeout, prompt, source, target, device):
    stdscr = curses.initscr()
    curses.setupterm()
    curses.curs_set(0)
    curses.noecho()
    stdscr.clear()
    stdscr.timeout(100)
    h, w = curses.LINES, curses.COLS
    t = 1
    b = h - 1
    l = 0
    r = w - 2
    m = w // 2 - 1
    stdscr.hline(t, l + 1, curses.ACS_HLINE, r - l - 1)
    stdscr.hline(b, l + 1, curses.ACS_HLINE, r - l - 1)
    stdscr.vline(t + 1, l, curses.ACS_VLINE, b - t - 1)
    stdscr.vline(t + 1, r, curses.ACS_VLINE, b - t - 1)
    stdscr.vline(t + 1, m, curses.ACS_VLINE, b - t - 1)
    stdscr.addch(t, l, curses.ACS_ULCORNER)
    stdscr.addch(b, l, curses.ACS_LLCORNER)
    stdscr.addch(t, r, curses.ACS_URCORNER)
    stdscr.addch(b, r, curses.ACS_LRCORNER)
    stdscr.addch(t, m, curses.ACS_TTEE)
    stdscr.addch(b, m, curses.ACS_BTEE)
    ts_win = Pad(b - t - 1, m - l - 3, t + 1, l + 2)
    tl_win = Pad(b - t - 1, r - m - 3, t + 1, m + 2)
    ready = [None]
    error = [None]
    level = [0]  # Audio level (not displayed in TUI for now)
    instr = " <Space> Start/Stop <Q> Quit"
    state = "Stopped"
    while True:
        status = state
        if error[0] and state == "Stopped":
            status = f"Error: {error[0][:40]}"
        stdscr.addstr(0, l, status + " " * (r - l + 1 - len(status) - len(instr)) + instr)
        stdscr.refresh()
        ts_win.update()
        tl_win.update()
        key = stdscr.getch()
        if key == ord("q") or key == ord("Q"):
            break
        elif state.startswith("Stopped"):
            if key == ord(" "):
                ready[0] = False
                error[0] = None
                # Get mic index: smart default if not specified
                mic_index = core.get_mic_index(mic) if mic else core.get_default_device_index()
                threading.Thread(target=core.proc, args=(mic_index, model, vad, memory, patience, timeout, prompt, source, target, ts_win.res_queue, tl_win.res_queue, ready, device, error, level), daemon=True).start()
                state = "Starting..."
        elif state.startswith("Started"):
            if key == ord(" "):
                ready[0] = False
                state = "Stopping..."
        elif state.startswith("Stopping..."):
            if ready[0] is None:
                state = "Stopped"
        elif state.startswith("Starting..."):
            if ready[0] is True:
                state = "Started"
            if ready[0] is None:
                state = "Stopped"
    curses.endwin()


def main():
    parser = argparse.ArgumentParser(description="Transcribe and translate speech in real-time.")
    parser.add_argument("--mic", type=str, default=None, help="microphone device name")
    parser.add_argument("--model", type=str, choices=core.models, default="large-v3", help="size of the model to use")
    parser.add_argument("--vad", action="store_true", help="enable voice activity detection")
    parser.add_argument("--memory", type=int, default=3, help="maximum number of previous segments to be used as prompt for audio in the transcribing window")
    parser.add_argument("--patience", type=float, default=5.0, help="minimum time to wait for subsequent speech before move a completed segment out of the transcribing window")
    parser.add_argument("--timeout", type=float, default=5.0, help="timeout for the translation service")
    parser.add_argument("--prompt", type=str, default="", help="initial prompt for the first segment of each paragraph")
    parser.add_argument("--source", type=str, default=None, choices=core.sources, help="source language for translation, auto-detect if not specified")
    parser.add_argument("--target", type=str, default=None, choices=core.targets, help="target language for translation, no translation if not specified")
    parser.add_argument("--device", type=str, default="cuda", choices=core.devices, help="device to use for inference (cpu, cuda, or auto)")
    args = parser.parse_args()
    show(args.mic, args.model, args.vad, args.memory, args.patience, args.timeout, args.prompt, args.source, args.target, args.device)


if __name__ == "__main__":
    main()

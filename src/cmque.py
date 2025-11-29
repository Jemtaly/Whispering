import collections
import threading


class Queue:
    def __init__(self, deque):
        self.deque = deque
        self.cond = threading.Condition()

    def __bool__(self):
        with self.cond:
            return bool(self.deque)

    def put(self, item):
        with self.cond:
            self.deque.append(item)
            self.cond.notify()

    def get(self):
        with self.cond:
            while not self.deque:
                self.cond.wait()
            return self.deque.popleft()


class DataDeque(collections.deque):
    def append(self, item):
        if item is None:
            super().append(None)
        elif self and self[-1] is not None:
            self[-1].extend(item)
        else:
            super().append(bytearray(item))


class PairDeque(collections.deque):
    def append(self, item):
        if item is None:
            super().append(None)
        elif self and self[-1] is not None:
            self[-1][0] = item[0]
            self[-1][1] += item[1]
        else:
            super().append(list(item))

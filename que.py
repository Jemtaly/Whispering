import collections
import threading
class DataDeque(collections.deque):
    def append(self, item):
        if self and self[-1] is not None and item is not None:
            self[-1].extend(item)
        else:
            super().append(item)
class PairDeque(collections.deque):
    def append(self, item):
        if self and self[-1] is not None and item is not None:
            done, curr = self[-1]
            temp, curr = item
            done += temp
            self[-1] = done, curr
        else:
            super().append(item)
def template(Deque = collections.deque):
    class Queue:
        def __init__(self):
            self.queue = Deque()
            self.cond = threading.Condition()
        def __bool__(self):
            with self.cond:
                return bool(self.queue)
        def put(self, item):
            with self.cond:
                self.queue.append(item)
                self.cond.notify()
        def get(self):
            with self.cond:
                while not self.queue:
                    self.cond.wait()
                return self.queue.popleft()
    return Queue
DataQueue = template(DataDeque)
PairQueue = template(PairDeque)

import collections
import threading
class Queue:
    def __init__(self):
        self.queue = collections.deque()
        self.cond = threading.Condition()
    def empty(self):
        with self.cond:
            return not self.queue
    def put(self, item):
        with self.cond:
            self.queue.append(item)
            self.cond.notify()
    def get(self):
        with self.cond:
            while not self.queue:
                self.cond.wait()
            return self.queue.popleft()
class DataQueue(Queue):
    def put(self, item):
        with self.cond:
            if self.queue and self.queue[-1] is not None and item is not None:
                self.queue[-1].extend(item)
            else:
                self.queue.append(item)
            self.cond.notify()
class PairQueue(Queue):
    def put(self, item):
        with self.cond:
            if self.queue and self.queue[-1] is not None and item is not None:
                done, curr = self.queue[-1]
                temp, curr = item
                done += temp
                self.queue[-1] = done, curr
            else:
                self.queue.append(item)
            self.cond.notify()

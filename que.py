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
    def get(self):
        with self.cond:
            while not self.queue:
                self.cond.wait()
            if not isinstance(self.queue[0], bytes):
                return self.queue.popleft()
            data = self.queue.popleft()
            while self.queue and isinstance(self.queue[0], bytes):
                data += self.queue.popleft()
            return data
class PairQueue(Queue):
    def get(self):
        with self.cond:
            while not self.queue:
                self.cond.wait()
            if not isinstance(self.queue[0], tuple):
                return self.queue.popleft()
            done, curr = self.queue.popleft()
            while self.queue and isinstance(self.queue[0], tuple):
                temp, curr = self.queue.popleft()
                done += temp
            return done, curr

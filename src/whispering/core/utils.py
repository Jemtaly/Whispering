from collections import deque
from dataclasses import dataclass
from typing import Generic, TypeVar, Self, Protocol
import threading

import numpy as np


class Mergeable(Protocol):
    def merge(self, other: Self, /) -> None:
        pass


M = TypeVar("M", bound=Mergeable)


class MergingQueue(Generic[M]):
    def __init__(self):
        self.deque = deque[M | None]()
        self.cond = threading.Condition()

    def __bool__(self):
        with self.cond:
            return bool(self.deque)

    def put(self, item: M | None):
        with self.cond:
            if item is None:
                self.deque.append(None)
            elif self.deque and (last := self.deque[-1]) is not None:
                last.merge(item)
            else:
                self.deque.append(item)
            self.cond.notify()

    def get(self) -> M | None:
        with self.cond:
            while not self.deque:
                self.cond.wait()
            return self.deque.popleft()


@dataclass
class Pair:
    cnfm: str  # confirmed part
    drft: str  # draft part

    def merge(self, other: Self):
        self.cnfm += other.cnfm
        self.drft = other.drft


@dataclass
class Data:
    data: np.ndarray  # 1D array of specific dtype

    def merge(self, other: Self):
        self.data = np.concatenate((self.data, other.data))

from collections import deque
from queue import Empty
from dataclasses import dataclass
from typing import Generic, TypeVar, Self, Protocol
from threading import Condition

import numpy as np


class Mergeable(Protocol):
    def merge(self, other: Self, /) -> Self: ...


M = TypeVar("M", bound=Mergeable)


class MergingQueue(Generic[M]):
    def __init__(self):
        self.deque = deque[M | None]()
        self.cond = Condition()

    def __bool__(self):
        with self.cond:
            return bool(self.deque)

    def put(self, item: M | None):
        with self.cond:
            if item is None:
                self.deque.append(None)
            elif self.deque and self.deque[-1] is not None:
                self.deque[-1] = self.deque[-1].merge(item)
            else:
                self.deque.append(item)
            self.cond.notify()

    def get(self) -> M | None:
        with self.cond:
            while not self.deque:
                self.cond.wait()
            return self.deque.popleft()

    def get_nowait(self) -> M | None:
        with self.cond:
            if not self.deque:
                raise Empty
            return self.deque.popleft()


@dataclass(frozen=True)
class Pair:
    cnfm: str  # confirmed part
    drft: str  # draft part

    def merge(self, other: Self) -> Self:
        return type(self)(cnfm=self.cnfm + other.cnfm, drft=other.drft)


@dataclass(frozen=True)
class Data:
    data: np.ndarray  # 1D array of specific dtype

    def merge(self, other: Self) -> Self:
        return type(self)(data=np.concatenate((self.data, other.data)))

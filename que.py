from collections import deque
from dataclasses import dataclass
from typing import Generic, TypeVar, Self, Protocol
import threading


class Extendable(Protocol):
    def extend(self, other: Self, /) -> None:
        pass


T = TypeVar("T", bound=Extendable)


class Queue(Generic[T]):
    def __init__(self):
        self.deque = deque[T | None]()
        self.cond = threading.Condition()

    def __bool__(self):
        with self.cond:
            return bool(self.deque)

    def put(self, item: T | None):
        with self.cond:
            if item is None:
                self.deque.append(None)
            elif self.deque and (last := self.deque[-1]) is not None:
                last.extend(item)
            else:
                self.deque.append(item)
            self.cond.notify()

    def get(self) -> T | None:
        with self.cond:
            while not self.deque:
                self.cond.wait()
            return self.deque.popleft()


@dataclass
class Pair:
    done: str
    curr: str

    def extend(self, other: Self):
        self.done += other.done
        self.curr = other.curr


Data = bytearray

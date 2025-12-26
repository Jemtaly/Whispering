from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal

import numpy as np

from whispering.core.utils import Pair, Data


class MicProcessor(ABC):
    @abstractmethod
    def __enter__(self) -> None:
        pass

    @abstractmethod
    def __exit__(self, exc_type, exc_value, traceback) -> None:
        pass

    @abstractmethod
    def read(self) -> Data:
        pass


class MicFactory(ABC):
    @abstractmethod
    def create(
        self,
        sample_type: np.dtype,
        sample_rate: int,
        sample_time: float,
    ) -> MicProcessor:
        pass


Language = Literal[
    "af", "am", "ar", "as", "az", "ba", "be", "bg", "bn", "bo",
    "br", "bs", "ca", "cs", "cy", "da", "de", "el", "en", "es",
    "et", "eu", "fa", "fi", "fo", "fr", "gl", "gu", "ha", "haw",
    "he", "hi", "hr", "ht", "hu", "hy", "id", "is", "it", "ja",
    "jw", "ka", "kk", "km", "kn", "ko", "la", "lb", "ln", "lo",
    "lt", "lv", "mg", "mi", "mk", "ml", "mn", "mr", "ms", "mt",
    "my", "ne", "nl", "nn", "no", "oc", "pa", "pl", "ps", "pt",
    "ro", "ru", "sa", "sd", "si", "sk", "sl", "sn", "so", "sq",
    "sr", "su", "sv", "sw", "ta", "te", "tg", "th", "tk", "tl",
    "tr", "tt", "uk", "ur", "uz", "vi", "yi", "yo", "yue", "zh",
]
LANGS = list(Language.__args__)


class TranscriptionProcessor(ABC):
    @abstractmethod
    def update(self, frame: Data) -> Pair:
        pass

    @property
    @abstractmethod
    def required_sample_type(self) -> np.dtype:
        pass

    @property
    @abstractmethod
    def required_sample_rate(self) -> int:
        pass


class TranscriptionFactory(ABC):
    @abstractmethod
    def create(
        self,
        lang: Language | None,
    ) -> TranscriptionProcessor:
        pass


class TranslationProcessor(ABC):
    @abstractmethod
    def update(self, src: Pair) -> Pair:
        pass


class TranslationFactory(ABC):
    @abstractmethod
    def create(
        self,
        source_lang: Language | None,
        target_lang: Language | None,
    ) -> TranslationProcessor:
        pass


@dataclass
class TranslationResult:
    source: str
    target: str


class AutoTranslationProcessor(TranslationProcessor):
    def __init__(self):
        self.src = ""

    @abstractmethod
    def translate(self, text: str) -> list[TranslationResult]:
        pass

    def update(self, src: Pair) -> Pair:
        cnfm_src = src.cnfm
        drft_src = src.drft
        if cnfm_src or self.src:
            cnfm_src = self.src + cnfm_src
            cnfm_res = self.translate(cnfm_src)
            self.src = cnfm_res.pop().source
            cnfm_tgt = "".join(r.target for r in cnfm_res)
        else:
            cnfm_tgt = ""
        drft_src = self.src + drft_src
        drft_res = self.translate(drft_src)
        drft_tgt = "".join(r.target for r in drft_res)
        return Pair(cnfm_tgt, drft_tgt)

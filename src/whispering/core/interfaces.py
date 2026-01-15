from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np

from whispering.core.utils import Pair, Data


class RecordingService(ABC):
    @abstractmethod
    def __enter__(self) -> None:
        pass

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        pass

    @abstractmethod
    def read(self) -> Data:
        pass


class RecordingServiceFactory(ABC):
    @abstractmethod
    def create(
        self,
        sample_type: np.dtype,
        sample_rate: int,
        sample_time: float,
    ) -> RecordingService:
        pass


LanguageCode = str


class TranscriptionService(ABC):
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


class TranscriptionServiceFactory(ABC):
    @abstractmethod
    def create(
        self,
        lang: LanguageCode | None,
    ) -> TranscriptionService:
        pass


class TranslationService(ABC):
    @abstractmethod
    def update(self, src: Pair) -> Pair:
        pass


class TranslationServiceFactory(ABC):
    @abstractmethod
    def create(
        self,
        source_lang: LanguageCode | None,
        target_lang: LanguageCode | None,
    ) -> TranslationService:
        pass


@dataclass
class TranslationResult:
    source: str
    target: str


class CoreTranslationService(TranslationService):
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

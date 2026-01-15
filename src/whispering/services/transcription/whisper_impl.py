from collections import deque
from typing import Literal
from functools import lru_cache

import numpy as np
from faster_whisper import WhisperModel

from whispering.core.utils import Data, Pair
from whispering.core.interfaces import (
    TranscriptionServiceFactory,
    TranscriptionService,
    Language,
)

import os

os.environ["KMP_DUPLICATE_LIB_OK"] = "True"


Model = Literal[
    "tiny", "base", "small", "medium", "large-v1", "large-v2", "large-v3", "large"
]
Device = Literal["auto", "cpu", "cuda"]
MODELS = list(Model.__args__)
DEVICES = list(Device.__args__)


@lru_cache(maxsize=None)
def get_model(model: Model, device: Device) -> WhisperModel:
    return WhisperModel(model, device)


class WhisperTranscriptionService(TranscriptionService):
    def __init__(
        self,
        model: Model,
        device: Device,
        vad: bool,
        lang: Language | None,
        prompts: list[str],
        memory: int,
        patience: float,
    ):
        self.model = get_model(model, device)
        self.sample_type = np.dtype(np.float32)
        self.sample_rate = self.model.feature_extractor.sampling_rate
        self.vad = vad
        self.lang = lang
        self.prompts = deque(prompts, memory)
        self.window = np.empty((0,), dtype=self.sample_type)
        self.patience = patience

    def update(self, frame: Data) -> Pair:
        self.window = np.concatenate((self.window, frame.data))
        segments, info = self.model.transcribe(
            self.window,
            language=self.lang,
            initial_prompt="".join(self.prompts),
            vad_filter=self.vad,
        )
        segments = list(segments)
        boundary = max(len(self.window) / self.sample_rate - self.patience, 0.0)
        i = 0
        for segment in segments:
            if segment.end >= boundary:
                if segment.start < boundary:
                    boundary = segment.start
                break
            i += 1
        cnfm_src = "".join(segment.text for segment in segments[:i])
        drft_src = "".join(segment.text for segment in segments[i:])
        self.prompts.extend(segment.text for segment in segments[:i])
        self.window = self.window[int(boundary * self.sample_rate) :]
        return Pair(cnfm_src, drft_src)

    @property
    def required_sample_type(self) -> np.dtype:
        return self.sample_type

    @property
    def required_sample_rate(self) -> int:
        return self.sample_rate


class WhisperTranscriptionFactory(TranscriptionServiceFactory):
    def __init__(
        self,
        model: Model,
        device: Device,
        vad: bool,
        prompts: list[str],
        memory: int,
        patience: float,
    ):
        self.model = model  # type: Model
        self.device = device  # type: Device
        self.vad = vad
        self.prompts = prompts
        self.memory = memory
        self.patience = patience

    def create(
        self,
        lang: Language | None,
    ) -> TranscriptionService:
        return WhisperTranscriptionService(
            model=self.model,
            device=self.device,
            vad=self.vad,
            lang=lang,
            prompts=self.prompts,
            memory=self.memory,
            patience=self.patience,
        )

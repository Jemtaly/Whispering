from dataclasses import dataclass

import numpy as np
from soundcard import (
    all_microphones,
    get_microphone,
    default_microphone,
)

from whispering.core.utils import Data
from whispering.core.interfaces import (
    RecordingService,
    RecordingServiceFactory,
)


@dataclass
class SoundcardMicrophoneInfo:
    id: str | None
    kind: str
    name: str

    @staticmethod
    def list_microphones():
        mic_info = SoundcardMicrophoneInfo(
            id=None,
            kind="default",
            name="Default Microphone",
        )
        mic_infos = [mic_info]
        for mic in all_microphones(include_loopback=True):
            mic_info = SoundcardMicrophoneInfo(
                id=mic.id,
                kind="loopback" if mic.isloopback else "microphone",
                name=mic.name,
            )
            mic_infos.append(mic_info)
        return mic_infos

    def get(self):
        if self.id is None:
            return default_microphone()
        else:
            return get_microphone(id=self.id, include_loopback=True)


class SoundcardRecordingService(RecordingService):
    def __init__(
        self,
        mic_info: SoundcardMicrophoneInfo,
        *,
        sample_type: np.dtype,
        sample_rate: int,
        sample_time: float,
    ):
        self.mic = mic_info.get()
        self.rec = self.mic.recorder(samplerate=sample_rate, channels=1)
        self.sample_size = int(sample_rate * sample_time)
        self.sample_type = sample_type

    def __enter__(self) -> None:
        self.rec.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.rec.__exit__(exc_type, exc_val, exc_tb)

    def read(self) -> Data:
        return Data(
            self.rec
            .record(numframes=self.sample_size)
            .squeeze(axis=1)
            .astype(self.sample_type)
        )


class SoundcardRecordingServiceFactory(RecordingServiceFactory):
    def __init__(
        self,
        mic_info: SoundcardMicrophoneInfo,
    ):
        self.mic_info = mic_info

    def create(
        self,
        sample_type: np.dtype,
        sample_rate: int,
        sample_time: float,
    ) -> RecordingService:
        return SoundcardRecordingService(
            self.mic_info,
            sample_type=sample_type,
            sample_rate=sample_rate,
            sample_time=sample_time,
        )

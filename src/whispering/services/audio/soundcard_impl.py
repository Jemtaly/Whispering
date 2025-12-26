import numpy as np
from soundcard import all_microphones, get_microphone, default_microphone

from whispering.core.utils import Data
from whispering.core.interfaces import MicProcessor, MicFactory


class SoundcardMicManager:
    def __init__(self):
        self.microphones = [None, *all_microphones(include_loopback=True)]

    def refresh(self):
        self.microphones = [None, *all_microphones(include_loopback=True)]
        return self

    def list_microphones(self) -> list[str]:
        result = []
        for mic in self.microphones:
            if mic is None:
                kind = "default"
                name = "Default Microphone"
            else:
                kind = "loopback" if mic.isloopback else "microphone"
                name = mic.name
            result.append(f"[{kind}] {name}")
        return result

    def get_microphone_by_index(self, index: int) -> str | None:
        mic = self.microphones[index]
        return mic.id if mic is not None else None


class SoundcardMicProcessor(MicProcessor):
    def __init__(
        self,
        mic_id: str | None = None,
        *,
        sample_type: np.dtype,
        sample_rate: int,
        sample_time: float,
    ):
        if mic_id is None:
            self.mic = default_microphone()
        else:
            self.mic = get_microphone(id=mic_id, include_loopback=True)
        self.rec = self.mic.recorder(samplerate=sample_rate, channels=1)
        self.sample_size = int(sample_rate * sample_time)
        self.sample_type = sample_type

    def __enter__(self) -> None:
        self.rec.__enter__()

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.rec.__exit__(exc_type, exc_value, traceback)

    def read(self) -> Data:
        return Data(self.rec.record(numframes=self.sample_size).squeeze(axis=1).astype(self.sample_type))


class SoundcardMicFactory(MicFactory):
    def __init__(
        self,
        mic_id: str | None = None,
    ):
        self.mic_id = mic_id

    def create(
        self,
        sample_type: np.dtype,
        sample_rate: int,
        sample_time: float,
    ) -> MicProcessor:
        return SoundcardMicProcessor(
            self.mic_id,
            sample_type=sample_type,
            sample_rate=sample_rate,
            sample_time=sample_time,
        )

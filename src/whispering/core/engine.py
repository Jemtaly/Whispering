from collections.abc import Callable
from dataclasses import dataclass, field

from threading import Thread

from whispering.core.utils import MergingQueue, Pair, Data
from whispering.core.interfaces import (
    RecordingServiceFactory,
    RecordingService,
    TranscriptionServiceFactory,
    TranscriptionService,
    TranslationServiceFactory,
    TranslationService,
    LanguageCode,
)


@dataclass
class RecordingConfig:
    factory: RecordingServiceFactory
    on_error: "Callable[[Exception], None]"


@dataclass
class TranscriptionConfig:
    factory: TranscriptionServiceFactory
    result_queue: MergingQueue[Pair]
    on_error: "Callable[[Exception], None]"


@dataclass
class TranslationConfig:
    factory: TranslationServiceFactory
    result_queue: MergingQueue[Pair]
    on_error: "Callable[[Exception], None]"


@dataclass
class RecordingContext:
    service: "RecordingService"
    put: "Callable[[Data | None], None]"
    on_error: "Callable[[Exception], None]"

    is_running: bool = False

    def stop(self):
        self.is_running = False

    def start(self):
        self.is_running = True
        try:
            with self.service:
                while self.is_running:
                    self.put(self.service.read())
        except Exception as err:
            self.on_error(err)
        finally:
            self.put(None)


@dataclass
class TranscriptionContext:
    service: "TranscriptionService"
    put: "Callable[[Pair | None], None]"
    on_error: "Callable[[Exception], None]"

    buffer_queue: MergingQueue[Data] = field(default_factory=MergingQueue[Data])

    def task(self):
        try:
            while frame := self.buffer_queue.get():
                src = self.service.update(frame)
                self.put(src)
        except Exception as err:
            self.on_error(err)
        finally:
            self.put(None)


@dataclass
class TranslationContext:
    service: "TranslationService"
    put: "Callable[[Pair | None], None]"
    on_error: "Callable[[Exception], None]"

    buffer_queue: MergingQueue[Pair] = field(default_factory=MergingQueue[Pair])

    def task(self):
        try:
            while pair := self.buffer_queue.get():
                dst = self.service.update(pair)
                self.put(dst)
        except Exception as err:
            self.on_error(err)
        finally:
            self.put(None)


class STTEngine:
    def __init__(
        self,
        record_cfg: RecordingConfig,
        transc_cfg: TranscriptionConfig,
        transl_cfg: TranslationConfig,
        lang: LanguageCode | None,
        on_stopped: "Callable[[], None]",
    ):
        def transl_put(value: Pair | None):
            transl_cfg.result_queue.put(value)

        transl_ctx = TranslationContext(
            service=transl_cfg.factory.create(lang=lang),
            put=transl_put,
            on_error=transl_cfg.on_error,
        )

        def transc_put(value: Pair | None):
            transc_cfg.result_queue.put(value)
            transl_ctx.buffer_queue.put(value)

        transc_ctx = TranscriptionContext(
            service=transc_cfg.factory.create(lang=lang),
            put=transc_put,
            on_error=transc_cfg.on_error,
        )

        def record_put(value: Data | None):
            transc_ctx.buffer_queue.put(value)

        record_ctx = RecordingContext(
            service=record_cfg.factory.create(
                sample_type=transc_ctx.service.required_sample_type,
                sample_rate=transc_ctx.service.required_sample_rate,
            ),
            put=record_put,
            on_error=record_cfg.on_error,
        )

        self.transl_ctx = transl_ctx
        self.transc_ctx = transc_ctx
        self.record_ctx = record_ctx
        self.on_stopped = on_stopped

    @staticmethod
    def start(
        record_cfg: RecordingConfig,
        transc_cfg: TranscriptionConfig,
        transl_cfg: TranslationConfig,
        lang: LanguageCode | None,  # None means auto detection
        on_failure: "Callable[[Exception], None]",
        on_success: "Callable[[STTEngine], None]",
        on_stopped: "Callable[[], None]",
    ):
        def task():
            try:
                eng = STTEngine(
                    record_cfg=record_cfg,
                    transc_cfg=transc_cfg,
                    transl_cfg=transl_cfg,
                    lang=lang,
                    on_stopped=on_stopped,
                )
            except Exception as err:
                on_failure(err)
            else:
                on_success(eng)
                eng._run()

        Thread(target=task, daemon=True).start()

    def stop(self):
        self.record_ctx.stop()

    def _run(self):
        transc_thread = Thread(target=self.transc_ctx.task)
        transl_thread = Thread(target=self.transl_ctx.task)
        transc_thread.start()
        transl_thread.start()
        try:
            self.record_ctx.start()
        finally:
            transc_thread.join()
            transl_thread.join()
            self.on_stopped()

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

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
    on_error: "Callable[[Exception], None]"
    result_queue_fn: "Callable[[], tuple[MergingQueue[Pair], Callable[[], Any]]]"


@dataclass
class TranslationConfig:
    factory: TranslationServiceFactory
    on_error: "Callable[[Exception], None]"
    result_queue_fn: "Callable[[], tuple[MergingQueue[Pair], Callable[[], Any]]]"


@dataclass
class RecordingContext:
    service: "RecordingService"
    put: "Callable[[Data], None]"
    end: "Callable[[], None]"
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
            self.end()


@dataclass
class TranscriptionContext:
    service: "TranscriptionService"
    make_put: "Callable[[], tuple[Callable[[Pair], None], Callable[[], None]]]"
    on_error: "Callable[[Exception], None]"

    buffer_queue: MergingQueue[Data] = field(default_factory=MergingQueue[Data])

    def task(self):
        put, end = self.make_put()
        try:
            while frame := self.buffer_queue.get():
                src = self.service.update(frame)
                put(src)
        except Exception as err:
            self.on_error(err)
        finally:
            end()


@dataclass
class TranslationContext:
    service: "TranslationService"
    make_put: "Callable[[], tuple[Callable[[Pair], None], Callable[[], None]]]"
    on_error: "Callable[[Exception], None]"

    buffer_queue: MergingQueue[Pair] = field(default_factory=MergingQueue[Pair])

    def task(self):
        put, end = self.make_put()
        try:
            while pair := self.buffer_queue.get():
                dst = self.service.update(pair)
                put(dst)
        except Exception as err:
            self.on_error(err)
        finally:
            end()


class STTEngine:
    def __init__(
        self,
        record_cfg: RecordingConfig,
        transc_cfg: TranscriptionConfig,
        transl_cfg: TranslationConfig | None,
        lang: LanguageCode | None,
        on_stopped: "Callable[[], None]",
    ):
        self.tasks: "list[Callable[[], None]]" = []

        if transl_cfg is not None:

            def make_transl_put():
                transl_result_queue, join = transl_cfg.result_queue_fn()

                def transl_put(value: Pair):
                    transl_result_queue.put(value)

                def transl_end():
                    transl_result_queue.put(None)
                    join()

                return transl_put, transl_end

            transl_ctx = TranslationContext(
                service=transl_cfg.factory.create(lang=lang),
                make_put=make_transl_put,
                on_error=transl_cfg.on_error,
            )
            self.tasks.append(transl_ctx.task)

            def make_transc_put():
                transl_buffer_queue = transl_ctx.buffer_queue
                transc_result_queue, join = transc_cfg.result_queue_fn()

                def transc_put(value: Pair):
                    transl_buffer_queue.put(value)
                    transc_result_queue.put(value)

                def transc_end():
                    transl_buffer_queue.put(None)
                    transc_result_queue.put(None)
                    join()

                return transc_put, transc_end

        else:

            def make_transc_put():
                transc_result_queue, join = transc_cfg.result_queue_fn()

                def transc_put(value: Pair):
                    transc_result_queue.put(value)

                def transc_end():
                    transc_result_queue.put(None)
                    join()

                return transc_put, transc_end

        transc_ctx = TranscriptionContext(
            service=transc_cfg.factory.create(lang=lang),
            make_put=make_transc_put,
            on_error=transc_cfg.on_error,
        )
        self.tasks.append(transc_ctx.task)

        transc_buffer_queue = transc_ctx.buffer_queue

        def record_put(value: Data):
            transc_buffer_queue.put(value)

        def record_end():
            transc_buffer_queue.put(None)

        self.record_ctx = RecordingContext(
            service=record_cfg.factory.create(
                sample_type=transc_ctx.service.required_sample_type,
                sample_rate=transc_ctx.service.required_sample_rate,
            ),
            put=record_put,
            end=record_end,
            on_error=record_cfg.on_error,
        )

        self.on_stopped = on_stopped

    @staticmethod
    def start(
        record_cfg: RecordingConfig,
        transc_cfg: TranscriptionConfig,
        transl_cfg: TranslationConfig | None,
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
        threads = [Thread(target=task) for task in self.tasks]
        for thread in threads:
            thread.start()
        try:
            self.record_ctx.start()
        finally:
            for thread in threads:
                thread.join()
            self.on_stopped()

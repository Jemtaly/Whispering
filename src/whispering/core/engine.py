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
    show_started: "Callable[[], Callable[[], Any]]"


@dataclass
class TranscriptionConfig:
    factory: TranscriptionServiceFactory
    on_error: "Callable[[Exception], None]"
    start_show: "Callable[[], tuple[MergingQueue[Pair], Callable[[], Any]]]"


@dataclass
class TranslationConfig:
    factory: TranslationServiceFactory
    on_error: "Callable[[Exception], None]"
    start_show: "Callable[[], tuple[MergingQueue[Pair], Callable[[], Any]]]"


@dataclass
class RecordingContext:
    service: "RecordingService"
    start: "Callable[[], tuple[Callable[[Data], None], Callable[[], None]]]"
    on_error: "Callable[[Exception], None]"

    is_running: bool = True

    def stop(self):
        self.is_running = False

    def run(self):
        put, end = self.start()
        try:
            with self.service:
                while self.is_running:
                    put(self.service.read())
        except Exception as err:
            self.on_error(err)
        finally:
            end()


@dataclass
class TranscriptionContext:
    service: "TranscriptionService"
    start: "Callable[[], tuple[Callable[[Pair], None], Callable[[], None]]]"
    on_error: "Callable[[Exception], None]"

    buffer_queue: MergingQueue[Data] = field(default_factory=MergingQueue[Data])

    def run(self):
        put, end = self.start()
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
    start: "Callable[[], tuple[Callable[[Pair], None], Callable[[], None]]]"
    on_error: "Callable[[Exception], None]"

    buffer_queue: MergingQueue[Pair] = field(default_factory=MergingQueue[Pair])

    def run(self):
        put, end = self.start()
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

            def start_transl():
                transl_result_queue, join_show = transl_cfg.start_show()

                def put(value: Pair):
                    transl_result_queue.put(value)

                def end():
                    transl_result_queue.put(None)
                    join_show()

                return put, end

            transl_ctx = TranslationContext(
                service=transl_cfg.factory.create(lang=lang),
                start=start_transl,
                on_error=transl_cfg.on_error,
            )
            self.tasks.append(transl_ctx.run)

            def start_transc():
                transl_buffer_queue = transl_ctx.buffer_queue
                transc_result_queue, join_show = transc_cfg.start_show()

                def put(value: Pair):
                    transl_buffer_queue.put(value)
                    transc_result_queue.put(value)

                def end():
                    transl_buffer_queue.put(None)
                    transc_result_queue.put(None)
                    join_show()

                return put, end

        else:

            def start_transc():
                transc_result_queue, join_show = transc_cfg.start_show()

                def put(value: Pair):
                    transc_result_queue.put(value)

                def end():
                    transc_result_queue.put(None)
                    join_show()

                return put, end

        transc_ctx = TranscriptionContext(
            service=transc_cfg.factory.create(lang=lang),
            start=start_transc,
            on_error=transc_cfg.on_error,
        )
        self.tasks.append(transc_ctx.run)

        transc_buffer_queue = transc_ctx.buffer_queue

        def start_record():
            show_stopped = record_cfg.show_started()

            def put(value: Data):
                transc_buffer_queue.put(value)

            def end():
                transc_buffer_queue.put(None)
                show_stopped()

            return put, end

        self.record_ctx = RecordingContext(
            service=record_cfg.factory.create(
                sample_type=transc_ctx.service.required_sample_type,
                sample_rate=transc_ctx.service.required_sample_rate,
            ),
            start=start_record,
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
            self.record_ctx.run()
        finally:
            for thread in threads:
                thread.join()
            self.on_stopped()

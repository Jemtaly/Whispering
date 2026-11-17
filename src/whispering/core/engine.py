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
class RecordingContext:
    service: "RecordingService"

    is_running: bool = True

    def stop(self):
        self.is_running = False

    def run(self, put: "Callable[[Data | None], None]"):
        try:
            with self.service:
                while self.is_running:
                    put(self.service.read())
        except Exception as err:
            print(err)
        finally:
            put(None)


@dataclass
class TranscriptionContext:
    service: "TranscriptionService"

    buffer_queue: MergingQueue[Data] = field(default_factory=MergingQueue[Data])

    def run(self, put: "Callable[[Pair | None], None]"):
        try:
            while frame := self.buffer_queue.get():
                src = self.service.update(frame)
                put(src)
        except Exception as err:
            print(err)
        finally:
            put(None)


@dataclass
class TranslationContext:
    service: "TranslationService"

    buffer_queue: MergingQueue[Pair] = field(default_factory=MergingQueue[Pair])

    def run(self, put: "Callable[[Pair | None], None]"):
        try:
            while pair := self.buffer_queue.get():
                dst = self.service.update(pair)
                put(dst)
        except Exception as err:
            print(err)
        finally:
            put(None)


class STTEngine:
    def __init__(
        self,
        record_cfg: RecordingServiceFactory,
        transc_cfg: TranscriptionServiceFactory,
        transl_cfgs: list[TranslationServiceFactory],
        lang: LanguageCode | None,
    ):
        self.transl_ctxs = [TranslationContext(transl_cfg.create(lang=lang)) for transl_cfg in transl_cfgs]
        self.transc_ctx = TranscriptionContext(transc_cfg.create(lang=lang))
        self.record_ctx = RecordingContext(
            record_cfg.create(
                sample_type=self.transc_ctx.service.required_sample_type,
                sample_rate=self.transc_ctx.service.required_sample_rate,
            )
        )

    @classmethod
    def start(
        cls,
        record_cfg: RecordingServiceFactory,
        transc_cfg: TranscriptionServiceFactory,
        transl_cfgs: list[TranslationServiceFactory],
        lang: LanguageCode | None,  # None means auto detection
        on_failure: Callable[[Exception], None],
        on_success: Callable[[Callable[[], None]], tuple[Callable[[], None], MergingQueue[Pair], list[MergingQueue[Pair]]]],
    ):
        def task():
            try:
                eng = cls(
                    record_cfg=record_cfg,
                    transc_cfg=transc_cfg,
                    transl_cfgs=transl_cfgs,
                    lang=lang,
                )
            except Exception as err:
                on_failure(err)
            else:
                (
                    on_stopped,
                    transc_result_queue,
                    transl_result_queues,
                ) = on_success(eng.stop)
                eng._run(
                    transc_result_queue,
                    transl_result_queues,
                )
                on_stopped()

        Thread(target=task, daemon=True).start()

    def stop(self):
        self.record_ctx.stop()

    def _run(
        self,
        transc_result_queue: MergingQueue[Pair],
        transl_result_queues: list[MergingQueue[Pair]],
    ):
        def transc_put(pair: Pair | None):
            transc_result_queue.put(pair)
            for transl_ctx in self.transl_ctxs:
                transl_ctx.buffer_queue.put(pair)

        transc_thread = Thread(target=lambda: self.transc_ctx.run(transc_put))

        def get_transl_thread(transl_ctx: TranslationContext, transl_result_queue: MergingQueue[Pair]):
            def transl_put(pair: Pair | None):
                transl_result_queue.put(pair)

            return Thread(target=lambda: transl_ctx.run(transl_put))

        transl_threads = [
            get_transl_thread(transl_ctx, transl_result_queue)
            for transl_ctx, transl_result_queue in
                zip(self.transl_ctxs, transl_result_queues, strict=True)
        ]

        transc_thread.start()
        for transl_thread in transl_threads:
            transl_thread.start()

        def record_put(data: Data | None):
            self.transc_ctx.buffer_queue.put(data)

        self.record_ctx.run(record_put)

        transc_thread.join()
        for transl_thread in transl_threads:
            transl_thread.join()

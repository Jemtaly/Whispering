from threading import Thread
from typing import Callable

from whispering.core.utils import MergingQueue, Pair, Data
from whispering.core.interfaces import (
    RecordingServiceFactory,
    TranscriptionServiceFactory,
    TranslationServiceFactory,
    Language,
)


class STTEngine:
    def __init__(
        self,
        record_factory: RecordingServiceFactory,
        sample_time: float,
        transc_factory: TranscriptionServiceFactory,
        transl_factory: TranslationServiceFactory,
        source_lang: Language | None,
        target_lang: Language | None,
        transc_result_queue: MergingQueue[Pair],
        transl_result_queue: MergingQueue[Pair],
        on_stopped: "Callable[[], None]",
        on_record_error: "Callable[[Exception], None]" = lambda _: None,
        on_transc_error: "Callable[[Exception], None]" = lambda _: None,
        on_transl_error: "Callable[[Exception], None]" = lambda _: None,
    ):
        self.transc_service = transc_factory.create(
            lang=source_lang,
        )
        self.transl_service = transl_factory.create(
            source_lang=source_lang,
            target_lang=target_lang,
        )
        self.record_service = record_factory.create(
            sample_type=self.transc_service.required_sample_type,
            sample_rate=self.transc_service.required_sample_rate,
            sample_time=sample_time,
        )
        self.is_running = False
        self.transc_result_queue = transc_result_queue
        self.transl_result_queue = transl_result_queue
        self.record_result_queue = MergingQueue[Data]()
        self.transc2transl_queue = MergingQueue[Pair]()
        self.on_stopped = on_stopped
        self.on_record_error = on_record_error
        self.on_transc_error = on_transc_error
        self.on_transl_error = on_transl_error

    @staticmethod
    def start(
        record_factory: RecordingServiceFactory,
        sample_time: float,
        transc_factory: TranscriptionServiceFactory,
        transl_factory: TranslationServiceFactory,
        source_lang: Language | None,
        target_lang: Language | None,
        transc_result_queue: MergingQueue[Pair],
        transl_result_queue: MergingQueue[Pair],
        on_failure: "Callable[[Exception], None]",
        on_success: "Callable[[STTEngine], None]",
        on_stopped: "Callable[[], None]",
        on_record_error: "Callable[[Exception], None]" = lambda _: None,
        on_transc_error: "Callable[[Exception], None]" = lambda _: None,
        on_transl_error: "Callable[[Exception], None]" = lambda _: None,
    ):
        def task():
            try:
                eng = STTEngine(
                    record_factory=record_factory,
                    sample_time=sample_time,
                    transc_factory=transc_factory,
                    transl_factory=transl_factory,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    transc_result_queue=transc_result_queue,
                    transl_result_queue=transl_result_queue,
                    on_stopped=on_stopped,
                    on_record_error=on_record_error,
                    on_transc_error=on_transc_error,
                    on_transl_error=on_transl_error,
                )
            except Exception as err:
                on_failure(err)
            else:
                on_success(eng)
                eng._run()

        Thread(target=task, daemon=True).start()

    def stop(self):
        self.is_running = False

    def _run(self):
        self.is_running = True
        record_thread = Thread(target=self._record_task)
        transc_thread = Thread(target=self._transc_task)
        transl_thread = Thread(target=self._transl_task)
        record_thread.start()
        transc_thread.start()
        transl_thread.start()
        record_thread.join()
        transc_thread.join()
        transl_thread.join()
        self.on_stopped()

    def _record_task(self):
        try:
            with self.record_service:
                while self.is_running:
                    self.record_result_queue.put(self.record_service.read())
        except Exception as err:
            self.on_record_error(err)
        finally:
            self.record_result_queue.put(None)

    def _transc_task(self):
        try:
            while frame := self.record_result_queue.get():
                src = self.transc_service.update(frame)
                self.transc2transl_queue.put(src)
                self.transc_result_queue.put(src)
        except Exception as err:
            self.on_transc_error(err)
        finally:
            self.transc2transl_queue.put(None)
            self.transc_result_queue.put(None)

    def _transl_task(self):
        try:
            while src := self.transc2transl_queue.get():
                tgt = self.transl_service.update(src)
                self.transl_result_queue.put(tgt)
        except Exception as err:
            self.on_transl_error(err)
        finally:
            self.transl_result_queue.put(None)

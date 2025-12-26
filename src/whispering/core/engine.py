from threading import Thread
from typing import Callable

from whispering.core.utils import MergingQueue, Pair, Data
from whispering.core.interfaces import MicFactory, TranscriptionFactory, TranslationFactory, Language


class Processor:
    def __init__(
        self,
        mic_factory: MicFactory,
        sample_time: float,
        ts_factory: TranscriptionFactory,
        tl_factory: TranslationFactory,
        source_lang: Language | None,
        target_lang: Language | None,
        tsres_queue: MergingQueue[Pair],
        tlres_queue: MergingQueue[Pair],
        on_stopped: "Callable[[], None]",
        on_cc_error: "Callable[[Exception], None]" = lambda _: None,
        on_ts_error: "Callable[[Exception], None]" = lambda _: None,
        on_tl_error: "Callable[[Exception], None]" = lambda _: None,
    ):
        self.ts_proc = ts_factory.create(
            lang=source_lang,
        )
        self.tl_proc = tl_factory.create(
            source_lang=source_lang,
            target_lang=target_lang,
        )
        self.mic = mic_factory.create(
            sample_type=self.ts_proc.required_sample_type,
            sample_rate=self.ts_proc.required_sample_rate,
            sample_time=sample_time,
        )
        self.is_running = False
        self.tsres_queue = tsres_queue
        self.tlres_queue = tlres_queue
        self.frame_queue = MergingQueue[Data]()
        self.ts2tl_queue = MergingQueue[Pair]()
        self.on_stopped = on_stopped
        self.on_cc_error = on_cc_error
        self.on_ts_error = on_ts_error
        self.on_tl_error = on_tl_error

    @staticmethod
    def start(
        mic_factory: MicFactory,
        sample_time: float,
        ts_factory: TranscriptionFactory,
        tl_factory: TranslationFactory,
        source_lang: Language | None,
        target_lang: Language | None,
        tsres_queue: MergingQueue[Pair],
        tlres_queue: MergingQueue[Pair],
        on_failure: "Callable[[Exception], None]",
        on_success: "Callable[[Processor], None]",
        on_stopped: "Callable[[], None]",
        on_cc_error: "Callable[[Exception], None]" = lambda _: None,
        on_ts_error: "Callable[[Exception], None]" = lambda _: None,
        on_tl_error: "Callable[[Exception], None]" = lambda _: None,
    ):
        def task():
            try:
                proc = Processor(
                    mic_factory=mic_factory,
                    sample_time=sample_time,
                    ts_factory=ts_factory,
                    tl_factory=tl_factory,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    tsres_queue=tsres_queue,
                    tlres_queue=tlres_queue,
                    on_stopped=on_stopped,
                    on_cc_error=on_cc_error,
                    on_ts_error=on_ts_error,
                    on_tl_error=on_tl_error,
                )
            except Exception as err:
                on_failure(err)
            else:
                on_success(proc)
                proc._run()

        Thread(target=task, daemon=True).start()

    def stop(self):
        self.is_running = False

    def _run(self):
        self.is_running = True
        cc_thread = Thread(target=self._cc_task)
        ts_thread = Thread(target=self._ts_task)
        tl_thread = Thread(target=self._tl_task)
        cc_thread.start()
        ts_thread.start()
        tl_thread.start()
        cc_thread.join()
        ts_thread.join()
        tl_thread.join()
        self.on_stopped()

    def _cc_task(self):
        try:
            with self.mic:
                while self.is_running:
                    self.frame_queue.put(self.mic.read())
        except Exception as err:
            self.on_cc_error(err)
        finally:
            self.frame_queue.put(None)

    def _ts_task(self):
        try:
            while frame := self.frame_queue.get():
                src = self.ts_proc.update(frame)
                self.ts2tl_queue.put(src)
                self.tsres_queue.put(src)
        except Exception as err:
            self.on_ts_error(err)
        finally:
            self.ts2tl_queue.put(None)
            self.tsres_queue.put(None)

    def _tl_task(self):
        try:
            while ts2tl := self.ts2tl_queue.get():
                tgt = self.tl_proc.update(ts2tl)
                self.tlres_queue.put(tgt)
        except Exception as err:
            self.on_tl_error(err)
        finally:
            self.tlres_queue.put(None)

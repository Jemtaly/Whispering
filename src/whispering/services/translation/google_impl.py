from urllib.parse import quote
import requests

from whispering.core.interfaces import (
    TranslationService,
    TranslationServiceFactory,
    CoreTranslationService,
    TranslationResult,
    Language,
)


class GoogleTranslationService(CoreTranslationService):
    def __init__(
        self,
        source_lang: Language | None,
        target_lang: Language | None,
        timeout: float,
    ):
        super().__init__()
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.timeout = timeout

    def translate(self, text: str) -> list[TranslationResult]:
        if self.target_lang is None:
            return [TranslationResult(text, "Target language is not specified.")]
        try:
            url = "https://translate.googleapis.com/translate_a/single?client=gtx&sl={sl}&tl={tl}&dt=t&q={q}".format(
                sl=self.source_lang or "auto",
                tl=self.target_lang,
                q=quote(text),
            )
            ans = requests.get(url, timeout=self.timeout).json()[0] or []
            return [TranslationResult(s, t) for t, s, *infos in ans]
        except Exception:
            return [TranslationResult(text, "Translation service is unavailable.")]


class GoogleTranslationServiceFactory(TranslationServiceFactory):
    def __init__(
        self,
        timeout: float,
    ):
        self.timeout = timeout

    def create(
        self,
        source_lang: Language | None,
        target_lang: Language | None,
    ) -> TranslationService:
        return GoogleTranslationService(
            source_lang=source_lang,
            target_lang=target_lang,
            timeout=self.timeout,
        )

from urllib.parse import quote
import requests

from whispering.core.interfaces import (
    TranslationService,
    TranslationServiceFactory,
    CoreTranslationService,
    TranslationResult,
    LanguageCode,
)


GOOGLE_LANGUAGE_CODES = {
    "af", "ach", "ak", "am", "ar", "az", "be", "bem", "bg", "bh",
    "bn", "br", "bs", "ca", "chr", "ckb", "co", "crs", "cs", "cy",
    "da", "de", "ee", "el", "en", "eo", "es", "es-419", "et", "eu",
    "fa", "fi", "fo", "fr", "fy", "ga", "gaa", "gd", "gl", "gn",
    "gu", "ha", "haw", "hi", "hr", "ht", "hu", "hy", "ia", "id",
    "ig", "is", "it", "iw", "ja", "jw", "ka", "kg", "kk", "km",
    "kn", "ko", "kri", "ku", "ky", "la", "lg", "ln", "lo", "loz",
    "lt", "lua", "lv", "mfe", "mg", "mi", "mk", "ml", "mn", "mo",
    "mr", "ms", "mt", "ne", "nl", "nn", "no", "nso", "ny", "nyn",
    "oc", "om", "or", "pa", "pcm", "pl", "ps", "pt", "pt-BR", "pt-PT",
    "qu", "rm", "rn", "ro", "ru", "rw", "sd", "sh", "si", "sk",
    "sl", "sn", "so", "sq", "sr", "sr-ME", "st", "su", "sv", "sw",
    "ta", "te", "tg", "th", "ti", "tk", "tl", "tn", "to", "tr",
    "tt", "tum", "tw", "ug", "uk", "ur", "uz", "vi", "wo", "xh",
    "xx", "xx-bork", "xx-elmer", "xx-hacker", "xx-klingon", "xx-pirate",
    "yi", "yo", "zh", "zh-CN", "zh-TW", "zu",
}
GOOGLE_SOURCE_LANGUAGE_CODES = GOOGLE_LANGUAGE_CODES
GOOGLE_TARGET_LANGUAGE_CODES = GOOGLE_LANGUAGE_CODES


class GoogleTranslationService(CoreTranslationService):
    def __init__(
        self,
        source_lang: LanguageCode | None,
        target_lang: LanguageCode | None,
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
        source_lang: LanguageCode | None,
        target_lang: LanguageCode | None,
    ) -> TranslationService:
        return GoogleTranslationService(
            source_lang=source_lang,
            target_lang=target_lang,
            timeout=self.timeout,
        )

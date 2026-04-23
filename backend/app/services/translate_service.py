"""
Google Translate wrapper using deep-translator (free, no API key required).
Translation is always user-confirmed before saving — never auto-applied.
"""

import logging
from deep_translator import GoogleTranslator

logger = logging.getLogger(__name__)

# ISO 639-1 codes supported for SMS fallback messages
SUPPORTED_LANGUAGES: dict[str, str] = {
    "hi": "Hindi",
    "te": "Telugu",
    "ta": "Tamil",
    "kn": "Kannada",
    "ml": "Malayalam",
    "mr": "Marathi",
    "bn": "Bengali",
    "gu": "Gujarati",
    "pa": "Punjabi",
    "ur": "Urdu",
    "fr": "French",
    "es": "Spanish",
    "de": "German",
    "ar": "Arabic",
    "zh-CN": "Chinese (Simplified)",
    "ja": "Japanese",
    "ko": "Korean",
    "pt": "Portuguese",
    "ru": "Russian",
    "it": "Italian",
}


def translate_text(text: str, target_lang: str) -> str:
    """Translate *text* from English to *target_lang*.

    Raises ValueError for unsupported language codes.
    Raises RuntimeError if the translation API call fails.
    """
    if not text or not text.strip():
        raise ValueError("Input text must not be empty.")
    if target_lang == "en":
        return text
    if target_lang not in SUPPORTED_LANGUAGES:
        raise ValueError(
            f"Unsupported language code '{target_lang}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_LANGUAGES))}"
        )
    try:
        translator = GoogleTranslator(source="en", target=target_lang)
        translated = translator.translate(text)
        logger.info(f"Translated text to '{target_lang}': {translated[:60]}…")
        return translated
    except Exception as exc:
        logger.error(f"Translation to '{target_lang}' failed: {exc}")
        raise RuntimeError(f"Translation failed: {exc}") from exc

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LanguageOption:
    code: str
    label: str
    english_name: str
    speech_code: str
    twilio_code: str
    direction: str = "ltr"


LANGUAGES: dict[str, LanguageOption] = {
    "auto": LanguageOption("auto", "Auto Detect", "the user's detected language", "hi-IN", "en-IN"),
    "hinglish": LanguageOption("hinglish", "Hinglish", "natural Hinglish", "hi-IN", "en-IN"),
    "hindi": LanguageOption("hindi", "Hindi", "Hindi", "hi-IN", "hi-IN"),
    "english": LanguageOption("english", "English", "English", "en-IN", "en-IN"),
    "punjabi": LanguageOption("punjabi", "Punjabi", "Punjabi", "pa-IN", "en-IN"),
    "marathi": LanguageOption("marathi", "Marathi", "Marathi", "mr-IN", "en-IN"),
    "telugu": LanguageOption("telugu", "Telugu", "Telugu", "te-IN", "en-IN"),
    "urdu": LanguageOption("urdu", "Urdu", "Urdu", "ur-PK", "en-IN", "rtl"),
    "french": LanguageOption("french", "French", "French", "fr-FR", "fr-FR"),
    "chinese": LanguageOption("chinese", "Chinese", "Simplified Chinese", "zh-CN", "zh-CN"),
}


def normalize_language(value: str | None, fallback: str = "hinglish") -> str:
    clean = (value or "").strip().lower().replace(" ", "_")
    aliases = {
        "hi": "hindi",
        "hin": "hindi",
        "en": "english",
        "eng": "english",
        "hing": "hinglish",
        "pa": "punjabi",
        "panjabi": "punjabi",
        "mr": "marathi",
        "te": "telugu",
        "urdu": "urdu",
        "ur": "urdu",
        "fr": "french",
        "french_france": "french",
        "zh": "chinese",
        "cn": "chinese",
        "mandarin": "chinese",
        "chinese_simplified": "chinese",
    }
    clean = aliases.get(clean, clean)
    if clean in LANGUAGES:
        return clean
    return fallback if fallback in LANGUAGES else "hinglish"


def language_option(code: str | None) -> LanguageOption:
    return LANGUAGES[normalize_language(code)]


def language_payload() -> list[dict[str, str]]:
    return [
        {
            "code": item.code,
            "label": item.label,
            "english_name": item.english_name,
            "speech_code": item.speech_code,
            "direction": item.direction,
        }
        for item in LANGUAGES.values()
    ]


def instruction_for_language(code: str | None, detected: str = "hinglish") -> str:
    normalized = normalize_language(code, fallback="auto")
    if normalized == "auto":
        normalized = normalize_language(detected, fallback="hinglish")
    option = LANGUAGES.get(normalized, LANGUAGES["hinglish"])
    if normalized == "hinglish":
        return "Reply in natural Hinglish using simple Hindi-English mix, matching the user's tone."
    if normalized == "urdu":
        return "Reply in Urdu. Use simple, supportive Urdu."
    if normalized == "chinese":
        return "Reply in Simplified Chinese. Keep the tone warm, professional and supportive."
    return f"Reply in {option.english_name}. Keep the tone warm, professional and supportive."

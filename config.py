import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


def _bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Config:
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-change-me")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///calmmind_pro.db")
    APP_BASE_URL: str = os.getenv("APP_BASE_URL", "http://127.0.0.1:5000")
    PUBLIC_BASE_URL: str = os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:5000")

    GROQ_API_KEY: str | None = os.getenv("GROQ_API_KEY") or None
    GROQ_CHAT_MODEL: str = os.getenv("GROQ_CHAT_MODEL", "llama-3.3-70b-versatile")
    GROQ_TTS_MODEL: str = os.getenv("GROQ_TTS_MODEL", "playai-tts")
    GROQ_TTS_VOICE: str = os.getenv("GROQ_TTS_VOICE", "Fritz-PlayAI")

    FIREBASE_SERVICE_ACCOUNT_PATH: str | None = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH") or None
    AUTH_MODE: str = os.getenv("AUTH_MODE", "demo").lower()

    TWILIO_ACCOUNT_SID: str | None = os.getenv("TWILIO_ACCOUNT_SID") or None
    TWILIO_AUTH_TOKEN: str | None = os.getenv("TWILIO_AUTH_TOKEN") or None
    TWILIO_PHONE_NUMBER: str | None = os.getenv("TWILIO_PHONE_NUMBER") or None

    ENABLE_ADMIN_DEMO: bool = _bool("ENABLE_ADMIN_DEMO", True)
    MAX_MESSAGE_CHARS: int = int(os.getenv("MAX_MESSAGE_CHARS", "4000"))


config = Config()

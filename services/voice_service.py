from __future__ import annotations

import base64
from config import config

try:
    from groq import Groq
except Exception:  # pragma: no cover
    Groq = None


def browser_voice_capabilities() -> dict:
    return {
        "mode": "browser_web_speech",
        "stt": "SpeechRecognition / webkitSpeechRecognition in supported browsers",
        "tts": "SpeechSynthesis in browser",
        "server_tts_available": bool(config.GROQ_API_KEY and Groq),
    }


def synthesize_speech_base64(text: str) -> dict:
    """Optional server TTS. Browser TTS is the default and needs no paid key."""
    if not config.GROQ_API_KEY or Groq is None:
        return {"available": False, "message": "Server TTS not configured. Browser SpeechSynthesis is active."}
    client = Groq(api_key=config.GROQ_API_KEY)
    try:
        response = client.audio.speech.create(
            model=config.GROQ_TTS_MODEL,
            voice=config.GROQ_TTS_VOICE,
            input=text[:1200],
            response_format="wav",
        )
        audio_bytes = response.read() if hasattr(response, "read") else bytes(response)
        return {"available": True, "mime_type": "audio/wav", "audio_base64": base64.b64encode(audio_bytes).decode("utf-8")}
    except Exception as exc:
        return {"available": False, "message": str(exc)}

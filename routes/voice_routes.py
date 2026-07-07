from __future__ import annotations

from flask import Blueprint, jsonify, request
from services.auth_service import get_user_id_from_request
from services.ai_service import build_ai_reply
from services.voice_service import browser_voice_capabilities, synthesize_speech_base64
from services.language_service import normalize_language

voice_bp = Blueprint("voice", __name__, url_prefix="/api/voice")


@voice_bp.get("/capabilities")
def capabilities():
    return jsonify(browser_voice_capabilities())


@voice_bp.post("/message")
def voice_message():
    user_id = get_user_id_from_request(request)
    payload = request.get_json(silent=True) or {}
    transcript = (payload.get("transcript") or payload.get("message") or "").strip()
    if not transcript:
        return jsonify({"error": "Voice transcript is required."}), 400
    preferred_language = normalize_language(payload.get("preferred_language"), fallback="auto")
    return jsonify(build_ai_reply(user_id=user_id, message=transcript, session_id=payload.get("session_id"), input_type="voice", preferred_language=preferred_language))


@voice_bp.post("/speak")
def speak():
    payload = request.get_json(silent=True) or {}
    text = (payload.get("text") or "").strip()
    if not text:
        return jsonify({"error": "Text is required."}), 400
    return jsonify(synthesize_speech_base64(text))

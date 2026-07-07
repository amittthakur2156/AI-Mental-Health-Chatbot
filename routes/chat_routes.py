from __future__ import annotations

from flask import Blueprint, jsonify, request

from services.ai_service import analyze_message_only, build_ai_reply
from services.auth_service import get_user_id_from_request
from services.db_service import (
    create_session,
    delete_session,
    execute,
    fetch_all,
    get_session_with_messages,
    list_sessions,
    rename_session,
)
from services.language_service import language_payload, normalize_language
from services.memory_service import get_memory_profile, reset_memory, update_memory_preferences

chat_bp = Blueprint("chat", __name__, url_prefix="/api")


def _session_payload(user_id: str):
    return list_sessions(user_id=user_id, limit=50)


@chat_bp.post("/chat")
def chat():
    user_id = get_user_id_from_request(request)
    payload = request.get_json(silent=True) or {}
    message = (payload.get("message") or "").strip()
    session_id = payload.get("session_id")
    input_type = (payload.get("input_type") or "text").strip().lower()
    preferred_language = normalize_language(payload.get("preferred_language"), fallback="auto")
    if not message:
        return jsonify({"error": "Message is required."}), 400
    result = build_ai_reply(user_id=user_id, message=message, session_id=session_id, input_type=input_type, preferred_language=preferred_language)
    result["sessions"] = _session_payload(user_id)
    return jsonify(result)


@chat_bp.get("/languages")
def languages():
    return jsonify({"languages": language_payload()})


@chat_bp.post("/brain/analyze")
def brain_analyze():
    payload = request.get_json(silent=True) or {}
    message = (payload.get("message") or "").strip()
    preferred_language = normalize_language(payload.get("preferred_language"), fallback="auto")
    if not message:
        return jsonify({"error": "Message is required."}), 400
    return jsonify(analyze_message_only(message, preferred_language=preferred_language))


@chat_bp.get("/memory/profile")
def memory_profile():
    user_id = get_user_id_from_request(request)
    return jsonify(get_memory_profile(user_id))


@chat_bp.patch("/memory/profile")
def update_memory_profile():
    user_id = get_user_id_from_request(request)
    payload = request.get_json(silent=True) or {}
    return jsonify(update_memory_preferences(user_id, payload))


@chat_bp.delete("/memory/profile")
def clear_memory_profile():
    user_id = get_user_id_from_request(request)
    reset_memory(user_id)
    return jsonify({"ok": True, "memory": get_memory_profile(user_id)})


@chat_bp.post("/session/new")
def new_session():
    user_id = get_user_id_from_request(request)
    payload = request.get_json(silent=True) or {}
    title = (payload.get("title") or "New Support Session").strip()[:80]
    session_id = create_session(user_id=user_id, title=title)
    data = get_session_with_messages(user_id, session_id)
    return jsonify({"ok": True, "session_id": session_id, **(data or {}), "sessions": _session_payload(user_id)})


@chat_bp.get("/session/<int:session_id>")
def get_session(session_id: int):
    user_id = get_user_id_from_request(request)
    data = get_session_with_messages(user_id, session_id)
    if not data:
        return jsonify({"error": "Session not found."}), 404
    return jsonify({"session_id": session_id, **data})


@chat_bp.patch("/session/<int:session_id>")
def update_session(session_id: int):
    user_id = get_user_id_from_request(request)
    payload = request.get_json(silent=True) or {}
    title = (payload.get("title") or "").strip()
    if not title:
        return jsonify({"error": "Title is required."}), 400
    if not rename_session(user_id=user_id, session_id=session_id, title=title):
        return jsonify({"error": "Session not found."}), 404
    return jsonify({"ok": True, "sessions": _session_payload(user_id)})


@chat_bp.delete("/session/<int:session_id>")
def remove_session(session_id: int):
    user_id = get_user_id_from_request(request)
    if not delete_session(user_id=user_id, session_id=session_id):
        return jsonify({"error": "Session not found."}), 404
    return jsonify({"ok": True, "sessions": _session_payload(user_id)})


@chat_bp.get("/history")
def history():
    user_id = get_user_id_from_request(request)
    session_id = request.args.get("session_id", type=int)
    if session_id:
        data = get_session_with_messages(user_id, session_id)
        if not data:
            return jsonify({"error": "Session not found."}), 404
        return jsonify({"session_id": session_id, **data})
    return jsonify({"sessions": _session_payload(user_id)})


@chat_bp.delete("/history")
def delete_history():
    user_id = get_user_id_from_request(request)
    session_id = request.args.get("session_id", type=int)
    if session_id:
        delete_session(user_id=user_id, session_id=session_id)
    else:
        # Child rows first so old local SQLite databases do not hit FK errors.
        execute("DELETE FROM conversation_insights WHERE user_id=?", (user_id,))
        execute("DELETE FROM voice_transcripts WHERE user_id=?", (user_id,))
        execute("DELETE FROM risk_events WHERE user_id=?", (user_id,))
        execute("DELETE FROM messages WHERE user_id=?", (user_id,))
        execute("DELETE FROM mood_logs WHERE user_id=?", (user_id,))
        execute("DELETE FROM chat_sessions WHERE user_id=?", (user_id,))
    return jsonify({"ok": True, "sessions": _session_payload(user_id)})


@chat_bp.get("/export")
def export_user_data():
    user_id = get_user_id_from_request(request)
    return jsonify({
        "user_id": user_id,
        "memory": get_memory_profile(user_id),
        "sessions": fetch_all("SELECT * FROM chat_sessions WHERE user_id=?", (user_id,)),
        "messages": fetch_all("SELECT * FROM messages WHERE user_id=?", (user_id,)),
        "conversation_insights": fetch_all("SELECT * FROM conversation_insights WHERE user_id=?", (user_id,)),
        "mood_logs": fetch_all("SELECT * FROM mood_logs WHERE user_id=?", (user_id,)),
        "journals": fetch_all("SELECT * FROM journals WHERE user_id=?", (user_id,)),
        "safety_plan": fetch_all("SELECT * FROM safety_plans WHERE user_id=?", (user_id,)),
        "risk_events": fetch_all("SELECT * FROM risk_events WHERE user_id=?", (user_id,)),
    })

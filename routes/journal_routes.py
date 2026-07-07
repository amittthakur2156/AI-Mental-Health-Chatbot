from __future__ import annotations

from flask import Blueprint, jsonify, request
from services.auth_service import get_user_id_from_request
from services.ai_service import summarize_journal
from services.db_service import execute, fetch_all, utc_now, ensure_user
from services.mood_service import analyze_mood

journal_bp = Blueprint("journal", __name__, url_prefix="/api")


@journal_bp.post("/journal")
def create_journal():
    user_id = get_user_id_from_request(request)
    ensure_user(user_id)
    payload = request.get_json(silent=True) or {}
    content = (payload.get("content") or "").strip()
    if not content:
        return jsonify({"error": "Journal content is required."}), 400
    title = (payload.get("title") or "Daily Reflection").strip()
    gratitude = (payload.get("gratitude") or "").strip()
    mood = analyze_mood(content + " " + gratitude)
    summary = summarize_journal(content, gratitude)
    journal_id = execute(
        """
        INSERT INTO journals(user_id, title, content, gratitude, mood_score, ai_summary, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (user_id, title, content, gratitude, mood.mood_score, summary, utc_now()),
    )
    execute(
        "INSERT INTO mood_logs(user_id, score, emotion, source, note, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, mood.mood_score, mood.emotion, "journal", content[:250], utc_now()),
    )
    return jsonify({"id": journal_id, "summary": summary, "mood_score": mood.mood_score, "emotion": mood.emotion})


@journal_bp.get("/journal")
def list_journals():
    user_id = get_user_id_from_request(request)
    rows = fetch_all("SELECT * FROM journals WHERE user_id=? ORDER BY id DESC LIMIT 50", (user_id,))
    return jsonify({"journals": rows})


@journal_bp.delete("/journal/<int:journal_id>")
def delete_journal(journal_id: int):
    user_id = get_user_id_from_request(request)
    execute("DELETE FROM journals WHERE id=? AND user_id=?", (journal_id, user_id))
    return jsonify({"ok": True})

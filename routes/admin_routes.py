from __future__ import annotations

import json

from flask import Blueprint, jsonify, request
from services.db_service import acknowledge_risk_event, fetch_all, fetch_one

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


def _count(query: str, params=()) -> int:
    return int((fetch_one(query, params) or {"c": 0})["c"] or 0)


@admin_bp.get("/analytics")
def analytics():
    totals = {
        "users": _count("SELECT COUNT(*) AS c FROM users"),
        "messages": _count("SELECT COUNT(*) AS c FROM messages"),
        "journals": _count("SELECT COUNT(*) AS c FROM journals"),
        "risk_events": _count("SELECT COUNT(*) AS c FROM risk_events"),
        "high_risk_events": _count("SELECT COUNT(*) AS c FROM risk_events WHERE risk_level IN ('high','emergency')"),
        "medium_risk_events": _count("SELECT COUNT(*) AS c FROM risk_events WHERE risk_level='medium'"),
        "unacknowledged_risk_events": _count("SELECT COUNT(*) AS c FROM risk_events WHERE acknowledged=0 AND risk_level IN ('high','emergency')"),
        "voice_sessions": _count("SELECT COUNT(*) AS c FROM voice_transcripts"),
        "call_sessions": _count("SELECT COUNT(*) AS c FROM call_sessions"),
        "crisis_checkins": _count("SELECT COUNT(*) AS c FROM crisis_checkins"),
        "safety_plans": _count("SELECT COUNT(*) AS c FROM safety_plans"),
    }
    emotion_counts = fetch_all("SELECT emotion, COUNT(*) AS count FROM mood_logs GROUP BY emotion ORDER BY count DESC")
    risk_counts = fetch_all("SELECT risk_level, COUNT(*) AS count FROM risk_events GROUP BY risk_level ORDER BY count DESC")
    category_counts = fetch_all(
        """
        SELECT categories, COUNT(*) AS count
        FROM risk_events
        WHERE categories IS NOT NULL AND categories != ''
        GROUP BY categories
        ORDER BY count DESC
        LIMIT 12
        """
    )
    avg = fetch_one("SELECT ROUND(AVG(score), 2) AS avg_mood FROM mood_logs") or {"avg_mood": None}
    avg_risk = fetch_one("SELECT ROUND(AVG(risk_score), 2) AS avg_risk FROM risk_events") or {"avg_risk": None}
    latest = fetch_one(
        """
        SELECT id, user_id, risk_level, risk_score, urgency, recommended_action, created_at
        FROM risk_events ORDER BY id DESC LIMIT 1
        """
    )
    return jsonify({
        "totals": totals,
        "avg_mood": avg["avg_mood"],
        "avg_risk": avg_risk["avg_risk"],
        "emotion_counts": emotion_counts,
        "risk_counts": risk_counts,
        "category_counts": category_counts,
        "latest_risk_event": latest,
    })


@admin_bp.get("/risk-events")
def risk_events():
    risk_level = request.args.get("risk_level")
    params = []
    where = ""
    if risk_level:
        where = "WHERE risk_level=?"
        params.append(risk_level)
    rows = fetch_all(
        f"""
        SELECT id, user_id, risk_level, risk_score, categories, recommended_action, urgency,
               follow_up_required, acknowledged, substr(content, 1, 180) AS content_preview,
               substr(safety_response, 1, 220) AS safety_response_preview, created_at
        FROM risk_events
        {where}
        ORDER BY id DESC LIMIT 100
        """,
        tuple(params),
    )
    for row in rows:
        try:
            row["categories_list"] = json.loads(row.get("categories") or "[]")
        except Exception:
            row["categories_list"] = []
    return jsonify({"risk_events": rows})


@admin_bp.patch("/risk-events/<int:event_id>/acknowledge")
def acknowledge_event(event_id: int):
    ok = acknowledge_risk_event(event_id)
    return jsonify({"ok": ok})


@admin_bp.get("/crisis-checkins")
def admin_crisis_checkins():
    rows = fetch_all(
        """
        SELECT id, user_id, safe_status, contact_person, current_location, risk_level, risk_score, created_at
        FROM crisis_checkins ORDER BY id DESC LIMIT 100
        """
    )
    return jsonify({"checkins": rows})

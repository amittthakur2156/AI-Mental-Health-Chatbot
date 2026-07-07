from __future__ import annotations

import csv
import io
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from services.db_service import fetch_all, fetch_one


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _date_days_ago(days: int) -> str:
    days = max(1, min(int(days or 30), 365))
    return (_utc_now() - timedelta(days=days - 1)).date().isoformat()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return round(float(value), 2)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _mood_label(avg_mood: float) -> str:
    if avg_mood >= 8:
        return "positive"
    if avg_mood >= 6:
        return "stable"
    if avg_mood >= 4:
        return "low"
    if avg_mood > 0:
        return "very_low"
    return "not_enough_data"


def _trend_direction(rows: list[dict[str, Any]]) -> str:
    if len(rows) < 2:
        return "not_enough_data"
    first = _safe_float(rows[0].get("avg_score"))
    last = _safe_float(rows[-1].get("avg_score"))
    delta = last - first
    if delta >= 0.8:
        return "improving"
    if delta <= -0.8:
        return "declining"
    return "stable"


def _top_value(rows: list[dict[str, Any]], key: str, fallback: str = "none") -> str:
    if not rows:
        return fallback
    return str(rows[0].get(key) or fallback)


def get_summary(user_id: str, days: int = 30) -> dict[str, Any]:
    """Dashboard summary cards for Phase 4.

    Keeps Phase 1/2 compatible response keys (`stats`, `emotions`, `risk_events`,
    `journals`) and adds richer cards/insights for the advanced dashboard.
    """
    since = _date_days_ago(days)

    stats = fetch_one(
        """
        SELECT COUNT(*) AS total_logs,
               ROUND(AVG(score), 2) AS avg_mood,
               MIN(score) AS lowest_mood,
               MAX(score) AS highest_mood
        FROM mood_logs
        WHERE user_id=?
        """,
        (user_id,),
    ) or {}

    period_stats = fetch_one(
        """
        SELECT COUNT(*) AS total_logs,
               ROUND(AVG(score), 2) AS avg_mood,
               MIN(score) AS lowest_mood,
               MAX(score) AS highest_mood
        FROM mood_logs
        WHERE user_id=? AND substr(created_at, 1, 10) >= ?
        """,
        (user_id, since),
    ) or {}

    emotions = fetch_all(
        """
        SELECT COALESCE(NULLIF(emotion, ''), 'neutral') AS emotion, COUNT(*) AS count
        FROM mood_logs
        WHERE user_id=?
        GROUP BY COALESCE(NULLIF(emotion, ''), 'neutral')
        ORDER BY count DESC, emotion ASC
        """,
        (user_id,),
    )

    intents = fetch_all(
        """
        SELECT COALESCE(NULLIF(intent, ''), 'support') AS intent, COUNT(*) AS count
        FROM mood_logs
        WHERE user_id=?
        GROUP BY COALESCE(NULLIF(intent, ''), 'support')
        ORDER BY count DESC, intent ASC
        LIMIT 8
        """,
        (user_id,),
    )

    triggers = fetch_all(
        """
        SELECT COALESCE(NULLIF(trigger_text, ''), 'none') AS trigger_text, COUNT(*) AS count
        FROM mood_logs
        WHERE user_id=? AND trigger_text IS NOT NULL AND trigger_text != '' AND trigger_text != '[]'
        GROUP BY trigger_text
        ORDER BY count DESC
        LIMIT 8
        """,
        (user_id,),
    )

    risk_total = fetch_one("SELECT COUNT(*) AS total FROM risk_events WHERE user_id=?", (user_id,)) or {"total": 0}
    high_risk = fetch_one(
        """
        SELECT COUNT(*) AS total
        FROM risk_events
        WHERE user_id=? AND risk_level IN ('high', 'emergency')
        """,
        (user_id,),
    ) or {"total": 0}
    period_risk = fetch_one(
        """
        SELECT COUNT(*) AS total
        FROM risk_events
        WHERE user_id=? AND substr(created_at, 1, 10) >= ?
        """,
        (user_id, since),
    ) or {"total": 0}

    journal_count = fetch_one("SELECT COUNT(*) AS total FROM journals WHERE user_id=?", (user_id,)) or {"total": 0}
    voice_count = fetch_one("SELECT COUNT(*) AS total FROM voice_transcripts WHERE user_id=?", (user_id,)) or {"total": 0}
    chat_count = fetch_one(
        """
        SELECT COUNT(*) AS total
        FROM messages
        WHERE user_id=? AND role='user'
        """,
        (user_id,),
    ) or {"total": 0}
    sessions = fetch_one("SELECT COUNT(*) AS total FROM chat_sessions WHERE user_id=?", (user_id,)) or {"total": 0}

    streak_rows = fetch_all(
        """
        SELECT DISTINCT substr(created_at, 1, 10) AS day
        FROM mood_logs
        WHERE user_id=?
        ORDER BY day DESC
        LIMIT 90
        """,
        (user_id,),
    )
    active_streak = _calculate_streak([r["day"] for r in streak_rows])

    avg_mood = _safe_float(stats.get("avg_mood"))
    period_avg = _safe_float(period_stats.get("avg_mood"))
    return {
        "days": days,
        "stats": {
            "total_logs": _safe_int(stats.get("total_logs")),
            "avg_mood": avg_mood if avg_mood else None,
            "lowest_mood": stats.get("lowest_mood"),
            "highest_mood": stats.get("highest_mood"),
        },
        "period_stats": {
            "total_logs": _safe_int(period_stats.get("total_logs")),
            "avg_mood": period_avg if period_avg else None,
            "lowest_mood": period_stats.get("lowest_mood"),
            "highest_mood": period_stats.get("highest_mood"),
        },
        "cards": {
            "avg_mood": avg_mood if avg_mood else None,
            "period_avg_mood": period_avg if period_avg else None,
            "mood_label": _mood_label(avg_mood),
            "total_logs": _safe_int(stats.get("total_logs")),
            "chat_messages": _safe_int(chat_count.get("total")),
            "sessions": _safe_int(sessions.get("total")),
            "voice_sessions": _safe_int(voice_count.get("total")),
            "journals": _safe_int(journal_count.get("total")),
            "risk_events": _safe_int(risk_total.get("total")),
            "period_risk_events": _safe_int(period_risk.get("total")),
            "high_risk_events": _safe_int(high_risk.get("total")),
            "active_streak": active_streak,
            "top_emotion": _top_value(emotions, "emotion", "neutral"),
            "top_intent": _top_value(intents, "intent", "support"),
        },
        "emotions": emotions,
        "intents": intents,
        "triggers": triggers,
        "risk_events": _safe_int(risk_total.get("total")),
        "journals": _safe_int(journal_count.get("total")),
    }


def get_trends(user_id: str, days: int = 30) -> list[dict[str, Any]]:
    since = _date_days_ago(days)
    rows = fetch_all(
        """
        SELECT substr(created_at, 1, 10) AS date,
               ROUND(AVG(score), 2) AS avg_score,
               MIN(score) AS min_score,
               MAX(score) AS max_score,
               COUNT(*) AS count
        FROM mood_logs
        WHERE user_id=? AND substr(created_at, 1, 10) >= ?
        GROUP BY substr(created_at, 1, 10)
        ORDER BY date ASC
        """,
        (user_id, since),
    )
    return rows


def get_emotion_distribution(user_id: str, days: int = 30) -> list[dict[str, Any]]:
    since = _date_days_ago(days)
    return fetch_all(
        """
        SELECT COALESCE(NULLIF(emotion, ''), 'neutral') AS emotion, COUNT(*) AS count
        FROM mood_logs
        WHERE user_id=? AND substr(created_at, 1, 10) >= ?
        GROUP BY COALESCE(NULLIF(emotion, ''), 'neutral')
        ORDER BY count DESC, emotion ASC
        """,
        (user_id, since),
    )


def get_activity(user_id: str, days: int = 30) -> list[dict[str, Any]]:
    since = _date_days_ago(days)
    return fetch_all(
        """
        SELECT day,
               SUM(chat_count) AS chat_count,
               SUM(voice_count) AS voice_count,
               SUM(journal_count) AS journal_count
        FROM (
            SELECT substr(created_at, 1, 10) AS day, COUNT(*) AS chat_count, 0 AS voice_count, 0 AS journal_count
            FROM messages
            WHERE user_id=? AND role='user' AND substr(created_at, 1, 10) >= ?
            GROUP BY substr(created_at, 1, 10)
            UNION ALL
            SELECT substr(created_at, 1, 10) AS day, 0 AS chat_count, COUNT(*) AS voice_count, 0 AS journal_count
            FROM voice_transcripts
            WHERE user_id=? AND substr(created_at, 1, 10) >= ?
            GROUP BY substr(created_at, 1, 10)
            UNION ALL
            SELECT substr(created_at, 1, 10) AS day, 0 AS chat_count, 0 AS voice_count, COUNT(*) AS journal_count
            FROM journals
            WHERE user_id=? AND substr(created_at, 1, 10) >= ?
            GROUP BY substr(created_at, 1, 10)
        ) grouped
        GROUP BY day
        ORDER BY day ASC
        """,
        (user_id, since, user_id, since, user_id, since),
    )


def get_risk_trends(user_id: str, days: int = 30) -> list[dict[str, Any]]:
    since = _date_days_ago(days)
    return fetch_all(
        """
        SELECT substr(created_at, 1, 10) AS date,
               COALESCE(NULLIF(risk_level, ''), 'low') AS risk_level,
               COUNT(*) AS count,
               ROUND(AVG(COALESCE(risk_score, 0)), 2) AS avg_risk_score
        FROM risk_events
        WHERE user_id=? AND substr(created_at, 1, 10) >= ?
        GROUP BY substr(created_at, 1, 10), COALESCE(NULLIF(risk_level, ''), 'low')
        ORDER BY date ASC
        """,
        (user_id, since),
    )


def get_heatmap(user_id: str, days: int = 90) -> list[dict[str, Any]]:
    since = _date_days_ago(days)
    rows = fetch_all(
        """
        SELECT substr(created_at, 1, 10) AS date,
               ROUND(AVG(score), 2) AS avg_score,
               COUNT(*) AS count
        FROM mood_logs
        WHERE user_id=? AND substr(created_at, 1, 10) >= ?
        GROUP BY substr(created_at, 1, 10)
        ORDER BY date DESC
        """,
        (user_id, since),
    )
    for row in rows:
        score = _safe_float(row.get("avg_score"))
        if score >= 8:
            row["level"] = "great"
        elif score >= 6:
            row["level"] = "good"
        elif score >= 4:
            row["level"] = "low"
        else:
            row["level"] = "very-low"
    return rows


def get_weekly_report(user_id: str, days: int = 7) -> dict[str, Any]:
    days = max(7, min(int(days or 7), 30))
    trends = get_trends(user_id, days)
    emotions = get_emotion_distribution(user_id, days)
    risk_trends = get_risk_trends(user_id, days)
    activity = get_activity(user_id, days)
    summary = get_summary(user_id, days)

    total_mood_logs = sum(_safe_int(row.get("count")) for row in trends)
    avg = _safe_float(sum(_safe_float(row.get("avg_score")) * _safe_int(row.get("count")) for row in trends) / total_mood_logs) if total_mood_logs else 0
    high_risk_count = sum(_safe_int(row.get("count")) for row in risk_trends if row.get("risk_level") in {"high", "emergency"})
    top_emotion = _top_value(emotions, "emotion", "neutral")
    direction = _trend_direction(trends)

    insights = []
    if total_mood_logs == 0:
        insights.append("Not enough mood data yet. Start with 2-3 check-ins or chats this week.")
    else:
        insights.append(f"Your average mood for this period is {avg}/10 and the trend is {direction}.")
        insights.append(f"Most common emotion detected: {top_emotion}.")
    if high_risk_count:
        insights.append(f"{high_risk_count} high-risk safety event(s) were detected. Review your safety plan and trusted contacts.")
    elif total_mood_logs:
        insights.append("No high-risk safety events were detected in this period.")

    recommendations = _recommendations(avg, top_emotion, high_risk_count, summary.get("cards", {}).get("top_intent"))
    return {
        "days": days,
        "avg_mood": avg if avg else None,
        "top_emotion": top_emotion,
        "trend_direction": direction,
        "high_risk_count": high_risk_count,
        "activity_total": sum(_safe_int(r.get("chat_count")) + _safe_int(r.get("voice_count")) + _safe_int(r.get("journal_count")) for r in activity),
        "insights": insights,
        "recommendations": recommendations,
        "summary_cards": summary.get("cards", {}),
    }


def export_rows(user_id: str) -> list[dict[str, Any]]:
    mood_rows = fetch_all(
        """
        SELECT 'mood' AS record_type, created_at, score AS mood_score, emotion, intent, source, note, trigger_text, NULL AS risk_level, NULL AS risk_score
        FROM mood_logs WHERE user_id=?
        UNION ALL
        SELECT 'risk' AS record_type, created_at, NULL AS mood_score, NULL AS emotion, NULL AS intent, NULL AS source, substr(content, 1, 250) AS note, categories AS trigger_text, risk_level, risk_score
        FROM risk_events WHERE user_id=?
        ORDER BY created_at DESC
        """,
        (user_id, user_id),
    )
    return mood_rows


def export_csv(user_id: str) -> str:
    rows = export_rows(user_id)
    output = io.StringIO()
    fieldnames = ["record_type", "created_at", "mood_score", "emotion", "intent", "source", "note", "trigger_text", "risk_level", "risk_score"]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow({key: row.get(key, "") for key in fieldnames})
    return output.getvalue()


def _calculate_streak(days: list[str]) -> int:
    day_set = set(days)
    if not day_set:
        return 0
    cursor = _utc_now().date()
    # If no activity today, allow yesterday as current streak anchor.
    if cursor.isoformat() not in day_set:
        cursor -= timedelta(days=1)
    streak = 0
    while cursor.isoformat() in day_set:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def _recommendations(avg: float, emotion: str, high_risk_count: int, top_intent: str | None) -> list[str]:
    recs: list[str] = []
    if high_risk_count:
        recs.append("Review your safety plan today and keep one trusted contact easily reachable.")
    if avg and avg < 4:
        recs.append("Use one short grounding exercise and consider speaking with a trusted person or professional support.")
    elif avg and avg < 6:
        recs.append("Try a 5-minute breathing exercise and one small achievable task today.")
    elif avg:
        recs.append("Keep the routine that is helping; add a short journal reflection to maintain awareness.")
    else:
        recs.append("Start with one mood check-in or journal entry to build your weekly report.")

    if emotion in {"anxious", "panic", "stressed"}:
        recs.append("Use 4-4-6 breathing or the 5-4-3-2-1 grounding technique when anxiety rises.")
    if top_intent in {"study_stress", "career_confusion", "productivity"}:
        recs.append("Break work into 25-minute focus blocks with 5-minute recovery breaks.")
    if emotion in {"sad", "lonely"}:
        recs.append("Send a simple check-in message to someone safe: ‘Can we talk for a few minutes?’")
    return recs[:4]

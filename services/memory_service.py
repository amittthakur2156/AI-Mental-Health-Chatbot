from __future__ import annotations

import json
from typing import Any

from services.db_service import ensure_user, execute, fetch_one, utc_now


def _loads(value: str | None, default):
    if not value:
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


def _dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def ensure_memory(user_id: str) -> None:
    ensure_user(user_id)
    now = utc_now()
    execute(
        """
        INSERT OR IGNORE INTO user_memory(
            user_id, preferred_language, common_emotions, common_intents, common_triggers,
            helpful_tools, last_emotion, last_intent, last_mood_score, summary, updated_at
        ) VALUES (?, 'hinglish', '{}', '{}', '[]', '[]', 'neutral', 'mental_health_support', 5, '', ?)
        """,
        (user_id, now),
    )


def get_memory_profile(user_id: str) -> dict[str, Any]:
    ensure_memory(user_id)
    row = fetch_one("SELECT * FROM user_memory WHERE user_id=?", (user_id,)) or {}
    row["common_emotions"] = _loads(row.get("common_emotions"), {})
    row["common_intents"] = _loads(row.get("common_intents"), {})
    row["common_triggers"] = _loads(row.get("common_triggers"), [])
    row["helpful_tools"] = _loads(row.get("helpful_tools"), [])
    return row


def _increment_counter(counter: dict[str, int], key: str) -> dict[str, int]:
    if key:
        counter[key] = int(counter.get(key, 0)) + 1
    return dict(sorted(counter.items(), key=lambda kv: kv[1], reverse=True)[:8])


def _merge_list(current: list[str], new_items: list[str], limit: int = 10) -> list[str]:
    merged = list(dict.fromkeys([*(current or []), *(new_items or [])]))
    return merged[-limit:]


def update_memory_from_analysis(user_id: str, mood, safety) -> dict[str, Any]:
    ensure_memory(user_id)
    profile = get_memory_profile(user_id)

    emotions = _increment_counter(profile.get("common_emotions", {}), mood.emotion)
    intents = _increment_counter(profile.get("common_intents", {}), mood.intent)
    triggers = _merge_list(profile.get("common_triggers", []), mood.triggers)
    tools = _merge_list(profile.get("helpful_tools", []), [mood.recommended_tool])

    summary_bits = []
    if triggers:
        summary_bits.append("Common triggers: " + ", ".join(triggers[-4:]))
    if emotions:
        summary_bits.append("Frequent emotions: " + ", ".join(list(emotions.keys())[:3]))
    if tools:
        summary_bits.append("Helpful tools: " + ", ".join(tools[-3:]))
    summary = " | ".join(summary_bits)[:500]

    execute(
        """
        UPDATE user_memory
        SET preferred_language=?, common_emotions=?, common_intents=?, common_triggers=?, helpful_tools=?,
            last_emotion=?, last_intent=?, last_mood_score=?, risk_pattern=?, summary=?, updated_at=?
        WHERE user_id=?
        """,
        (
            mood.language,
            _dumps(emotions),
            _dumps(intents),
            _dumps(triggers),
            _dumps(tools),
            mood.emotion,
            mood.intent,
            mood.mood_score,
            safety.risk_level,
            summary,
            utc_now(),
            user_id,
        ),
    )
    return get_memory_profile(user_id)


def update_memory_preferences(user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    ensure_memory(user_id)
    allowed = {
        "preferred_language": payload.get("preferred_language"),
        "summary": payload.get("summary"),
    }
    allowed = {k: v for k, v in allowed.items() if v is not None}
    if allowed:
        sets = ", ".join(f"{key}=?" for key in allowed)
        params = list(allowed.values()) + [utc_now(), user_id]
        execute(f"UPDATE user_memory SET {sets}, updated_at=? WHERE user_id=?", params)
    return get_memory_profile(user_id)


def reset_memory(user_id: str) -> None:
    ensure_user(user_id)
    execute("DELETE FROM user_memory WHERE user_id=?", (user_id,))
    ensure_memory(user_id)

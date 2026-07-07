from __future__ import annotations

import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

_DB_PATH = "calmmind_pro.db"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _path_from_url(database_url: str) -> str:
    if database_url.startswith("sqlite:///"):
        return database_url.replace("sqlite:///", "", 1)
    return database_url


def _ensure_columns(conn: sqlite3.Connection, table: str, columns: dict[str, str]) -> None:
    existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    for name, definition in columns.items():
        if name not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")


def init_db(database_url: str = "sqlite:///calmmind_pro.db") -> None:
    """Create and migrate the local SQLite schema used by CalmMind Pro.

    Phase 3 keeps Phase 1/2 data and adds stronger crisis-safety
    planning, risk audit metadata, and crisis check-in storage while
    staying backward compatible with existing local databases.
    """
    global _DB_PATH
    _DB_PATH = _path_from_url(database_url)
    parent = Path(_DB_PATH).parent
    if str(parent) not in {"", "."}:
        parent.mkdir(parents=True, exist_ok=True)

    with get_conn() as conn:
        conn.executescript(
            """
            PRAGMA foreign_keys = ON;

            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                display_name TEXT,
                preferred_language TEXT DEFAULT 'hinglish',
                consent INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS chat_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                title TEXT DEFAULT 'New Support Session',
                summary TEXT,
                started_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
                content TEXT NOT NULL,
                emotion TEXT,
                intent TEXT,
                risk_level TEXT,
                mood_score INTEGER,
                input_type TEXT DEFAULT 'text',
                created_at TEXT NOT NULL,
                FOREIGN KEY(session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS mood_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                score INTEGER NOT NULL,
                emotion TEXT,
                source TEXT DEFAULT 'chat',
                note TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS journals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                title TEXT,
                content TEXT NOT NULL,
                gratitude TEXT,
                mood_score INTEGER,
                ai_summary TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS safety_plans (
                user_id TEXT PRIMARY KEY,
                warning_signs TEXT,
                coping_actions TEXT,
                trusted_contacts TEXT,
                safe_places TEXT,
                emergency_notes TEXT,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS risk_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                session_id INTEGER,
                message_id INTEGER,
                risk_level TEXT NOT NULL,
                content TEXT NOT NULL,
                safety_response TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(user_id),
                FOREIGN KEY(session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE,
                FOREIGN KEY(message_id) REFERENCES messages(id)
            );

            CREATE TABLE IF NOT EXISTS crisis_checkins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                session_id INTEGER,
                safe_status TEXT NOT NULL,
                contact_person TEXT,
                current_location TEXT,
                notes TEXT,
                risk_level TEXT,
                risk_score INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(user_id),
                FOREIGN KEY(session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS voice_transcripts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                session_id INTEGER,
                transcript TEXT NOT NULL,
                reply TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(user_id),
                FOREIGN KEY(session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS call_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                call_sid TEXT,
                user_id TEXT DEFAULT 'phone_user',
                transcript TEXT,
                summary TEXT,
                risk_level TEXT,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                rating INTEGER,
                comment TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS user_memory (
                user_id TEXT PRIMARY KEY,
                preferred_language TEXT DEFAULT 'hinglish',
                common_emotions TEXT DEFAULT '{}',
                common_intents TEXT DEFAULT '{}',
                common_triggers TEXT DEFAULT '[]',
                helpful_tools TEXT DEFAULT '[]',
                last_emotion TEXT DEFAULT 'neutral',
                last_intent TEXT DEFAULT 'mental_health_support',
                last_mood_score INTEGER DEFAULT 5,
                risk_pattern TEXT DEFAULT 'low',
                summary TEXT DEFAULT '',
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS conversation_insights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                session_id INTEGER,
                message_id INTEGER,
                language TEXT,
                triggers TEXT,
                recommended_tool TEXT,
                response_style TEXT,
                confidence REAL,
                risk_score INTEGER,
                knowledge_used TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(user_id),
                FOREIGN KEY(session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE,
                FOREIGN KEY(message_id) REFERENCES messages(id)
            );

            CREATE TABLE IF NOT EXISTS trusted_contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                relation TEXT,
                notes TEXT,
                is_primary INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS video_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                room_id TEXT NOT NULL,
                room_url TEXT NOT NULL,
                language TEXT DEFAULT 'hinglish',
                status TEXT DEFAULT 'created',
                started_at TEXT NOT NULL,
                ended_at TEXT,
                summary TEXT,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            );
            """
        )

        # Phase 2 migrations for existing Phase 1 databases.
        _ensure_columns(conn, "users", {
            "main_stress_area": "TEXT",
            "coping_preference": "TEXT",
            "voice_preference": "TEXT",
            "memory_enabled": "INTEGER DEFAULT 1",
            "preferred_speech_language": "TEXT DEFAULT 'hi-IN'",
            "preferred_tts_language": "TEXT DEFAULT 'hi-IN'",
        })
        _ensure_columns(conn, "messages", {
            "language": "TEXT",
            "triggers": "TEXT",
            "knowledge_used": "TEXT",
            "risk_score": "INTEGER DEFAULT 0",
            "response_style": "TEXT",
        })
        _ensure_columns(conn, "mood_logs", {
            "intent": "TEXT",
            "trigger_text": "TEXT",
        })
        _ensure_columns(conn, "risk_events", {
            "risk_score": "INTEGER DEFAULT 0",
            "categories": "TEXT",
            "recommended_action": "TEXT",
            "urgency": "TEXT DEFAULT 'normal'",
            "follow_up_required": "INTEGER DEFAULT 0",
            "acknowledged": "INTEGER DEFAULT 0",
            "acknowledged_at": "TEXT",
        })
        _ensure_columns(conn, "safety_plans", {
            "environment_safety": "TEXT",
            "reasons_to_live": "TEXT",
            "professional_support": "TEXT",
            "crisis_steps": "TEXT",
            "completion_score": "INTEGER DEFAULT 0",
            "last_reviewed_at": "TEXT",
        })
        _ensure_columns(conn, "chat_sessions", {
            "dominant_emotion": "TEXT",
            "dominant_intent": "TEXT",
            "max_risk_level": "TEXT DEFAULT 'low'",
        })
        _ensure_columns(conn, "call_sessions", {
            "user_phone": "TEXT",
            "language": "TEXT DEFAULT 'hinglish'",
            "status": "TEXT DEFAULT 'completed'",
            "duration_seconds": "INTEGER DEFAULT 0",
        })
        conn.commit()


@contextmanager
def get_conn():
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        yield conn
        conn.commit()
    finally:
        conn.close()


def fetch_all(query: str, params: Iterable[Any] = ()) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(query, tuple(params)).fetchall()
    return [dict(row) for row in rows]


def fetch_one(query: str, params: Iterable[Any] = ()) -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute(query, tuple(params)).fetchone()
    return dict(row) if row else None


def execute(query: str, params: Iterable[Any] = ()) -> int:
    with get_conn() as conn:
        cur = conn.execute(query, tuple(params))
        return int(cur.lastrowid or 0)


def ensure_user(user_id: str, display_name: str | None = None, preferred_language: str = "hinglish") -> None:
    now = utc_now()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO users(user_id, display_name, preferred_language, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                display_name = COALESCE(excluded.display_name, users.display_name),
                preferred_language = COALESCE(excluded.preferred_language, users.preferred_language),
                updated_at = excluded.updated_at
            """,
            (user_id, display_name, preferred_language, now, now),
        )


def create_session(user_id: str, title: str = "New Support Session") -> int:
    ensure_user(user_id)
    now = utc_now()
    return execute(
        "INSERT INTO chat_sessions(user_id, title, started_at, updated_at) VALUES (?, ?, ?, ?)",
        (user_id, title.strip()[:80] or "New Support Session", now, now),
    )


def get_or_create_session(user_id: str, session_id: int | None = None, title: str = "New Support Session") -> int:
    ensure_user(user_id)
    if session_id:
        row = fetch_one("SELECT id FROM chat_sessions WHERE id=? AND user_id=?", (session_id, user_id))
        if row:
            return int(row["id"])
    return create_session(user_id, title)


def _smart_title_from_message(message: str) -> str:
    clean = re.sub(r"\s+", " ", (message or "").strip())
    clean = re.sub(r"[^\w\s\-.,?!'’:/()\u0900-\u097F]", "", clean)
    if not clean:
        return "New Support Session"
    words = clean.split()
    title = " ".join(words[:7])
    if len(words) > 7:
        title += "..."
    return title[:70]


def update_session_title_from_message(user_id: str, session_id: int, message: str) -> None:
    row = fetch_one(
        """
        SELECT s.title,
               (SELECT COUNT(*) FROM messages m WHERE m.session_id=s.id AND m.user_id=s.user_id AND m.role='user') AS user_message_count
        FROM chat_sessions s
        WHERE s.id=? AND s.user_id=?
        """,
        (session_id, user_id),
    )
    if not row:
        return
    default_titles = {"New Support Session", "CalmMind Session", "Untitled Session"}
    if int(row.get("user_message_count") or 0) <= 1 and (row.get("title") in default_titles):
        execute("UPDATE chat_sessions SET title=?, updated_at=? WHERE id=? AND user_id=?", (_smart_title_from_message(message), utc_now(), session_id, user_id))


def update_session_brain_summary(user_id: str, session_id: int, *, emotion: str, intent: str, risk_level: str) -> None:
    execute(
        """
        UPDATE chat_sessions
        SET dominant_emotion=COALESCE(?, dominant_emotion), dominant_intent=COALESCE(?, dominant_intent),
            max_risk_level=CASE
                WHEN max_risk_level='emergency' OR ?='emergency' THEN 'emergency'
                WHEN max_risk_level='high' OR ?='high' THEN 'high'
                WHEN max_risk_level='medium' OR ?='medium' THEN 'medium'
                ELSE 'low'
            END,
            updated_at=?
        WHERE id=? AND user_id=?
        """,
        (emotion, intent, risk_level, risk_level, risk_level, utc_now(), session_id, user_id),
    )


def rename_session(user_id: str, session_id: int, title: str) -> bool:
    title = (title or "").strip()[:80]
    if not title:
        return False
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE chat_sessions SET title=?, updated_at=? WHERE id=? AND user_id=?",
            (title, utc_now(), session_id, user_id),
        )
        return cur.rowcount > 0


def delete_session(user_id: str, session_id: int) -> bool:
    with get_conn() as conn:
        exists = conn.execute("SELECT id FROM chat_sessions WHERE id=? AND user_id=?", (session_id, user_id)).fetchone()
        if not exists:
            return False
        conn.execute("DELETE FROM conversation_insights WHERE session_id=? AND user_id=?", (session_id, user_id))
        conn.execute("DELETE FROM voice_transcripts WHERE session_id=? AND user_id=?", (session_id, user_id))
        conn.execute("DELETE FROM risk_events WHERE session_id=? AND user_id=?", (session_id, user_id))
        conn.execute("DELETE FROM messages WHERE session_id=? AND user_id=?", (session_id, user_id))
        conn.execute("DELETE FROM chat_sessions WHERE id=? AND user_id=?", (session_id, user_id))
        return True


def list_sessions(user_id: str, limit: int = 40) -> list[dict[str, Any]]:
    ensure_user(user_id)
    return fetch_all(
        """
        SELECT
            s.id,
            s.title,
            s.summary,
            s.started_at,
            s.updated_at,
            s.dominant_emotion,
            s.dominant_intent,
            s.max_risk_level,
            COUNT(m.id) AS message_count,
            COALESCE(MAX(CASE WHEN m.role='user' THEN m.created_at END), s.started_at) AS last_user_message_at,
            (
                SELECT substr(mm.content, 1, 96)
                FROM messages mm
                WHERE mm.session_id=s.id AND mm.user_id=s.user_id
                ORDER BY mm.id DESC
                LIMIT 1
            ) AS last_preview,
            (
                SELECT mm.emotion
                FROM messages mm
                WHERE mm.session_id=s.id AND mm.user_id=s.user_id AND mm.role='user'
                ORDER BY mm.id DESC
                LIMIT 1
            ) AS last_emotion,
            (
                SELECT mm.risk_level
                FROM messages mm
                WHERE mm.session_id=s.id AND mm.user_id=s.user_id AND mm.role='user'
                ORDER BY mm.id DESC
                LIMIT 1
            ) AS last_risk_level
        FROM chat_sessions s
        LEFT JOIN messages m ON m.session_id=s.id AND m.user_id=s.user_id
        WHERE s.user_id=?
        GROUP BY s.id
        ORDER BY s.updated_at DESC
        LIMIT ?
        """,
        (user_id, limit),
    )


def get_session_with_messages(user_id: str, session_id: int) -> dict[str, Any] | None:
    session = fetch_one(
        "SELECT id, title, summary, dominant_emotion, dominant_intent, max_risk_level, started_at, updated_at FROM chat_sessions WHERE user_id=? AND id=?",
        (user_id, session_id),
    )
    if not session:
        return None
    messages = fetch_all(
        """
        SELECT id, role, content, emotion, intent, risk_level, risk_score, mood_score, input_type,
               language, triggers, knowledge_used, response_style, created_at
        FROM messages
        WHERE user_id=? AND session_id=?
        ORDER BY id ASC
        """,
        (user_id, session_id),
    )
    return {"session": session, "messages": messages}


def save_message(
    *,
    user_id: str,
    session_id: int,
    role: str,
    content: str,
    emotion: str | None = None,
    intent: str | None = None,
    risk_level: str | None = None,
    mood_score: int | None = None,
    input_type: str = "text",
    language: str | None = None,
    triggers: str | None = None,
    knowledge_used: str | None = None,
    risk_score: int | None = None,
    response_style: str | None = None,
) -> int:
    now = utc_now()
    message_id = execute(
        """
        INSERT INTO messages(
            session_id, user_id, role, content, emotion, intent, risk_level, mood_score, input_type,
            language, triggers, knowledge_used, risk_score, response_style, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (session_id, user_id, role, content, emotion, intent, risk_level, mood_score, input_type, language, triggers, knowledge_used, risk_score or 0, response_style, now),
    )
    execute("UPDATE chat_sessions SET updated_at=? WHERE id=? AND user_id=?", (now, session_id, user_id))
    if role == "user" and mood_score is not None:
        execute(
            """
            INSERT INTO mood_logs(user_id, score, emotion, intent, source, note, trigger_text, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, mood_score, emotion, intent, input_type, content[:250], triggers, now),
        )
    return message_id



def log_risk_event(
    *,
    user_id: str,
    session_id: int | None,
    message_id: int | None,
    risk_level: str,
    risk_score: int,
    categories: str,
    recommended_action: str,
    content: str,
    safety_response: str,
    urgency: str = "normal",
    follow_up_required: bool = False,
) -> int:
    """Centralized Phase 3 risk-event logger used by chat, voice, and crisis-check APIs."""
    return execute(
        """
        INSERT INTO risk_events(
            user_id, session_id, message_id, risk_level, risk_score, categories,
            recommended_action, urgency, follow_up_required, content, safety_response, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            session_id,
            message_id,
            risk_level,
            risk_score,
            categories,
            recommended_action,
            urgency,
            1 if follow_up_required else 0,
            content,
            safety_response,
            utc_now(),
        ),
    )


def save_crisis_checkin(
    *,
    user_id: str,
    session_id: int | None = None,
    safe_status: str,
    contact_person: str = "",
    current_location: str = "",
    notes: str = "",
    risk_level: str = "low",
    risk_score: int = 0,
) -> int:
    ensure_user(user_id)
    return execute(
        """
        INSERT INTO crisis_checkins(
            user_id, session_id, safe_status, contact_person, current_location,
            notes, risk_level, risk_score, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (user_id, session_id, safe_status, contact_person, current_location, notes, risk_level, risk_score, utc_now()),
    )


def acknowledge_risk_event(event_id: int) -> bool:
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE risk_events SET acknowledged=1, acknowledged_at=? WHERE id=?",
            (utc_now(), event_id),
        )
        return cur.rowcount > 0

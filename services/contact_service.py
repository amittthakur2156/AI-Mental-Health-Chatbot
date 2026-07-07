from __future__ import annotations

import re
from typing import Any

from services.db_service import ensure_user, execute, fetch_all, fetch_one, utc_now


def clean_phone(phone: str | None) -> str:
    value = re.sub(r"[^0-9+]+", "", phone or "")
    if value.startswith("00"):
        value = "+" + value[2:]
    return value[:20]


def default_support_contacts() -> list[dict[str, str]]:
    return [
        {"name": "Emergency Services India", "phone": "112", "relation": "emergency", "notes": "Immediate danger, ambulance, police or fire."},
        {"name": "Tele-MANAS", "phone": "14416", "relation": "mental_health_helpline", "notes": "Mental-health support helpline."},
    ]


def list_contacts(user_id: str) -> list[dict[str, Any]]:
    ensure_user(user_id)
    rows = fetch_all("SELECT * FROM trusted_contacts WHERE user_id=? ORDER BY is_primary DESC, updated_at DESC", (user_id,))
    return rows


def add_contact(user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    ensure_user(user_id)
    name = (payload.get("name") or "Trusted Contact").strip()[:80]
    phone = clean_phone(payload.get("phone"))
    relation = (payload.get("relation") or "trusted_person").strip()[:80]
    notes = (payload.get("notes") or "").strip()[:240]
    is_primary = 1 if payload.get("is_primary") else 0
    if not phone:
        raise ValueError("Phone number is required.")
    now = utc_now()
    if is_primary:
        execute("UPDATE trusted_contacts SET is_primary=0 WHERE user_id=?", (user_id,))
    cid = execute(
        """
        INSERT INTO trusted_contacts(user_id, name, phone, relation, notes, is_primary, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (user_id, name, phone, relation, notes, is_primary, now, now),
    )
    return fetch_one("SELECT * FROM trusted_contacts WHERE id=? AND user_id=?", (cid, user_id)) or {}


def delete_contact(user_id: str, contact_id: int) -> bool:
    row = fetch_one("SELECT id FROM trusted_contacts WHERE id=? AND user_id=?", (contact_id, user_id))
    if not row:
        return False
    execute("DELETE FROM trusted_contacts WHERE id=? AND user_id=?", (contact_id, user_id))
    return True


def create_video_room(user_id: str, language: str = "hinglish") -> dict[str, Any]:
    ensure_user(user_id)
    safe_user = re.sub(r"[^a-zA-Z0-9]", "", user_id)[-10:] or "guest"
    stamp = re.sub(r"[^0-9]", "", utc_now())[-10:]
    room_id = f"calmmind-{safe_user}-{stamp}"
    room_url = f"https://meet.jit.si/{room_id}"
    vid = execute(
        """
        INSERT INTO video_sessions(user_id, room_id, room_url, language, status, started_at)
        VALUES (?, ?, ?, ?, 'created', ?)
        """,
        (user_id, room_id, room_url, language, utc_now()),
    )
    return fetch_one("SELECT * FROM video_sessions WHERE id=? AND user_id=?", (vid, user_id)) or {"room_id": room_id, "room_url": room_url}


def list_video_sessions(user_id: str) -> list[dict[str, Any]]:
    ensure_user(user_id)
    return fetch_all("SELECT * FROM video_sessions WHERE user_id=? ORDER BY id DESC LIMIT 20", (user_id,))

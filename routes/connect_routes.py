from __future__ import annotations

from flask import Blueprint, jsonify, request

from services.auth_service import get_user_id_from_request
from services.contact_service import add_contact, create_video_room, default_support_contacts, delete_contact, list_contacts, list_video_sessions
from services.language_service import normalize_language

connect_bp = Blueprint("connect", __name__, url_prefix="/api/connect")


@connect_bp.get("/contacts")
def contacts():
    user_id = get_user_id_from_request(request)
    return jsonify({"contacts": list_contacts(user_id), "defaults": default_support_contacts()})


@connect_bp.post("/contacts")
def create_contact():
    user_id = get_user_id_from_request(request)
    payload = request.get_json(silent=True) or {}
    try:
        contact = add_contact(user_id, payload)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"ok": True, "contact": contact, "contacts": list_contacts(user_id)})


@connect_bp.delete("/contacts/<int:contact_id>")
def remove_contact(contact_id: int):
    user_id = get_user_id_from_request(request)
    if not delete_contact(user_id, contact_id):
        return jsonify({"error": "Contact not found."}), 404
    return jsonify({"ok": True, "contacts": list_contacts(user_id)})


@connect_bp.post("/video-room")
def video_room():
    user_id = get_user_id_from_request(request)
    payload = request.get_json(silent=True) or {}
    language = normalize_language(payload.get("language"), fallback="hinglish")
    room = create_video_room(user_id, language=language)
    return jsonify({"ok": True, "room": room, "sessions": list_video_sessions(user_id)})


@connect_bp.get("/video-sessions")
def video_sessions():
    user_id = get_user_id_from_request(request)
    return jsonify({"sessions": list_video_sessions(user_id)})

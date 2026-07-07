from __future__ import annotations

import json

from flask import Blueprint, jsonify, request
from services.auth_service import get_user_id_from_request
from services.db_service import (
    execute,
    fetch_all,
    fetch_one,
    ensure_user,
    log_risk_event,
    save_crisis_checkin,
    utc_now,
)
from services.safety_service import (
    build_safety_card,
    classify_risk,
    crisis_response,
    get_emergency_resources,
    get_safety_plan_template,
    medium_risk_response,
    plan_completion_score,
    validate_safety_plan,
)

safety_bp = Blueprint("safety", __name__, url_prefix="/api")


@safety_bp.post("/crisis-check")
def crisis_check():
    user_id = get_user_id_from_request(request)
    ensure_user(user_id)
    payload = request.get_json(silent=True) or {}
    text = (payload.get("text") or "").strip()
    session_id = payload.get("session_id")
    should_log = bool(payload.get("log_event"))
    result = classify_risk(text)
    response = None
    if result.risk_level in {"high", "emergency"}:
        response = crisis_response(text, result.risk_level, safety=result)
    elif result.risk_level == "medium":
        response = medium_risk_response(result)

    event_id = None
    if should_log and result.risk_level in {"medium", "high", "emergency"}:
        event_id = log_risk_event(
            user_id=user_id,
            session_id=session_id,
            message_id=None,
            risk_level=result.risk_level,
            risk_score=result.risk_score,
            categories=json.dumps(result.categories, ensure_ascii=False),
            recommended_action=result.recommended_action,
            content=text,
            safety_response=response or "Safety check logged.",
            urgency=result.urgency,
            follow_up_required=result.follow_up_required,
        )

    return jsonify({
        **result.to_dict(),
        "response": response,
        "event_id": event_id,
        "safety_card": build_safety_card(result),
    })


@safety_bp.get("/emergency-resources")
def emergency_resources():
    return jsonify({"resources": get_emergency_resources()})


@safety_bp.get("/safety-plan/template")
def safety_plan_template():
    return jsonify({"template": get_safety_plan_template(), "resources": get_emergency_resources()})


@safety_bp.get("/safety-plan")
def get_safety_plan():
    user_id = get_user_id_from_request(request)
    ensure_user(user_id)
    row = fetch_one("SELECT * FROM safety_plans WHERE user_id=?", (user_id,)) or {}
    return jsonify({
        "plan": row,
        "completion_score": plan_completion_score(row),
        "validation": validate_safety_plan(row),
        "template": get_safety_plan_template(),
        "resources": get_emergency_resources(),
    })


@safety_bp.post("/safety-plan")
def save_safety_plan():
    user_id = get_user_id_from_request(request)
    ensure_user(user_id)
    payload = request.get_json(silent=True) or {}
    allowed = {
        "warning_signs": payload.get("warning_signs", ""),
        "coping_actions": payload.get("coping_actions", ""),
        "trusted_contacts": payload.get("trusted_contacts", ""),
        "safe_places": payload.get("safe_places", ""),
        "environment_safety": payload.get("environment_safety", ""),
        "reasons_to_live": payload.get("reasons_to_live", ""),
        "professional_support": payload.get("professional_support", ""),
        "crisis_steps": payload.get("crisis_steps", ""),
        "emergency_notes": payload.get("emergency_notes", ""),
    }
    completion = plan_completion_score(allowed)
    now = utc_now()
    execute(
        """
        INSERT INTO safety_plans(
            user_id, warning_signs, coping_actions, trusted_contacts, safe_places,
            environment_safety, reasons_to_live, professional_support, crisis_steps,
            emergency_notes, completion_score, last_reviewed_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            warning_signs=excluded.warning_signs,
            coping_actions=excluded.coping_actions,
            trusted_contacts=excluded.trusted_contacts,
            safe_places=excluded.safe_places,
            environment_safety=excluded.environment_safety,
            reasons_to_live=excluded.reasons_to_live,
            professional_support=excluded.professional_support,
            crisis_steps=excluded.crisis_steps,
            emergency_notes=excluded.emergency_notes,
            completion_score=excluded.completion_score,
            last_reviewed_at=excluded.last_reviewed_at,
            updated_at=excluded.updated_at
        """,
        (
            user_id,
            allowed["warning_signs"],
            allowed["coping_actions"],
            allowed["trusted_contacts"],
            allowed["safe_places"],
            allowed["environment_safety"],
            allowed["reasons_to_live"],
            allowed["professional_support"],
            allowed["crisis_steps"],
            allowed["emergency_notes"],
            completion,
            now,
            now,
        ),
    )
    return jsonify({"ok": True, "completion_score": completion, "validation": validate_safety_plan(allowed)})


@safety_bp.post("/crisis-checkin")
def crisis_checkin():
    user_id = get_user_id_from_request(request)
    ensure_user(user_id)
    payload = request.get_json(silent=True) or {}
    safe_status = (payload.get("safe_status") or "not_sure").strip().lower()
    notes = (payload.get("notes") or "").strip()
    contact_person = (payload.get("contact_person") or "").strip()
    current_location = (payload.get("current_location") or "").strip()

    result = classify_risk(" ".join([safe_status, notes]))
    if safe_status in {"no", "not_safe", "unsafe"}:
        result.risk_level = "high"
        result.risk_score = max(result.risk_score, 82)
        result.urgency = "same_moment"
        result.recommended_action = "trusted_contact_or_emergency_support"
        result.follow_up_required = True

    checkin_id = save_crisis_checkin(
        user_id=user_id,
        session_id=payload.get("session_id"),
        safe_status=safe_status,
        contact_person=contact_person,
        current_location=current_location,
        notes=notes,
        risk_level=result.risk_level,
        risk_score=result.risk_score,
    )

    response = crisis_response(notes, result.risk_level, safety=result) if result.risk_level in {"high", "emergency"} else medium_risk_response(result)
    if result.risk_level in {"medium", "high", "emergency"}:
        log_risk_event(
            user_id=user_id,
            session_id=payload.get("session_id"),
            message_id=None,
            risk_level=result.risk_level,
            risk_score=result.risk_score,
            categories=json.dumps(result.categories, ensure_ascii=False),
            recommended_action=result.recommended_action,
            content=f"Safety check-in: {safe_status}. {notes}",
            safety_response=response,
            urgency=result.urgency,
            follow_up_required=result.follow_up_required,
        )

    return jsonify({"ok": True, "checkin_id": checkin_id, "response": response, **result.to_dict()})


@safety_bp.get("/crisis-checkins")
def crisis_checkins():
    user_id = get_user_id_from_request(request)
    rows = fetch_all(
        """
        SELECT id, safe_status, contact_person, current_location, notes, risk_level, risk_score, created_at
        FROM crisis_checkins WHERE user_id=? ORDER BY id DESC LIMIT 20
        """,
        (user_id,),
    )
    return jsonify({"checkins": rows})

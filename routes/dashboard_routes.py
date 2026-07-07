from __future__ import annotations

import json
from flask import Blueprint, Response, jsonify, request

from services.auth_service import get_user_id_from_request
from services.analytics_service import (
    export_csv,
    export_rows,
    get_activity,
    get_emotion_distribution,
    get_heatmap,
    get_risk_trends,
    get_summary,
    get_trends,
    get_weekly_report,
)


dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api/mood")


def _days() -> int:
    try:
        return max(7, min(int(request.args.get("days", 30)), 365))
    except (TypeError, ValueError):
        return 30


@dashboard_bp.get("/summary")
def mood_summary():
    user_id = get_user_id_from_request(request)
    return jsonify(get_summary(user_id, _days()))


@dashboard_bp.get("/trends")
def mood_trends():
    user_id = get_user_id_from_request(request)
    return jsonify({"trends": get_trends(user_id, _days())})


@dashboard_bp.get("/emotions")
def mood_emotions():
    user_id = get_user_id_from_request(request)
    return jsonify({"emotions": get_emotion_distribution(user_id, _days())})


@dashboard_bp.get("/activity")
def mood_activity():
    user_id = get_user_id_from_request(request)
    return jsonify({"activity": get_activity(user_id, _days())})


@dashboard_bp.get("/risk-trends")
def mood_risk_trends():
    user_id = get_user_id_from_request(request)
    return jsonify({"risk_trends": get_risk_trends(user_id, _days())})


@dashboard_bp.get("/heatmap")
def mood_heatmap():
    user_id = get_user_id_from_request(request)
    return jsonify({"heatmap": get_heatmap(user_id, max(_days(), 90))})


@dashboard_bp.get("/weekly-report")
def mood_weekly_report():
    user_id = get_user_id_from_request(request)
    return jsonify({"report": get_weekly_report(user_id, min(_days(), 30))})


@dashboard_bp.get("/export/json")
def mood_export_json():
    user_id = get_user_id_from_request(request)
    payload = {
        "summary": get_summary(user_id, 30),
        "weekly_report": get_weekly_report(user_id, 7),
        "records": export_rows(user_id),
    }
    return Response(
        json.dumps(payload, indent=2, ensure_ascii=False),
        mimetype="application/json",
        headers={"Content-Disposition": "attachment; filename=calmmind_mood_analytics.json"},
    )


@dashboard_bp.get("/export/csv")
def mood_export_csv():
    user_id = get_user_id_from_request(request)
    return Response(
        export_csv(user_id),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=calmmind_mood_analytics.csv"},
    )

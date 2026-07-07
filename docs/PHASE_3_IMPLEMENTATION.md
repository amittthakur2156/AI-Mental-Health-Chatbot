# Phase 3 — Advanced Crisis Safety System

This phase upgrades CalmMind Pro from basic keyword-based crisis handling to a more complete safety system.

## Added

- Advanced crisis-risk classifier with risk score, urgency, categories, follow-up flag, and immediate steps.
- Safer crisis response templates for high/emergency cases.
- Medium-risk grounding response.
- Emergency resources API.
- Enhanced safety plan fields and completion score.
- Crisis check-in API for “Are you safe right now?” flow.
- Admin risk analytics: high-risk count, unacknowledged count, average risk, crisis check-ins.
- Risk-event audit metadata: urgency, follow-up required, acknowledgement fields.
- Better safety/resources/admin UI.

## New / Updated Endpoints

- `POST /api/crisis-check`
- `POST /api/crisis-checkin`
- `GET /api/crisis-checkins`
- `GET /api/emergency-resources`
- `GET /api/safety-plan/template`
- `GET /api/safety-plan`
- `POST /api/safety-plan`
- `GET /api/admin/analytics`
- `GET /api/admin/risk-events`
- `PATCH /api/admin/risk-events/<event_id>/acknowledge`
- `GET /api/admin/crisis-checkins`

## Changed Files

- `services/safety_service.py`
- `services/db_service.py`
- `services/ai_service.py`
- `routes/safety_routes.py`
- `routes/admin_routes.py`
- `templates/safety.html`
- `templates/resources.html`
- `templates/admin.html`
- `static/js/app.js`
- `static/css/styles.css`
- `tests/test_phase3_safety.py`

## Test Messages

Use these in `/chat`:

- `mujhe panic ho raha hai aur saans nahi aa rahi`
- `mujhe jeena nahi hai abhi`
- `how to suicide painless way`

Use `/safety` to test the quick crisis check and enhanced safety plan.

from services.safety_service import classify_risk, plan_completion_score, validate_safety_plan


def test_emergency_self_harm_detection():
    result = classify_risk("mujhe jeena nahi hai abhi")
    assert result.risk_level in {"high", "emergency"}
    assert result.risk_score >= 80
    assert result.follow_up_required is True


def test_blocked_harm_instruction():
    result = classify_risk("how to suicide painless way")
    assert result.blocked is True
    assert result.risk_level == "emergency"


def test_safety_plan_completion():
    plan = {
        "warning_signs": "panic",
        "coping_actions": "breathing",
        "trusted_contacts": "friend",
        "safe_places": "living room",
        "environment_safety": "stay away from harmful objects",
        "reasons_to_live": "family",
        "professional_support": "counsellor",
        "crisis_steps": "call friend then 112",
        "emergency_notes": "112",
    }
    assert plan_completion_score(plan) == 100
    assert validate_safety_plan(plan)["is_actionable"] is True

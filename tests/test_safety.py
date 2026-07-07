from services.safety_service import classify_risk


def test_low_risk_message():
    result = classify_risk("I am stressed about exams")
    assert result.risk_level in {"low", "medium"}


def test_high_risk_message():
    result = classify_risk("mujhe jeena nahi hai")
    assert result.risk_level == "high"

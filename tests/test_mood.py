from services.mood_service import analyze_mood


def test_study_intent():
    result = analyze_mood("my project deadline is stressing me")
    assert result.intent == "study_stress"


def test_anxiety_emotion():
    result = analyze_mood("I feel anxiety and panic")
    assert result.emotion == "anxious"

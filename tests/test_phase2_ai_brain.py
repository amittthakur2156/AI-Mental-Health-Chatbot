from services.mood_service import analyze_mood
from services.safety_service import classify_risk
from services.rag_service import knowledge_metadata


def test_phase2_detects_language_and_trigger():
    result = analyze_mood("mujhe final year project deadline ka bahut stress hai")
    assert result.language == "hinglish"
    assert result.intent == "study_stress"
    assert "project_deadline" in result.triggers


def test_phase2_risk_score_high():
    result = classify_risk("mujhe jeena nahi hai")
    assert result.risk_level == "high"
    assert result.risk_score >= 80


def test_phase2_rag_returns_knowledge():
    hits = knowledge_metadata("panic attack me ghabrahat ho rahi hai")
    assert hits

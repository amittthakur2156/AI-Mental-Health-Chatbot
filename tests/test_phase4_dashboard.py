from services.analytics_service import _mood_label, _trend_direction


def test_mood_label():
    assert _mood_label(8.5) == "positive"
    assert _mood_label(6.2) == "stable"
    assert _mood_label(4.5) == "low"
    assert _mood_label(2.0) == "very_low"
    assert _mood_label(0) == "not_enough_data"


def test_trend_direction():
    assert _trend_direction([]) == "not_enough_data"
    assert _trend_direction([{"avg_score": 4}, {"avg_score": 5.2}]) == "improving"
    assert _trend_direction([{"avg_score": 7}, {"avg_score": 5.5}]) == "declining"
    assert _trend_direction([{"avg_score": 6}, {"avg_score": 6.3}]) == "stable"

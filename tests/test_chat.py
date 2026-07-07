from services.db_service import init_db
from services.ai_service import build_ai_reply


def test_chat_reply(tmp_path):
    init_db(f"sqlite:///{tmp_path / 'test.db'}")
    result = build_ai_reply("tester", "I am stressed about study")
    assert "reply" in result
    assert result["session_id"]

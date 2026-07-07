from __future__ import annotations

import json
from typing import Any

from config import config
from services.db_service import (
    ensure_user,
    execute,
    fetch_all,
    log_risk_event,
    get_or_create_session,
    save_message,
    update_session_brain_summary,
    update_session_title_from_message,
    utc_now,
)
from services.memory_service import get_memory_profile, update_memory_from_analysis
from services.mood_service import analyze_mood
from services.rag_service import context_block, knowledge_metadata
from services.language_service import normalize_language
from services.response_controller import build_system_prompt, fallback_reply, postprocess_reply
from services.safety_service import classify_risk, crisis_response, final_safety_filter

try:
    from groq import Groq
except Exception:  # pragma: no cover
    Groq = None


def _client():
    if not config.GROQ_API_KEY or Groq is None:
        return None
    return Groq(api_key=config.GROQ_API_KEY)


def recent_context(user_id: str, session_id: int, limit: int = 10) -> list[dict[str, str]]:
    rows = fetch_all(
        """
        SELECT role, content FROM messages
        WHERE user_id=? AND session_id=?
        ORDER BY id DESC LIMIT ?
        """,
        (user_id, session_id, limit),
    )
    return [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]


def generate_llm_reply(*, message: str, context_messages: list[dict[str, str]], rag_context: str, system_prompt: str) -> str | None:
    client = _client()
    if client is None:
        return None

    messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
    if rag_context:
        messages.append({"role": "system", "content": rag_context})
    messages.extend(context_messages[-10:])
    messages.append({"role": "user", "content": message})

    try:
        completion = client.chat.completions.create(
            model=config.GROQ_CHAT_MODEL,
            messages=messages,
            temperature=0.42,
            max_tokens=750,
        )
        return completion.choices[0].message.content.strip()
    except Exception:
        return None


def save_conversation_insight(*, user_id: str, session_id: int, message_id: int, mood, safety, knowledge_used: list[dict]) -> None:
    execute(
        """
        INSERT INTO conversation_insights(
            user_id, session_id, message_id, language, triggers, recommended_tool, response_style,
            confidence, risk_score, knowledge_used, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            session_id,
            message_id,
            mood.language,
            json.dumps(mood.triggers, ensure_ascii=False),
            mood.recommended_tool,
            mood.response_style,
            mood.confidence,
            safety.risk_score,
            json.dumps(knowledge_used, ensure_ascii=False),
            utc_now(),
        ),
    )


def build_ai_reply(user_id: str, message: str, session_id: int | None = None, input_type: str = "text", preferred_language: str | None = None) -> dict[str, Any]:
    """Phase 2 AI brain pipeline.

    Pipeline:
    clean input -> language/intent/emotion -> risk -> memory -> RAG -> response controller -> save analytics.
    """
    message = (message or "").strip()[: config.MAX_MESSAGE_CHARS]
    ensure_user(user_id)
    session_id = get_or_create_session(user_id, session_id=session_id, title="CalmMind Session")

    mood = analyze_mood(message)
    selected_language = normalize_language(preferred_language, fallback="auto")
    if selected_language != "auto":
        mood.language = selected_language
    safety = classify_risk(message)
    knowledge = knowledge_metadata(message, category=None if mood.intent == "general_question" else mood.intent)
    rag = context_block(message, category=None if mood.intent == "general_question" else mood.intent)
    memory_before = get_memory_profile(user_id)

    knowledge_titles = [item.get("title") for item in knowledge[:3]]
    triggers_json = json.dumps(mood.triggers, ensure_ascii=False)
    knowledge_json = json.dumps(knowledge_titles, ensure_ascii=False)

    user_message_id = save_message(
        user_id=user_id,
        session_id=session_id,
        role="user",
        content=message,
        emotion=mood.emotion,
        intent=mood.intent,
        risk_level=safety.risk_level,
        mood_score=mood.mood_score,
        input_type=input_type,
        language=mood.language,
        triggers=triggers_json,
        knowledge_used=knowledge_json,
        risk_score=safety.risk_score,
        response_style=mood.response_style,
    )

    update_session_title_from_message(user_id, session_id, message)
    update_session_brain_summary(user_id, session_id, emotion=mood.emotion, intent=mood.intent, risk_level=safety.risk_level)
    memory_after = update_memory_from_analysis(user_id, mood, safety)
    save_conversation_insight(user_id=user_id, session_id=session_id, message_id=user_message_id, mood=mood, safety=safety, knowledge_used=knowledge)

    if safety.risk_level in {"high", "emergency"}:
        reply = crisis_response(message, safety.risk_level, safety=safety, language=mood.language)
    else:
        context = recent_context(user_id, session_id)
        system_prompt = build_system_prompt(mood=mood, safety=safety, memory=memory_after, rag_context=rag)
        raw_reply = generate_llm_reply(message=message, context_messages=context, rag_context=rag, system_prompt=system_prompt)
        reply = raw_reply or fallback_reply(message, mood=mood, safety=safety, rag_context=rag, memory=memory_after)
        reply = postprocess_reply(reply, mood=mood, safety=safety, used_knowledge=bool(knowledge))
        reply = final_safety_filter(reply, safety, language=mood.language)

    assistant_message_id = save_message(
        user_id=user_id,
        session_id=session_id,
        role="assistant",
        content=reply,
        emotion=mood.emotion,
        intent=mood.intent,
        risk_level=safety.risk_level,
        mood_score=mood.mood_score,
        input_type=input_type,
        language=mood.language,
        triggers=triggers_json,
        knowledge_used=knowledge_json,
        risk_score=safety.risk_score,
        response_style=mood.response_style,
    )

    if safety.risk_level in {"medium", "high", "emergency"}:
        log_risk_event(
            user_id=user_id,
            session_id=session_id,
            message_id=user_message_id,
            risk_level=safety.risk_level,
            risk_score=safety.risk_score,
            categories=json.dumps(safety.categories, ensure_ascii=False),
            recommended_action=safety.recommended_action,
            content=message,
            safety_response=reply,
            urgency=safety.urgency,
            follow_up_required=safety.follow_up_required,
        )

    if input_type == "voice":
        execute(
            "INSERT INTO voice_transcripts(user_id, session_id, transcript, reply, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, session_id, message, reply, utc_now()),
        )

    return {
        "session_id": session_id,
        "message_id": assistant_message_id,
        "reply": reply,
        "emotion": mood.emotion,
        "intent": mood.intent,
        "risk_level": safety.risk_level,
        "risk_score": safety.risk_score,
        "mood_score": mood.mood_score,
        "input_type": input_type,
        "language": mood.language,
        "triggers": mood.triggers,
        "recommended_tool": mood.recommended_tool,
        "response_style": mood.response_style,
        "knowledge_used": knowledge_titles,
        "memory_summary": memory_after.get("summary") or memory_before.get("summary") or "",
        "safety_card": {
            "urgency": safety.urgency,
            "categories": safety.categories,
            "recommended_action": safety.recommended_action,
            "follow_up_required": safety.follow_up_required,
            "immediate_steps": safety.immediate_steps,
        },
        "analysis": {
            "emotion": mood.emotion,
            "intent": mood.intent,
            "risk_level": safety.risk_level,
            "risk_score": safety.risk_score,
            "mood_score": mood.mood_score,
            "confidence": mood.confidence,
            "language": mood.language,
            "triggers": mood.triggers,
            "sentiment_score": mood.sentiment_score,
            "urgency": mood.urgency,
            "recommended_tool": mood.recommended_tool,
            "response_style": mood.response_style,
            "keywords_matched": mood.keywords_matched,
            "safety_categories": safety.categories,
            "safety_recommended_action": safety.recommended_action,
            "safety_urgency": safety.urgency,
            "safety_immediate_steps": safety.immediate_steps,
            "safety_follow_up_required": safety.follow_up_required,
            "knowledge_used": knowledge_titles,
            "memory_summary": memory_after.get("summary") or "",
        },
    }


def analyze_message_only(message: str, preferred_language: str | None = None) -> dict[str, Any]:
    mood = analyze_mood(message)
    selected_language = normalize_language(preferred_language, fallback="auto")
    if selected_language != "auto":
        mood.language = selected_language
    safety = classify_risk(message)
    knowledge = knowledge_metadata(message, category=None if mood.intent == "general_question" else mood.intent)
    return {
        "emotion": mood.emotion,
        "intent": mood.intent,
        "mood_score": mood.mood_score,
        "confidence": mood.confidence,
        "language": mood.language,
        "triggers": mood.triggers,
        "sentiment_score": mood.sentiment_score,
        "recommended_tool": mood.recommended_tool,
        "response_style": mood.response_style,
        "risk_level": safety.risk_level,
        "risk_score": safety.risk_score,
        "safety_categories": safety.categories,
        "safety_urgency": safety.urgency,
        "safety_recommended_action": safety.recommended_action,
        "safety_immediate_steps": safety.immediate_steps,
        "knowledge_matches": [k.get("title") for k in knowledge[:3]],
    }


def summarize_journal(content: str, gratitude: str | None = None) -> str:
    mood = analyze_mood(content + " " + (gratitude or ""))
    if mood.emotion == "positive":
        return "Aaj ke journal me positive energy dikh rahi hai. Is routine ko continue rakhna helpful ho sakta hai."
    if mood.emotion in {"anxious", "panic"}:
        return "Journal me anxiety/stress ka signal hai. Aaj ek chhota priority list aur breathing exercise helpful ho sakti hai."
    if mood.emotion in {"sad", "lonely"}:
        return "Journal me sadness/loneliness ka signal hai. Aaj kisi trusted person se short connection banana helpful ho sakta hai."
    if mood.intent == "study_stress":
        return "Journal me study/project pressure dikh raha hai. Ek 25-minute focus block aur ek realistic micro-task helpful rahega."
    return "Journal balanced hai. Aaj ke liye ek small goal aur gratitude point maintain karna helpful hoga."

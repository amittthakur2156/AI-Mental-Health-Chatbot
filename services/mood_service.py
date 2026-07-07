from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable


@dataclass
class MoodResult:
    emotion: str
    intent: str
    mood_score: int
    confidence: float
    language: str = "hinglish"
    triggers: list[str] = field(default_factory=list)
    sentiment_score: int = 0
    urgency: str = "normal"
    recommended_tool: str = "supportive_chat"
    response_style: str = "professional_support"
    keywords_matched: list[str] = field(default_factory=list)


# Phase 2: richer multilingual keyword maps. Keep them transparent so the
# project remains explainable in viva/demo even without paid classifier APIs.
EMOTION_KEYWORDS: dict[str, list[str]] = {
    "panic": [
        "panic", "panic attack", "can't breathe", "cant breathe", "saans nahi", "ghabrahat",
        "ghabra raha", "ghabra rahi", "heart race", "dil tez", "control nahi",
    ],
    "anxious": [
        "anxiety", "anxious", "stress", "stressed", "tension", "pressure", "worry", "worried",
        "dar", "fear", "nervous", "overthinking", "overthink", "bechain", "restless",
    ],
    "sad": [
        "sad", "depressed", "low", "dukhi", "rona", "cry", "crying", "empty", "hopeless",
        "worthless", "broken", "hurt", "mood off", "down", "heavy", "udaas",
    ],
    "lonely": ["lonely", "alone", "akela", "akeli", "koi nahi", "isolated", "ignored", "left out"],
    "angry": ["angry", "gussa", "irritated", "frustrated", "hate", "annoyed", "rage", "chidh"],
    "tired": ["tired", "thak", "thaka", "exhausted", "burnout", "burned out", "drained", "fatigue"],
    "positive": ["happy", "good", "better", "great", "excited", "calm", "relaxed", "thank", "thanks", "grateful"],
}

INTENT_KEYWORDS: dict[str, list[str]] = {
    "study_stress": [
        "exam", "assignment", "project", "study", "college", "school", "marks", "deadline",
        "padhai", "semester", "syllabus", "presentation", "viva", "final year",
    ],
    "relationship_issue": [
        "relationship", "breakup", "friend", "family", "parents", "partner", "girlfriend", "boyfriend",
        "gf", "bf", "fight", "trust", "ignored", "toxic", "love", "dost",
    ],
    "sleep_problem": ["sleep", "neend", "insomnia", "night", "so nahi", "sone", "nightmare", "late night"],
    "panic_anxiety": ["panic", "anxiety", "ghabra", "can't breathe", "cant breathe", "saans", "dil tez"],
    "motivation": ["motivation", "lazy", "procrastinate", "discipline", "focus", "productive", "routine", "goal"],
    "career_confusion": ["career", "job", "placement", "interview", "resume", "future", "confused", "internship"],
    "wellness_tool": ["breathing", "grounding", "meditation", "exercise", "calm me", "relax", "affirmation"],
    "journal_reflection": ["journal", "diary", "reflection", "gratitude", "write about"],
    "general_question": [
        "what", "why", "how", "kaise", "kya", "explain", "code", "python", "java", "html", "css",
        "flask", "meaning", "define", "calculate", "batao", "samjhao",
    ],
}

TRIGGER_KEYWORDS: dict[str, list[str]] = {
    "exam_pressure": ["exam", "marks", "syllabus", "padhai", "test", "semester"],
    "project_deadline": ["project", "deadline", "submission", "presentation", "viva", "final year"],
    "relationship_conflict": ["breakup", "relationship", "fight", "trust", "ignored", "partner", "gf", "bf"],
    "family_pressure": ["family", "parents", "ghar", "expectations", "pressure from home"],
    "sleep_issue": ["sleep", "neend", "insomnia", "late night"],
    "career_uncertainty": ["career", "job", "future", "placement", "interview"],
    "loneliness": ["lonely", "alone", "akela", "akeli", "koi nahi"],
}

NEGATIVE_INTENSIFIERS = ["bahut", "bohot", "very", "extremely", "too much", "zyada", "intense", "unbearable", "can't handle", "cant handle"]
POSITIVE_WORDS = ["good", "better", "happy", "calm", "relaxed", "grateful", "hope", "manageable", "theek"]
NEGATIVE_WORDS = ["bad", "sad", "stress", "anxiety", "panic", "low", "hopeless", "angry", "tired", "problem", "dar"]


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def _contains_term(text: str, term: str) -> bool:
    term = term.lower().strip()
    if " " in term:
        return term in text
    return bool(re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", text))


def _score_terms(text: str, terms: Iterable[str]) -> tuple[int, list[str]]:
    hits = [term for term in terms if _contains_term(text, term)]
    return len(hits), hits


def detect_language(text: str) -> str:
    clean = text or ""
    has_devanagari = bool(re.search(r"[\u0900-\u097F]", clean))
    hinglish_terms = ["mujhe", "mai", "main", "mera", "meri", "nahi", "kaise", "kya", "hai", "hoon", "kar", "bata"]
    english_words = len(re.findall(r"[a-zA-Z]{3,}", clean))
    if has_devanagari and english_words < 3:
        return "hindi"
    if any(_contains_term(normalize(clean), t) for t in hinglish_terms):
        return "hinglish"
    return "english"


def detect_triggers(clean: str) -> list[str]:
    triggers = []
    for trigger, terms in TRIGGER_KEYWORDS.items():
        score, _ = _score_terms(clean, terms)
        if score:
            triggers.append(trigger)
    return triggers[:4]


def classify_emotion(clean: str) -> tuple[str, float, list[str]]:
    best = ("neutral", 0, [])
    for emotion, terms in EMOTION_KEYWORDS.items():
        score, hits = _score_terms(clean, terms)
        if score > best[1]:
            best = (emotion, score, hits)

    emotion, score, hits = best
    if score == 0:
        return "neutral", 0.36, []
    # A panic phrase should dominate anxiety if it appears.
    confidence = min(0.92, 0.58 + score * 0.12)
    return emotion, confidence, hits


def classify_intent(clean: str, emotion: str) -> tuple[str, list[str]]:
    best_intent = "mental_health_support"
    best_score = 0
    best_hits: list[str] = []
    for intent, terms in INTENT_KEYWORDS.items():
        score, hits = _score_terms(clean, terms)
        if score > best_score:
            best_intent, best_score, best_hits = intent, score, hits

    # Emotion-based tie breakers.
    if best_score == 0:
        if emotion in {"panic", "anxious"}:
            return "panic_anxiety", []
        if emotion == "tired":
            return "sleep_problem", []
        return "mental_health_support", []
    return best_intent, best_hits


def calculate_mood_score(clean: str, emotion: str, triggers: list[str]) -> int:
    base_by_emotion = {
        "positive": 8,
        "neutral": 5,
        "tired": 4,
        "anxious": 4,
        "panic": 2,
        "angry": 3,
        "sad": 3,
        "lonely": 3,
    }
    score = base_by_emotion.get(emotion, 5)
    if any(_contains_term(clean, word) for word in NEGATIVE_INTENSIFIERS):
        score -= 1
    if "hopeless" in clean or "worthless" in clean:
        score -= 1
    if len(triggers) >= 2:
        score -= 1
    if any(_contains_term(clean, word) for word in POSITIVE_WORDS):
        score += 1
    return max(1, min(10, score))


def sentiment_score(clean: str) -> int:
    positive = sum(1 for word in POSITIVE_WORDS if _contains_term(clean, word))
    negative = sum(1 for word in NEGATIVE_WORDS if _contains_term(clean, word))
    return max(-5, min(5, positive - negative))


def recommend_tool(intent: str, emotion: str, triggers: list[str]) -> str:
    if emotion == "panic" or intent == "panic_anxiety":
        return "grounding_54321"
    if intent == "sleep_problem":
        return "sleep_routine"
    if intent == "study_stress" or "project_deadline" in triggers:
        return "study_micro_plan"
    if emotion == "anxious":
        return "box_breathing"
    if emotion in {"sad", "lonely"}:
        return "connection_journal_prompt"
    if intent == "motivation":
        return "tiny_goal_plan"
    return "supportive_chat"


def choose_response_style(intent: str, emotion: str, mood_score: int) -> str:
    if emotion == "panic":
        return "grounding_first"
    if mood_score <= 3:
        return "gentle_support"
    if intent == "general_question":
        return "clear_teacher"
    if intent in {"study_stress", "career_confusion", "motivation"}:
        return "coach_plan"
    return "professional_support"


def analyze_mood(text: str) -> MoodResult:
    clean = normalize(text)
    language = detect_language(text)
    emotion, confidence, emotion_hits = classify_emotion(clean)
    intent, intent_hits = classify_intent(clean, emotion)
    triggers = detect_triggers(clean)
    score = calculate_mood_score(clean, emotion, triggers)
    urgency = "elevated" if emotion in {"panic", "sad"} and score <= 3 else "normal"
    recommended = recommend_tool(intent, emotion, triggers)
    style = choose_response_style(intent, emotion, score)
    return MoodResult(
        emotion=emotion,
        intent=intent,
        mood_score=score,
        confidence=confidence,
        language=language,
        triggers=triggers,
        sentiment_score=sentiment_score(clean),
        urgency=urgency,
        recommended_tool=recommended,
        response_style=style,
        keywords_matched=(emotion_hits + intent_hits)[:8],
    )

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# -----------------------------------------------------------------------------
# Phase 3 Safety Engine
# -----------------------------------------------------------------------------
# This file is intentionally rule-first and deterministic. Mental-health safety
# checks should not depend only on a generative model. The LLM can add empathy,
# but this layer always has final control over crisis replies and blocked content.

HIGH_RISK_TERMS = [
    "suicide", "kill myself", "end my life", "die", "i want to die", "want to die",
    "mar jana", "mar jaunga", "mar jaungi", "marna chahta", "marna chahti",
    "khud ko maar", "khud ko mar", "khud ko nuksan", "self harm", "self-harm",
    "cut myself", "zinda nahi", "jeena nahi", "jeena nhi", "jeena nahi hai",
    "i don't want to live", "i dont want to live", "overdose", "hang myself",
    "finish myself", "life end", "apni life khatam", "sab khatam karna",
]

IMMINENT_TERMS = [
    "right now", "abhi", "aaj", "tonight", "iss waqt", "currently", "now",
    "maine decide kar liya", "plan bana liya", "mere paas", "i have a plan",
]

MEDIUM_RISK_TERMS = [
    "hopeless", "worthless", "panic", "panic attack", "attack", "unsafe", "abuse",
    "violence", "domestic", "can't breathe", "cant breathe", "bahut dar",
    "control nahi", "control nhi", "toot gaya", "akela", "akeli", "no one cares",
    "give up", "can't handle", "cant handle", "trauma", "breakdown", "dar lag raha",
    "saans nahi", "saans nhi", "ghabrahat", "overthinking", "bahut ro raha",
]

ABUSE_TERMS = [
    "abuse", "hit me", "beats me", "domestic violence", "ghar me maar", "ghar mein maar",
    "forced", "threat", "blackmail", "harassment", "stalking", "unsafe at home",
]

PANIC_TERMS = [
    "panic", "panic attack", "saans nahi", "saans nhi", "can't breathe", "cant breathe",
    "heart race", "dil tez", "ghabrahat", "control nahi", "control nhi",
]

HARM_TO_OTHERS_TERMS = [
    "kill someone", "hurt someone", "maar dunga", "maar dungi", "harm someone",
    "attack someone", "badla lena", "violence karna", "weapon leke",
]

BLOCKED_HARM_TERMS = [
    "how to suicide", "best way to die", "how to die", "how to harm myself",
    "poison myself", "suicide method", "self harm method", "painless way to die",
    "which poison", "how much overdose", "hang myself method", "cut vein",
]

PROTECTIVE_TERMS = [
    "safe", "i am safe", "family ke sath", "family ke saath", "with my friend",
    "doctor", "therapist", "help line", "helpline", "counsellor", "counselor",
]

EMERGENCY_RESOURCES = [
    {
        "name": "Emergency Services India",
        "contact": "112",
        "type": "emergency",
        "available": "24/7",
        "description": "Immediate danger, medical emergency, police/fire/ambulance support.",
    },
    {
        "name": "Tele-MANAS",
        "contact": "14416 / 1800-891-4416",
        "type": "mental_health_support",
        "available": "24/7 in many regions",
        "description": "Government mental-health support helpline in India.",
    },
    {
        "name": "Trusted Person",
        "contact": "Saved in your safety plan",
        "type": "personal_support",
        "available": "As available",
        "description": "Friend, family member, mentor, teacher, or someone nearby who can stay with you.",
    },
]

GROUNDING_STEPS = [
    "Put both feet on the floor and relax your shoulders.",
    "Take 3 slow breaths: inhale 4 seconds, exhale 6 seconds.",
    "Name 5 things you can see, 4 things you can feel, and 3 sounds you can hear.",
    "Send one short message to a trusted person: 'I am not feeling safe, can you stay with me?'",
]

SAFETY_PLAN_TEMPLATE = {
    "warning_signs": "Example: racing thoughts, chest tightness, crying, feeling hopeless, urge to isolate.",
    "coping_actions": "Example: box breathing, 5-4-3-2-1 grounding, walk outside, calming playlist, cold water splash.",
    "trusted_contacts": "Example: Name + phone number of friend/family/mentor who can respond quickly.",
    "safe_places": "Example: living room with family, friend's house, college office, public safe place.",
    "environment_safety": "Example: move away from harmful objects/medicines, stay near people, avoid being alone.",
    "reasons_to_live": "Example: family, goals, future plans, pets, friends, faith, dreams, unfinished work.",
    "professional_support": "Example: counsellor/doctor contact, college mentor, Tele-MANAS 14416.",
    "crisis_steps": "1) Move to safe place. 2) Contact trusted person. 3) Call 112 if immediate danger. 4) Use grounding.",
    "emergency_notes": "India emergency: 112. Tele-MANAS: 14416 / 1800-891-4416.",
}


@dataclass
class SafetyResult:
    risk_level: str
    blocked: bool
    reasons: list[str]
    risk_score: int = 0
    categories: list[str] = field(default_factory=list)
    urgency: str = "normal"
    recommended_action: str = "supportive_reply"
    resources: list[dict[str, str]] = field(default_factory=lambda: EMERGENCY_RESOURCES.copy())
    immediate_steps: list[str] = field(default_factory=list)
    grounding_steps: list[str] = field(default_factory=lambda: GROUNDING_STEPS.copy())
    follow_up_required: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "risk_level": self.risk_level,
            "blocked": self.blocked,
            "reasons": self.reasons,
            "risk_score": self.risk_score,
            "categories": self.categories,
            "urgency": self.urgency,
            "recommended_action": self.recommended_action,
            "resources": self.resources,
            "immediate_steps": self.immediate_steps,
            "grounding_steps": self.grounding_steps,
            "follow_up_required": self.follow_up_required,
        }


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def _hit(clean: str, term: str) -> bool:
    term = term.lower().strip()
    if " " in term or "-" in term:
        return term in clean
    return bool(re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", clean))


def _hits(clean: str, terms: list[str]) -> list[str]:
    return [term for term in terms if _hit(clean, term)]


def _unique(items: list[str]) -> list[str]:
    return list(dict.fromkeys([item for item in items if item]))


def classify_risk(text: str) -> SafetyResult:
    clean = normalize(text)
    reasons: list[str] = []
    categories: list[str] = []
    score = 5
    blocked = False

    blocked_hits = _hits(clean, BLOCKED_HARM_TERMS)
    if blocked_hits:
        blocked = True
        reasons += [f"blocked_harm_instruction:{term}" for term in blocked_hits]
        categories.append("harmful_instruction")
        score += 92

    high_hits = _hits(clean, HIGH_RISK_TERMS)
    if high_hits:
        reasons += [f"high_risk_self_harm:{term}" for term in high_hits]
        categories.append("self_harm_or_suicide")
        score += 76

    imminent_hits = _hits(clean, IMMINENT_TERMS)
    if high_hits and imminent_hits:
        reasons += [f"imminent_language:{term}" for term in imminent_hits]
        categories.append("possible_imminent_risk")
        score += 14

    medium_hits = _hits(clean, MEDIUM_RISK_TERMS)
    if medium_hits:
        reasons += [f"medium_distress:{term}" for term in medium_hits]
        categories.append("distress_or_safety_concern")
        score += min(40, 18 + len(medium_hits) * 6)

    panic_hits = _hits(clean, PANIC_TERMS)
    if panic_hits:
        reasons += [f"panic_signal:{term}" for term in panic_hits]
        categories.append("panic_or_breathing_distress")
        score += 20

    abuse_hits = _hits(clean, ABUSE_TERMS)
    if abuse_hits:
        reasons += [f"abuse_or_unsafe_environment:{term}" for term in abuse_hits]
        categories.append("abuse_or_unsafe_environment")
        score += 28

    others_hits = _hits(clean, HARM_TO_OTHERS_TERMS)
    if others_hits:
        reasons += [f"harm_to_others:{term}" for term in others_hits]
        categories.append("harm_to_others")
        score += 65

    protective_hits = _hits(clean, PROTECTIVE_TERMS)
    if protective_hits and not blocked:
        reasons += [f"protective_factor:{term}" for term in protective_hits]
        categories.append("protective_factor_present")
        score = max(5, score - 12)

    score = min(100, max(0, score))
    categories = _unique(categories)

    if blocked:
        return SafetyResult(
            risk_level="emergency",
            blocked=True,
            reasons=reasons,
            risk_score=max(score, 95),
            categories=categories,
            urgency="immediate",
            recommended_action="block_and_crisis_protocol",
            immediate_steps=build_immediate_steps(categories, emergency=True),
            follow_up_required=True,
        )

    if high_hits and imminent_hits:
        return SafetyResult(
            risk_level="emergency",
            blocked=False,
            reasons=reasons,
            risk_score=max(score, 90),
            categories=categories,
            urgency="immediate",
            recommended_action="crisis_protocol_with_emergency_escalation",
            immediate_steps=build_immediate_steps(categories, emergency=True),
            follow_up_required=True,
        )

    if high_hits or others_hits:
        return SafetyResult(
            risk_level="high",
            blocked=False,
            reasons=reasons,
            risk_score=max(score, 80),
            categories=categories,
            urgency="same_moment",
            recommended_action="crisis_protocol",
            immediate_steps=build_immediate_steps(categories, emergency=False),
            follow_up_required=True,
        )

    if score >= 45 or panic_hits or abuse_hits:
        return SafetyResult(
            risk_level="medium",
            blocked=False,
            reasons=reasons,
            risk_score=max(score, 45),
            categories=categories,
            urgency="elevated",
            recommended_action="grounding_and_check_in",
            immediate_steps=build_immediate_steps(categories, emergency=False),
            follow_up_required="abuse_or_unsafe_environment" in categories,
        )

    return SafetyResult(
        risk_level="low",
        blocked=False,
        reasons=reasons,
        risk_score=score,
        categories=categories,
        urgency="normal",
        recommended_action="supportive_reply",
        immediate_steps=[],
        follow_up_required=False,
    )


def build_immediate_steps(categories: list[str], emergency: bool = False) -> list[str]:
    steps: list[str] = []
    if emergency:
        steps.append("If there is immediate danger, call 112 now or ask someone nearby to call for you.")
    steps.append("Move to a place where you are not alone, or call/message a trusted person right now.")
    if "self_harm_or_suicide" in categories or "possible_imminent_risk" in categories:
        steps.append("Put distance between yourself and anything you could use to harm yourself.")
    if "harm_to_others" in categories:
        steps.append("Step away from the other person and any weapons/objects; contact emergency support if someone may be hurt.")
    if "panic_or_breathing_distress" in categories:
        steps.append("Try slow exhale breathing: inhale 4 seconds, exhale 6 seconds, repeat 5 times.")
    if "abuse_or_unsafe_environment" in categories:
        steps.append("Move toward a safer/public place if possible and contact a trusted person or emergency service.")
    steps.append("Answer one safety check: are you safe right now? yes / no / not sure")
    return _unique(steps)


def crisis_response(user_text: str, risk_level: str = "high", safety: SafetyResult | None = None, language: str | None = None) -> str:
    from services.language_service import normalize_language

    safety = safety or classify_risk(user_text)
    lang = normalize_language(language, fallback="hinglish")
    emergency = risk_level == "emergency" or safety.urgency == "immediate"

    if lang in {"english", "french", "chinese"}:
        templates = {
            "english": (
                "I’m really sorry you’re feeling this much pain. Your immediate safety matters most right now.\n\n"
                + ("If you are in immediate danger, call your local emergency number now. In India, call 112.\n" if emergency else "If you feel unsafe, call or message a trusted person right now and do not stay alone.\n")
                + "1) Move near another person or to a safer place.\n"
                + "2) Put distance between you and anything you could use to harm yourself.\n"
                + "3) Contact a trusted person now.\n"
                + "4) For mental-health support in India, Tele-MANAS: 14416 / 1800-891-4416.\n\n"
                + "Please reply with one word: are you safe right now — yes, no, or not sure?"
            ),
            "french": (
                "Je suis vraiment désolé que vous ressentiez autant de douleur. Votre sécurité immédiate est la priorité.\n\n"
                + ("Si vous êtes en danger immédiat, appelez les services d’urgence maintenant. En Inde, appelez le 112.\n" if emergency else "Si vous ne vous sentez pas en sécurité, appelez ou envoyez un message à une personne de confiance maintenant et ne restez pas seul(e).\n")
                + "1) Allez près d’une autre personne ou dans un endroit plus sûr.\n"
                + "2) Éloignez-vous de tout ce qui pourrait vous blesser.\n"
                + "3) Contactez maintenant une personne de confiance.\n"
                + "4) En Inde, Tele-MANAS: 14416 / 1800-891-4416.\n\n"
                + "Répondez simplement: êtes-vous en sécurité maintenant — oui, non, ou pas sûr ?"
            ),
            "chinese": (
                "很抱歉你正在承受这么沉重的痛苦。现在最重要的是你的安全。\n\n"
                + ("如果你正处于立即危险中，请立刻拨打当地紧急电话。在印度请拨打112。\n" if emergency else "如果你感到不安全，请现在联系一个你信任的人，不要独自待着。\n")
                + "1) 去到有人陪伴或更安全的地方。\n"
                + "2) 远离任何可能伤害自己的物品。\n"
                + "3) 现在联系一个信任的人。\n"
                + "4) 在印度，Tele-MANAS: 14416 / 1800-891-4416。\n\n"
                + "请只回复：你现在安全吗——是、不是、还是不确定？"
            ),
        }
        return templates[lang]

    # Indian-language demo fallback in Hinglish/simplified support style.
    emergency_line = (
        "Agar tum abhi immediate danger me ho, India me 112 call karo ya kisi nearby person se abhi help maango.\n"
        if emergency
        else "Agar tum unsafe feel kar rahe ho, please abhi kisi trusted person ko call/message karo aur akela mat raho.\n"
    )
    steps = safety.immediate_steps or build_immediate_steps(safety.categories, emergency=emergency)
    step_text = "\n".join([f"{idx + 1}) {step}" for idx, step in enumerate(steps[:5])])
    return (
        "Mujhe afsos hai ki tum itna heavy feel kar rahe ho. Abhi sabse pehle tumhari safety important hai.\n\n"
        f"{emergency_line}\n"
        f"{step_text}\n\n"
        "Mental-health support ke liye Tele-MANAS 14416 / 1800-891-4416 available ho sakta hai. "
        "Main tumhare saath hoon — bas ek short reply do: kya tum abhi safe jagah par ho?"
    )


def medium_risk_response(safety: SafetyResult | None = None) -> str:
    safety = safety or SafetyResult("medium", False, [], risk_score=45)
    steps = safety.grounding_steps[:3]
    return (
        "Ye moment intense lag sakta hai. Pehle ek quick grounding step karte hain:\n"
        + "\n".join([f"• {step}" for step in steps])
        + "\nAgar tum unsafe feel kar rahe ho, kisi trusted person ko abhi message/call karo."
    )


def safety_disclaimer() -> str:
    return (
        "Note: Main ek AI wellness companion hoon, doctor/therapist/emergency service ka replacement nahi. "
        "Agar situation urgent ho, local emergency service ya qualified professional se contact karo."
    )


def final_safety_filter(reply: str, safety: SafetyResult, language: str | None = None) -> str:
    """Last line defense: never let harmful instruction requests get normal answers."""
    if safety.risk_level in {"high", "emergency"}:
        return crisis_response("", safety.risk_level, safety=safety, language=language)
    if safety.blocked:
        return crisis_response("", "emergency", safety=safety, language=language)
    return reply


def get_emergency_resources() -> list[dict[str, str]]:
    return EMERGENCY_RESOURCES.copy()


def get_safety_plan_template() -> dict[str, str]:
    return SAFETY_PLAN_TEMPLATE.copy()


def plan_completion_score(plan: dict[str, Any] | None) -> int:
    if not plan:
        return 0
    fields = [
        "warning_signs", "coping_actions", "trusted_contacts", "safe_places",
        "environment_safety", "reasons_to_live", "professional_support", "crisis_steps", "emergency_notes",
    ]
    filled = 0
    for field in fields:
        value = str(plan.get(field) or "").strip()
        if len(value) >= 3:
            filled += 1
    return round((filled / len(fields)) * 100)


def validate_safety_plan(plan: dict[str, Any]) -> dict[str, Any]:
    missing = []
    important = ["trusted_contacts", "safe_places", "coping_actions", "emergency_notes"]
    for field in important:
        if not str(plan.get(field) or "").strip():
            missing.append(field)
    score = plan_completion_score(plan)
    return {
        "completion_score": score,
        "missing_important_fields": missing,
        "is_actionable": score >= 55 and not missing,
        "next_step": missing[0] if missing else "review_plan_monthly",
    }


def build_safety_card(result: SafetyResult) -> dict[str, Any]:
    """Compact payload for frontend/admin risk cards."""
    return {
        "risk_level": result.risk_level,
        "risk_score": result.risk_score,
        "urgency": result.urgency,
        "categories": result.categories,
        "action": result.recommended_action,
        "follow_up_required": result.follow_up_required,
        "immediate_steps": result.immediate_steps,
    }

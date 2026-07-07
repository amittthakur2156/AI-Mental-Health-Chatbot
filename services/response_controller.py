from __future__ import annotations

from services.language_service import instruction_for_language, language_option, normalize_language
from services.safety_service import SafetyResult, safety_disclaimer


def user_facing_language_name(language: str) -> str:
    return language_option(language).english_name


def response_style_instruction(style: str) -> str:
    instructions = {
        "grounding_first": "Start with one short grounding step before explanation. Keep it calming and concrete.",
        "gentle_support": "Use a warm validating tone, short paragraphs, and one gentle follow-up question.",
        "clear_teacher": "Answer clearly like a helpful tutor, but remain emotionally aware if the user sounds stressed.",
        "coach_plan": "Give a practical step-by-step mini plan with 2-4 bullets and one next action.",
        "professional_support": "Be empathetic, professional, practical, and concise.",
    }
    return instructions.get(style, instructions["professional_support"])


def build_system_prompt(*, mood, safety: SafetyResult, memory: dict, rag_context: str) -> str:
    memory_summary = memory.get("summary") or "No long-term pattern yet."
    language_instruction = instruction_for_language(mood.language, detected=mood.language)
    return f"""
You are CalmMind AI, a professional mental-wellness support companion.
Positioning: supportive companion only, not a doctor, therapist, diagnosis tool, emergency service, or crisis line.
Language rule: {language_instruction}
Do not switch language unless the selected language is Auto Detect and the user clearly changes language.
Detected user state: emotion={mood.emotion}, intent={mood.intent}, mood_score={mood.mood_score}/10, triggers={', '.join(mood.triggers) or 'none'}, risk={safety.risk_level}.
User memory summary: {memory_summary}
Response style: {response_style_instruction(mood.response_style)}
Safety rules:
- Never diagnose, prescribe, or promise certainty.
- Never provide self-harm, suicide, violence, weapon, poisoning, or evasion instructions.
- If risk is high/emergency, do not answer normally; follow crisis protocol.
- For mental-health topics, validate feeling + suggest one small action + ask one useful follow-up.
- For general questions, answer normally but keep tone supportive.
- For calls/voice, keep replies speakable: short sentences, no markdown tables.
Approved knowledge context may be provided; use it when relevant and don't invent medical claims.
""".strip()


def localized_disclaimer(language: str) -> str:
    lang = normalize_language(language)
    return {
        "english": "Note: I am an AI wellness companion, not a replacement for a doctor, therapist, or emergency service. If this feels urgent, contact local emergency services or a qualified professional.",
        "french": "Note : je suis un compagnon de bien-être IA, pas un remplacement pour un médecin, un thérapeute ou un service d’urgence. En cas d’urgence, contactez les services locaux ou un professionnel qualifié.",
        "chinese": "提示：我是AI心理健康陪伴助手，不能替代医生、治疗师或紧急服务。如果情况紧急，请联系当地紧急服务或合格专业人士。",
        "urdu": "نوٹ: میں ایک AI wellness companion ہوں، ڈاکٹر، therapist یا emergency service کا replacement نہیں۔ اگر صورتحال urgent ہو تو local emergency service یا qualified professional سے رابطہ کریں۔",
    }.get(lang, safety_disclaimer())


def postprocess_reply(reply: str, *, mood, safety: SafetyResult, used_knowledge: bool) -> str:
    clean = (reply or "").strip()
    if not clean:
        return fallback_line(mood.language)

    needs_disclaimer = mood.intent != "general_question" and safety.risk_level in {"low", "medium"}
    if needs_disclaimer and "replacement" not in clean.lower() and "doctor" not in clean.lower() and "therapist" not in clean.lower():
        clean = f"{clean}\n\n{localized_disclaimer(mood.language)}"

    if len(clean) > 2600:
        clean = clean[:2500].rsplit(" ", 1)[0] + "..."
    return clean


def fallback_line(language: str) -> str:
    lang = normalize_language(language)
    return {
        "hindi": "Main yahan hoon. Tum apni baat thoda aur share kar sakte ho?",
        "hinglish": "Main yahan hoon. Tum apni baat thoda aur share kar sakte ho?",
        "english": "I am here with you. Could you share a little more about what is happening?",
        "punjabi": "Main tuhade naal haan. Tusi thoda hor dass sakde ho ki ki ho reha hai?",
        "marathi": "मी इथे आहे. काय होत आहे ते थोडे आणखी सांगू शकता का?",
        "telugu": "నేను మీతోనే ఉన్నాను. ఏమి జరుగుతోందో కొంచెం మరింత చెప్పగలరా?",
        "urdu": "میں آپ کے ساتھ ہوں۔ کیا آپ تھوڑا اور بتا سکتے ہیں کہ کیا ہو رہا ہے؟",
        "french": "Je suis là avec vous. Pouvez-vous m'en dire un peu plus sur ce qui se passe ?",
        "chinese": "我在这里陪着你。你可以再多说一点现在发生了什么吗？",
    }.get(lang, "Main yahan hoon. Tum apni baat thoda aur share kar sakte ho?")


def fallback_reply(message: str, *, mood, safety: SafetyResult, rag_context: str, memory: dict) -> str:
    if safety.risk_level in {"high", "emergency"}:
        from services.safety_service import crisis_response
        return crisis_response(message, safety.risk_level, language=mood.language)

    # Local fallback is multilingual enough for demo; LLM response will be better when key is present.
    lang = normalize_language(mood.language)
    if lang == "english":
        return _english_fallback(message, mood)
    if lang not in {"hindi", "hinglish", "english"}:
        return _simple_multilingual_fallback(message, mood, lang)

    tool_line = {
        "grounding_54321": "Abhi 5-4-3-2-1 grounding try karo: 5 cheezein dekho, 4 touch feel karo, 3 sounds suno, 2 smells notice karo, aur 1 slow breath lo.",
        "box_breathing": "Box breathing try karo: 4 sec inhale, 4 sec hold, 4 sec exhale, 4 sec hold — 4 rounds.",
        "study_micro_plan": "Ek 25-minute focus block set karo: sirf ek small task, phone side, 5-minute break ke baad progress check.",
        "sleep_routine": "Aaj raat screen 30 min pehle low/off, ek brain-dump note, phir 4 slow breaths ke saath bed routine try karo.",
        "connection_journal_prompt": "Ek trusted person ko short message bhejo: ‘Aaj thoda low feel kar raha/rahi hoon, can we talk for 5 minutes?’",
        "tiny_goal_plan": "Aaj sirf ek tiny goal choose karo jo 10 minutes me start ho sake. Momentum perfection se zyada important hai.",
    }.get(mood.recommended_tool, "Ek chhota next step choose karo jo abhi 2 minutes me start ho sake.")

    if mood.intent == "general_question":
        return "Bilkul, main explain kar sakta hoon. Tumhara question ye hai: " + message[:140] + "\n\nIsko simple steps me todkar answer dunga. Thoda aur context doge to main aur accurate reply de paunga."

    trigger_text = f" Main notice kar raha hoon ki trigger {', '.join(mood.triggers)} ho sakta hai." if mood.triggers else ""
    return (
        f"Samajh raha hoon — tum {mood.emotion} feel kar rahe/rahi ho, aur ye valid hai.{trigger_text}\n\n"
        f"Abhi ke liye: {tool_line}\n\n"
        "Mujhe 0 se 10 me batao, intensity abhi kitni hai?"
    )


def _english_fallback(message: str, mood) -> str:
    if mood.intent == "general_question":
        return (
            "Sure — I can help explain that clearly. Here is what I understood: " + message[:140] +
            "\n\nShare a little more context and I will give a more accurate step-by-step answer."
        )
    tool_line = {
        "grounding_54321": "Try 5-4-3-2-1 grounding: notice 5 things you can see, 4 you can feel, 3 sounds, 2 smells, and 1 slow breath.",
        "box_breathing": "Try box breathing: inhale 4 seconds, hold 4, exhale 4, hold 4 — repeat 4 rounds.",
        "study_micro_plan": "Set one 25-minute focus block: choose one tiny task, keep your phone away, then take a 5-minute break.",
        "sleep_routine": "Tonight, reduce screen use 30 minutes before bed, write a quick brain-dump note, then take 4 slow breaths.",
        "connection_journal_prompt": "Message one trusted person: ‘I’m feeling low today. Can we talk for 5 minutes?’",
        "tiny_goal_plan": "Pick one tiny task you can start in 2 minutes. Momentum matters more than perfection.",
    }.get(mood.recommended_tool, "Choose one small next step you can start within 2 minutes.")
    trigger_text = f" I notice the trigger may be {', '.join(mood.triggers)}." if mood.triggers else ""
    return (
        f"I hear you — feeling {mood.emotion} makes sense, and you do not have to handle it all at once.{trigger_text}\n\n"
        f"For now: {tool_line}\n\n"
        "On a scale from 0 to 10, how intense does this feel right now?"
    )


def _simple_multilingual_fallback(message: str, mood, lang: str) -> str:
    lines = {
        "punjabi": f"Main samajh sakda/sakdi haan ki tusi {mood.emotion} feel kar rahe ho. Hun ikk chhota step lo: 4 slow breaths lo, phir mainu 0 to 10 tak intensity dasso.",
        "marathi": f"मला समजते की तुम्हाला {mood.emotion} वाटत आहे. आत्ता एक छोटा उपाय करा: 4 हळू श्वास घ्या, मग 0 ते 10 मध्ये तीव्रता सांगा.",
        "telugu": f"మీరు {mood.emotion}గా అనిపిస్తోందని నేను అర్థం చేసుకుంటున్నాను. ఇప్పుడే చిన్న స్టెప్: 4 నెమ్మదిగా శ్వాసలు తీసుకుని, 0 నుంచి 10 వరకు తీవ్రత చెప్పండి.",
        "urdu": f"میں سمجھ سکتا/سکتی ہوں کہ آپ {mood.emotion} محسوس کر رہے ہیں۔ ابھی ایک چھوٹا قدم لیں: 4 آہستہ سانسیں لیں، پھر شدت 0 سے 10 تک بتائیں۔",
        "french": f"Je comprends que vous vous sentiez {mood.emotion}. Pour l'instant, prenez 4 respirations lentes, puis dites-moi l'intensité de 0 à 10.",
        "chinese": f"我理解你现在感到 {mood.emotion}。先做一个小步骤：慢慢呼吸4次，然后告诉我强度是0到10中的几分。",
    }
    return lines.get(lang, fallback_line(lang))

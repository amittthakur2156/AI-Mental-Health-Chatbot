from __future__ import annotations

import json
from flask import Blueprint, Response, request, jsonify
from twilio.twiml.voice_response import VoiceResponse, Gather, Connect, Stream

from config import config
from services.ai_service import build_ai_reply
from services.db_service import execute, fetch_all, utc_now, ensure_user
from services.language_service import language_option, normalize_language

call_bp = Blueprint("calls", __name__)


def _twiml(response: VoiceResponse) -> Response:
    return Response(str(response), mimetype="text/xml")


def _safe_say(text: str, max_chars: int = 1200) -> str:
    cleaned = " ".join((text or "").replace("\n", " ").split())
    return cleaned[:max_chars] or "Sorry, I could not generate a response."


@call_bp.post("/twilio/voice")
def twilio_voice():
    """Turn-based phone call AI using Twilio <Gather input='speech'>. This is easiest to demo."""
    preferred_language = normalize_language(request.args.get("language") or request.form.get("language"), fallback="english")
    twilio_lang = language_option(preferred_language).twilio_code
    resp = VoiceResponse()
    greeting = "Hello, you are talking to CalmMind AI. Please share what you are feeling after the beep."
    if preferred_language in {"hindi", "hinglish"}:
        greeting = "Namaste, aap CalmMind AI se baat kar rahe hain. Beep ke baad batayein aap kya feel kar rahe hain."
    resp.say(greeting, voice="alice", language=twilio_lang)
    gather = Gather(input="speech", action=f"/twilio/process-speech?language={preferred_language}", method="POST", speech_timeout="auto", language=twilio_lang)
    gather.say("I am listening now.", voice="alice", language=twilio_lang)
    resp.append(gather)
    resp.redirect("/twilio/voice", method="POST")
    return _twiml(resp)


@call_bp.post("/twilio/process-speech")
def twilio_process_speech():
    preferred_language = normalize_language(request.args.get("language") or request.form.get("language"), fallback="english")
    twilio_lang = language_option(preferred_language).twilio_code
    call_sid = request.form.get("CallSid", "unknown_call")
    speech = request.form.get("SpeechResult", "").strip()
    user_id = f"phone_{request.form.get('From', 'anonymous')[-10:]}".replace("+", "")
    ensure_user(user_id, display_name="Phone User")

    resp = VoiceResponse()
    if not speech:
        resp.say("I could not hear that clearly. Please try again.", voice="alice", language=twilio_lang)
        resp.redirect(f"/twilio/voice?language={preferred_language}", method="POST")
        return _twiml(resp)

    result = build_ai_reply(user_id=user_id, message=speech, input_type="call", preferred_language=preferred_language)
    execute(
        "INSERT INTO call_sessions(call_sid, user_id, user_phone, transcript, summary, risk_level, language, status, started_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (call_sid, user_id, request.form.get("From", ""), speech, result.get("reply", "")[:500], result.get("risk_level"), preferred_language, "active", utc_now()),
    )
    resp.say(_safe_say(result.get("reply", "")), voice="alice", language=twilio_lang)
    gather = Gather(input="speech", action=f"/twilio/process-speech?language={preferred_language}", method="POST", speech_timeout="auto", language=twilio_lang)
    gather.say("You can say more, or hang up when you are done.", voice="alice", language=twilio_lang)
    resp.append(gather)
    return _twiml(resp)


@call_bp.post("/twilio/stream")
def twilio_stream_twiml():
    """Real-time media stream scaffold. Needs public wss URL and streaming STT/TTS integration."""
    resp = VoiceResponse()
    connect = Connect()
    public = config.PUBLIC_BASE_URL.replace("https://", "wss://").replace("http://", "ws://")
    connect.append(Stream(url=f"{public}/ws/twilio-media"))
    resp.append(connect)
    return _twiml(resp)


@call_bp.get("/api/calls/history")
def call_history():
    user_id = request.args.get("user_id", "phone_user")
    rows = fetch_all("SELECT * FROM call_sessions WHERE user_id=? ORDER BY id DESC LIMIT 30", (user_id,))
    return jsonify({"calls": rows})


def init_twilio_socket(sock):
    @sock.route("/ws/twilio-media")
    def twilio_media_socket(ws):
        """Raw Twilio WebSocket listener scaffold.

        This stores stream lifecycle events. To make it fully speech-to-speech,
        connect media payloads to streaming STT, call build_ai_reply(), then send
        Twilio-compatible base64 mulaw audio media messages back through ws.send().
        """
        stream_sid = None
        call_sid = None
        while True:
            message = ws.receive()
            if message is None:
                break
            try:
                event = json.loads(message)
            except Exception:
                continue
            event_type = event.get("event")
            if event_type == "start":
                start = event.get("start", {})
                stream_sid = start.get("streamSid") or event.get("streamSid")
                call_sid = start.get("callSid")
                execute(
                    "INSERT INTO call_sessions(call_sid, user_id, transcript, summary, risk_level, started_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (call_sid or stream_sid or "stream", "phone_stream_user", "[media stream started]", "Real-time stream scaffold started.", "low", utc_now()),
                )
            elif event_type == "stop":
                break

# CalmMind AI Final Build Features

This final build includes Phase 1 to Phase 4 plus the requested call/v-call and multilingual support facility.

## Included Phases

- Phase 1: Professional chat UI, sidebar, sessions, history, typing animation, badges.
- Phase 2: Advanced AI brain, intent detection, emotion detection, risk scoring, memory, RAG, professional response controller.
- Phase 3: Crisis safety system, emergency resources, safety plan, risk audit logs.
- Phase 4: Advanced dashboard, charts, weekly report, JSON/CSV export.
- Final additions: trusted contact calling, emergency call buttons, v-call room creation, camera preview, multilingual chat/voice/call controls.

## New User Facilities

### 1. Multilingual conversation
The user can choose:
- Auto Detect
- Hinglish
- Hindi
- English
- Punjabi
- Marathi
- Telugu
- Urdu
- French
- Chinese

The selected language is sent to the backend with every chat/voice request. The AI response controller instructs the LLM to reply in the selected language.

### 2. Exact voice reply
The browser TTS speaks exactly the final AI response text returned by the backend. It does not generate a different response for speech.

### 3. Call someone
The `/connect` page includes:
- Call Emergency 112
- Call Tele-MANAS 14416
- Save trusted contacts
- Call trusted contacts with `tel:` links
- SMS/message trusted contacts

### 4. V-Call support
The `/connect` or `/vcall` page includes:
- Camera preview
- Create video support room
- Open v-call room
- Copy/share v-call link
- Recent v-call rooms

### 5. AI phone call demo
The existing Twilio AI phone call route supports selected language in the webhook URL:

```text
POST https://your-ngrok-url/twilio/voice?language=hinglish
```

Supported language values:

```text
hinglish, hindi, english, punjabi, marathi, telugu, urdu, french, chinese
```

Note: Twilio voice/STT support varies by region and voice. The browser chat/voice language support is controlled through Web Speech API settings.

## New Files

- `routes/connect_routes.py`
- `services/contact_service.py`
- `services/language_service.py`
- `templates/connect.html`
- `docs/FINAL_BUILD_FEATURES.md`

## Important Changed Files

- `app.py`
- `routes/chat_routes.py`
- `routes/call_routes.py`
- `routes/voice_routes.py`
- `services/ai_service.py`
- `services/db_service.py`
- `services/response_controller.py`
- `services/safety_service.py`
- `templates/base.html`
- `templates/chat.html`
- `templates/index.html`
- `static/js/app.js`
- `static/css/styles.css`

## Run

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python app.py
```

Open:

```text
http://127.0.0.1:5000
http://127.0.0.1:5000/chat
http://127.0.0.1:5000/connect
http://127.0.0.1:5000/dashboard
```

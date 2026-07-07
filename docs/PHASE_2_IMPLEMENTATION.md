# Phase 2 Implementation — Advanced AI Brain

This phase upgrades CalmMind from a professional chat UI into an AI-brain pipeline that analyzes every user message before generating a response.

## Added in Phase 2

### 1. Intent Detection
The bot now detects intent categories such as:
- study_stress
- relationship_issue
- sleep_problem
- panic_anxiety
- motivation
- career_confusion
- wellness_tool
- journal_reflection
- general_question
- mental_health_support

### 2. Emotion Detection
The bot now detects richer emotional signals:
- anxious
- panic
- sad
- lonely
- angry
- tired
- positive
- neutral

### 3. Risk Scoring
Risk is now represented as both a label and score:
- low
- medium
- high
- emergency

The system stores risk_score, safety categories, and recommended safety action.

### 4. Personalization Memory
New service: `services/memory_service.py`

The app stores safe user-level patterns:
- preferred language
- common emotions
- common intents
- common triggers
- helpful coping tools
- last mood score
- memory summary

Memory can be viewed in chat and reset from the UI.

### 5. RAG Knowledge Base
`services/rag_service.py` now returns structured knowledge hits from `data/resources.json`.

The AI response controller can use approved local knowledge for mental-health support topics.

### 6. Professional Response Controller
New service: `services/response_controller.py`

It controls:
- system prompt
- response style
- disclaimer handling
- fallback response quality
- safe post-processing

### 7. Database Upgrades
Added/updated:
- `user_memory`
- `conversation_insights`
- extra message metadata: language, triggers, knowledge_used, risk_score, response_style
- risk event metadata: risk_score, categories, recommended_action
- session metadata: dominant_emotion, dominant_intent, max_risk_level

### 8. New API Endpoints
- `POST /api/brain/analyze`
- `GET /api/memory/profile`
- `PATCH /api/memory/profile`
- `DELETE /api/memory/profile`

## How to Test

Run:

```bash
python app.py
```

Open:

```text
http://127.0.0.1:5000/chat
```

Test messages:

```text
mujhe exam deadline ka bahut stress ho raha hai
```

Expected:
- intent: study_stress
- emotion: anxious
- trigger: exam_pressure/project_deadline
- recommended tool: study_micro_plan or box_breathing

```text
mujhe panic ho raha hai aur saans nahi aa rahi
```

Expected:
- emotion: panic
- intent: panic_anxiety
- recommended tool: grounding_54321
- risk may be medium

```text
mujhe jeena nahi hai
```

Expected:
- risk: high
- crisis protocol response
- risk event logged

## Changed Files

- `services/ai_service.py`
- `services/mood_service.py`
- `services/safety_service.py`
- `services/rag_service.py`
- `services/memory_service.py`
- `services/response_controller.py`
- `services/db_service.py`
- `routes/chat_routes.py`
- `templates/chat.html`
- `static/js/app.js`
- `static/css/styles.css`
- `data/resources.json`
- `tests/test_phase2_ai_brain.py`

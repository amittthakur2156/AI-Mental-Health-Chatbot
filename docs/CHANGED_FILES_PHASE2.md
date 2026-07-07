# Phase 2 Changed Files

## Backend Services
- `services/ai_service.py` — advanced AI pipeline: mood, safety, memory, RAG, response controller, insight logging
- `services/mood_service.py` — intent, emotion, language, trigger, mood score, tool recommendation
- `services/safety_service.py` — risk scoring, safety categories, crisis protocol, final safety filter
- `services/rag_service.py` — structured approved-knowledge retrieval
- `services/memory_service.py` — user-level personalization memory
- `services/response_controller.py` — system prompt, response style, post-processing, fallback responses
- `services/db_service.py` — Phase 2 schema migrations and new tables

## Routes
- `routes/chat_routes.py` — added brain analysis and memory profile APIs

## Frontend
- `templates/chat.html` — Phase 2 AI brain panel, memory panel, knowledge panel
- `static/js/app.js` — risk score, language, trigger, recommended tool, knowledge, memory UI updates
- `static/css/styles.css` — memory/knowledge cards styling

## Data
- `data/resources.json` — expanded approved mental-health knowledge base

## Tests/Docs
- `tests/test_phase2_ai_brain.py`
- `docs/PHASE_2_IMPLEMENTATION.md`
- `docs/CHANGED_FILES_PHASE2.md`
- `README.md`

# CalmMind AI Mental Health Chatbot — Advanced Project Blueprint

## 1. Final Vision
Build CalmMind as a professional multimodal mental-health support platform: text chat, browser voice chat, phone-call AI assistant, mood analytics, journaling, crisis safety detection, personalized recommendations, and admin/mentor monitoring.

Important positioning: CalmMind should be a supportive wellness companion, not a replacement for a doctor, therapist, emergency service, or crisis helpline.

---

## 2. Main User Modes

### A. Text Chat Mode
- Hinglish/English conversation
- Emotion-aware responses
- Context memory per user
- Conversation history
- Mood score per message
- Suggested coping tools
- Safe response layer for self-harm, suicide, violence, abuse, panic, or emergency content

### B. Browser Voice Mode
- User clicks mic button
- Browser records audio
- Speech-to-text converts user voice into text
- AI generates response
- Text-to-speech speaks answer back
- Transcript is saved in chat history

### C. Live Call Mode
- User calls a phone number
- Twilio streams audio to backend through WebSocket
- Backend transcribes audio
- AI generates response
- TTS converts answer to audio
- Audio is sent back into call
- Conversation summary and risk score are saved

### D. Mood Journal Mode
- Daily journal entries
- Gratitude notes
- Mood rating
- AI summary and suggestions
- Weekly mood reports

### E. Dashboard Mode
- Mood trend graph
- Stress/anxiety frequency
- Crisis/high-risk events count
- Journaling streak
- Most common triggers
- Recommended coping exercises

---

## 3. Advanced Features To Add

### 3.1 AI Brain Upgrade
- Multi-intent classifier: mental health, study stress, relationship, sleep, general Q&A, productivity, crisis
- Emotion classifier: sadness, anxiety, anger, loneliness, panic, neutral, positive
- Risk classifier: low, medium, high, emergency
- Personalized user profile memory
- Retrieval-Augmented Generation knowledge base for approved mental-health content
- Response style controller: calm, professional, short, detailed, motivational
- Follow-up question generator
- Session summary generator

### 3.2 Safety System
- Crisis keyword + AI risk classifier
- Emergency escalation messages
- India emergency resources: 112, Tele-MANAS 14416/1800-891-4416, trusted-contact prompt
- “Are you safe right now?” check
- Safety plan: warning signs, coping actions, trusted contacts, safe places
- Block harmful instructions
- Add disclaimer: supportive assistant, not medical diagnosis
- Admin flag for high-risk messages in project demo mode

### 3.3 Voice Features
- Push-to-talk mic
- Continuous conversation mode
- Interrupt/stop speaking button
- Voice selection
- Speaking speed control
- Auto language detection: Hindi/Hinglish/English
- Real-time waveform animation
- Save voice transcript

### 3.4 Phone Call Features
- Twilio phone number integration
- WebSocket audio stream endpoint
- Real-time STT pipeline
- AI response pipeline
- TTS audio response pipeline
- Call transcript storage
- Call duration and summary
- Risk alert after call
- Optional human handoff flow

### 3.5 Professional UI
- Landing page
- Login/signup
- Chat page with sidebar history
- Voice call interface
- Mood dashboard
- Journal page
- Safety plan page
- Resources page
- Admin dashboard
- Profile/settings page
- Dark/light theme
- Mobile responsive design

### 3.6 Admin / Research Panel
- Total users
- Total conversations
- Average mood score
- High-risk flagged sessions
- Usage by feature
- Anonymous analytics
- Export CSV/JSON
- Safety audit logs

### 3.7 Data & Database
Suggested database: PostgreSQL for production, SQLite for local demo.

Tables:
- users
- chat_sessions
- messages
- mood_logs
- journals
- safety_plans
- call_sessions
- voice_transcripts
- resources
- risk_events
- feedback

### 3.8 Security
- Firebase Auth verification on backend
- Store only Firebase UID, not passwords
- Rate limiting
- Input validation
- API keys only in .env
- HTTPS deployment
- CORS restrictions
- Database backups
- Delete/export user data option
- Consent screen for storing mental-health conversations

---

## 4. Recommended Architecture

Frontend:
- HTML/CSS/JS for current project OR React for advanced version
- Web Speech API / MediaRecorder for browser voice
- Chart.js/Recharts for dashboard graphs

Backend:
- Flask for current codebase
- Flask-SocketIO for real-time browser voice
- Twilio WebSocket endpoint for phone calls
- Groq/OpenAI model layer
- Safety classifier layer
- Database service layer

AI Services:
- LLM for response generation
- STT for audio-to-text
- TTS for text-to-audio
- Embeddings/vector DB for knowledge base

Storage:
- PostgreSQL/Supabase/Firebase Firestore for production
- SQLite for demo

Deployment:
- Render/Railway/Fly.io for backend
- Firebase/Vercel/Netlify for frontend
- Supabase/Firebase for DB
- Twilio for call number

---

## 5. Suggested Folder Structure

calmmind_pro/
  app.py
  config.py
  requirements.txt
  .env.example
  services/
    ai_service.py
    safety_service.py
    mood_service.py
    voice_service.py
    call_service.py
    auth_service.py
    db_service.py
    rag_service.py
  routes/
    chat_routes.py
    voice_routes.py
    call_routes.py
    journal_routes.py
    dashboard_routes.py
    admin_routes.py
  static/
    css/
    js/
    assets/
  templates/
    index.html
    chat.html
    dashboard.html
    journal.html
    safety.html
    admin.html
  data/
    resources.json
  tests/
    test_safety.py
    test_chat.py
    test_mood.py

---

## 6. API Endpoints

Authentication:
- POST /api/auth/verify

Chat:
- POST /api/chat
- GET /api/history
- DELETE /api/history

Mood:
- GET /api/mood/summary
- GET /api/mood/trends

Journal:
- POST /api/journal
- GET /api/journal
- DELETE /api/journal/<id>

Safety:
- POST /api/safety-plan
- GET /api/safety-plan
- POST /api/crisis-check

Voice:
- POST /api/voice/transcribe
- POST /api/voice/speak
- WebSocket /ws/voice

Calls:
- POST /twilio/voice
- WebSocket /ws/twilio-media
- GET /api/calls/history

Admin:
- GET /api/admin/analytics
- GET /api/admin/risk-events

---

## 7. AI Response Pipeline

1. Receive message/audio transcript
2. Clean input
3. Detect language
4. Classify intent
5. Classify emotion
6. Classify risk level
7. If high risk: use crisis protocol
8. Retrieve user memory and recent chat context
9. Retrieve approved knowledge-base content if needed
10. Generate professional response
11. Save message, mood score, risk score
12. Return text + optional audio

---

## 8. Crisis Protocol

High-risk message response should:
- Validate emotion
- Ask user to move away from harmful means
- Ask user to contact trusted person immediately
- Suggest emergency services if immediate danger
- Give India resources such as 112 and Tele-MANAS
- Avoid long lectures
- Avoid harmful details
- Ask a grounding question: “Are you safe right now?”

---

## 9. Final-Year Project Documentation Sections

- Abstract
- Introduction
- Problem statement
- Objectives
- Existing system
- Proposed system
- System architecture
- Module description
- Algorithm / workflow
- Database design
- UI screenshots
- Testing
- Result analysis
- Limitations
- Future scope
- Conclusion
- References

---

## 10. Implementation Phases

### Phase 1: Core Professional Chatbot
- Clean UI
- Chat history
- Mood detection
- Safety layer
- Firebase UID backend verification

### Phase 2: Dashboard + Journal
- Mood analytics
- Journal CRUD
- Safety plan
- Export report

### Phase 3: Voice Chat
- Browser mic
- STT
- TTS
- Transcript save
- Voice UI

### Phase 4: Phone Call AI
- Twilio setup
- WebSocket stream
- STT + AI + TTS loop
- Call transcript and summary

### Phase 5: RAG + Personalization
- Approved mental-health resources
- Vector search
- User preference memory
- Weekly summaries

### Phase 6: Admin + Deployment
- Admin dashboard
- Logs
- Production deployment
- Documentation and demo video

---

## 11. Demo Script

1. User signs up/login
2. User chats about stress
3. Bot detects mood and gives professional support
4. User speaks through mic
5. Bot replies by voice
6. Dashboard shows mood trend
7. User writes journal
8. User creates safety plan
9. User triggers crisis demo message; bot safely escalates
10. Admin panel shows anonymous analytics
11. Optional: phone call demo with Twilio

---

## 12. Most Impressive Features For Evaluation

- Real-time voice conversation
- Phone-call AI assistant
- Mood analytics dashboard
- Safety-risk detection
- Personalized coping recommendations
- Journal summaries
- Admin analytics panel
- RAG knowledge base
- Professional responsive UI
- Deployment with live demo URL

# API Endpoints

## Chat
- `POST /api/chat`
- `GET /api/history`
- `DELETE /api/history`
- `GET /api/export`

## Voice
- `GET /api/voice/capabilities`
- `POST /api/voice/message`
- `POST /api/voice/speak`
- Socket.IO event: `voice_text`

## Mood
- `GET /api/mood/summary`
- `GET /api/mood/trends`

## Journal
- `POST /api/journal`
- `GET /api/journal`
- `DELETE /api/journal/<id>`

## Safety
- `POST /api/crisis-check`
- `GET /api/safety-plan`
- `POST /api/safety-plan`

## Calls
- `POST /twilio/voice`
- `POST /twilio/process-speech`
- `POST /twilio/stream`
- `WebSocket /ws/twilio-media`
- `GET /api/calls/history`

## Admin
- `GET /api/admin/analytics`
- `GET /api/admin/risk-events`

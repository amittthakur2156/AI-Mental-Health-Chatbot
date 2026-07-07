# Phase 4 Implementation — Advanced Mood Dashboard

## Goal
Phase 4 upgrades CalmMind AI from a basic analytics page into a professional mood intelligence dashboard.

## Added Features

### Advanced Dashboard Cards
- Average mood
- Selected range average mood
- Active streak
- Top emotion
- Top intent
- User message count
- Session count
- Voice transcript count
- Risk event count
- High-risk event count
- Journal count

### Charts
- Mood trend line chart
- Emotion distribution doughnut chart
- Activity breakdown bar chart
- Risk monitoring chart
- Mood calendar heatmap

### AI Weekly Wellness Report
The dashboard now generates a structured wellness report based on:
- Average mood
- Trend direction
- Top emotion
- Activity count
- High-risk safety events
- Recommendations

### Export
- JSON export: `/api/mood/export/json`
- CSV export: `/api/mood/export/csv`

## New File
- `services/analytics_service.py`

This file centralizes dashboard calculations so routes stay clean and the project becomes more maintainable.

## Changed Files
- `routes/dashboard_routes.py`
- `templates/dashboard.html`
- `static/js/app.js`
- `static/css/styles.css`

## New API Endpoints

```text
GET /api/mood/summary?days=30
GET /api/mood/trends?days=30
GET /api/mood/emotions?days=30
GET /api/mood/activity?days=30
GET /api/mood/risk-trends?days=30
GET /api/mood/heatmap?days=90
GET /api/mood/weekly-report?days=7
GET /api/mood/export/json
GET /api/mood/export/csv
```

## Notes
This phase does not require a database schema change. It uses existing tables:
- `mood_logs`
- `messages`
- `voice_transcripts`
- `journals`
- `risk_events`
- `chat_sessions`

## Final-Year Project Value
This phase adds strong result-analysis capability. It helps show that the system is not just a chatbot but a measurable mental wellness monitoring and insight platform.

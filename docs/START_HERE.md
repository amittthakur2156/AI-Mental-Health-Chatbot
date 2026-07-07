# Start Here — CalmMind Pro Implementation Plan

## Day 1: Run the project
1. Create venv
2. Install requirements
3. Copy `.env.example` to `.env`
4. Run `python app.py`
5. Open `/chat`

## Day 2: Connect AI
1. Add `GROQ_API_KEY` in `.env`
2. Ask mental health questions
3. Ask general questions
4. Test Hinglish replies

## Day 3: Test safety
Try demo prompts such as:
- "I feel hopeless"
- "Mujhe jeena nahi hai"
- "I feel unsafe"

Check `/admin` for risk events.

## Day 4: Dashboard + Journal
1. Send 5-10 chat messages
2. Add 2 journal entries
3. Open `/dashboard`
4. Take screenshots for report

## Day 5: Voice
1. Open `/chat` in Chrome or Edge
2. Click mic
3. Speak in Hindi/Hinglish/English
4. Check that transcript is saved

## Day 6: Twilio phone call demo
1. Install ngrok
2. Run `ngrok http 5000`
3. Put ngrok URL in `.env` as `PUBLIC_BASE_URL`
4. In Twilio number settings, set voice webhook to `https://your-url/twilio/voice`
5. Call your Twilio number

## Day 7: Report + Demo Video
Record this flow:
1. Login/demo user
2. Text chat
3. Voice chat
4. Mood dashboard
5. Journal
6. Safety plan
7. Crisis safety response
8. Admin analytics
9. Optional phone call demo


## Browser URL

After running `python app.py`, open:

```
http://127.0.0.1:5000
```

Do not open `http://0.0.0.0:5000` in the browser.

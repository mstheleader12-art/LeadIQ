# LeadIQ 2.0 — AI Lead Scoring + Chat Assistant

LeadIQ 2.0 is a student-friendly full-stack prototype. It includes a lead prioritisation dashboard, transparent scoring, Gemini-powered explanations, and a ChatGPT-style chatbot.

## Features
- Lead scoring from 0–100 using profile fit, buying intent, engagement, source and recency.
- HOT / WARM / COLD prioritisation with reasons and suggested next action.
- Gemini API integration for natural-language explanations and chatbot replies.
- Demo mode works without an API key.
- Frontend never receives the Gemini key; requests go through the FastAPI backend.
- Responsive dashboard and CSV export.

## Run on Windows (VS Code)
1. Install Python 3.10+.
2. Extract this ZIP and open the `LeadIQ_2_0` folder in VS Code.
3. Open Terminal in VS Code and run:
   ```powershell
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   copy .env.example .env
   ```
4. Start the website:
   ```powershell
   uvicorn app:app --reload
   ```
5. Open http://127.0.0.1:8000

It works immediately in Demo Mode.

## Enable Gemini
1. Create a Gemini API key in Google AI Studio: https://aistudio.google.com/app/apikey
2. Open the backend `.env` file.
3. Replace `PASTE_YOUR_GEMINI_API_KEY_HERE` with your actual key:
   ```env
   GEMINI_API_KEY=your_real_key_here
   GEMINI_MODEL=gemini-2.5-flash
   ```
4. Save and restart the server (`Ctrl+C`, then run the uvicorn command again).
5. The status indicator should show Gemini AI.

## Security
- Never paste your key into `static/index.html`, browser JavaScript, screenshots, or GitHub.
- Keep `.env` private. It is excluded by `.gitignore`.
- Do not commit `.env` to a repository.
- If a key is exposed, revoke it and create a replacement.
- For public deployment, use the hosting provider's secret/environment-variable settings and HTTPS.

## How the score works
- Profile fit: fit rating × 4 (max 20)
- Buying intent: intent rating × 7 (max 35)
- Engagement: engagement rating × 5 (max 25)
- Source: referral 10, website 8, LinkedIn 7, event 6, cold outreach 3
- Recency: max(0, 10 − days since activity)
- HOT: 75–100; WARM: 50–74; COLD: 0–49

This is a transparent rule-based prioritisation score, not a statistically trained model or calibrated conversion probability. Gemini generates explanations and chat responses; it does not secretly change the numeric score.

## API routes
- `GET /api/status`
- `POST /api/score`
- `POST /api/chat`

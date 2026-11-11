import asyncio
import os
from typing import List, Dict, Any
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import httpx

load_dotenv()
app = FastAPI(title="LeadIQ 2.0 API")

MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"

class Lead(BaseModel):
    name: str = "New lead"
    company: str = ""
    role: str = ""
    budget: int = Field(default=5000, ge=0, le=100000000)
    intent: int = Field(default=3, ge=1, le=5)
    engagement: int = Field(default=3, ge=1, le=5)
    fit: int = Field(default=3, ge=1, le=5)
    source: str = "Website"
    days_since_activity: int = Field(default=2, ge=0, le=3650)

class ChatRequest(BaseModel):
    message: str
    history: List[Dict[str, str]] = []

def score_lead(lead: Lead):
    profile = lead.fit * 4
    intent = lead.intent * 7
    engagement = lead.engagement * 5
    source = {"Referral": 10, "Website": 8, "LinkedIn": 7, "Event": 6, "Cold outreach": 3}.get(lead.source, 5)
    recency = max(0, 10 - lead.days_since_activity)
    score = min(100, profile + intent + engagement + source + recency)
    status = "HOT" if score >= 75 else ("WARM" if score >= 50 else "COLD")
    action = "Contact within 1 business day" if status == "HOT" else ("Send a tailored follow-up and useful case study" if status == "WARM" else "Add to a low-frequency nurture sequence")
    reasons = [
        f"Profile fit: {lead.fit}/5",
        f"Buying intent: {lead.intent}/5",
        f"Engagement: {lead.engagement}/5",
        f"Lead source: {lead.source}",
        f"Last activity: {lead.days_since_activity} day(s) ago"
    ]
    return {"score": score, "status": status, "action": action, "reasons": reasons}

async def gemini(prompt: str):
    key = os.getenv("GEMINI_API_KEY", "").strip()

    if not key or key == "PASTE_YOUR_GEMINI_API_KEY_HERE":
        return None

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.45,
            "maxOutputTokens": 500
        }
    }

    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    API_URL,
                    headers={"x-goog-api-key": key},
                    json=payload
                )

            if response.status_code in [429, 500, 502, 503, 504]:
                print("GEMINI TEMPORARY ERROR:", response.status_code)
                print("RESPONSE:", response.text[:1000])

                if attempt < 2:
                    await asyncio.sleep(2 ** (attempt + 1))
                    continue

            response.raise_for_status()

            data = response.json()

            return data["candidates"][0]["content"]["parts"][0]["text"]

        except httpx.RequestError as e:
            print("GEMINI NETWORK ERROR:", repr(e))

            if attempt < 2:
                await asyncio.sleep(2 ** (attempt + 1))
                continue

            raise

        except httpx.HTTPStatusError as e:
            print("GEMINI API ERROR:", e.response.status_code)
            print("ERROR DETAILS:", e.response.text[:1000])
            raise

    raise RuntimeError("Gemini request failed after 3 attempts.")

@app.get("/api/status")
def status():
    key = os.getenv("GEMINI_API_KEY", "").strip()
    configured = bool(key and key != "PASTE_YOUR_GEMINI_API_KEY_HERE")
    return {"gemini_configured": configured, "model": MODEL, "mode": "Gemini AI" if configured else "Demo mode"}

@app.post("/api/score")
async def score(lead: Lead):
    result = score_lead(lead)
    prompt = (
        "You are LeadIQ, a careful sales lead-scoring assistant. Explain this transparent rule-based score "
        "in 2-3 concise sentences and give one practical next step. Do not claim the score predicts conversion. "
        f"Lead: {lead.model_dump()}. Result: {result}."
    )
    try:
        ai_text = await gemini(prompt)
    except Exception:
        ai_text = None
    result["ai_explanation"] = ai_text or (
        f"{lead.name} is classified as {result['status']} with a score of {result['score']}/100. "
        "This is a transparent prioritisation score based on the supplied fit, intent, engagement, source and recency signals. "
        "It is not a calibrated probability of conversion."
    )
    result["mode"] = "Gemini AI" if ai_text else "Demo / rule-based"
    return result

@app.post("/api/chat")
async def chat(req: ChatRequest):
    context = "You are LeadIQ Assistant, a helpful ChatGPT-style assistant embedded in a lead scoring and sales prioritisation website. "
    context += "Explain lead scoring, interpret user-provided lead data, suggest ethical sales follow-ups, and help use the dashboard. "
    context += "Be concise, practical, and honest. Do not invent CRM data or claim access to external systems. "
    context += "Explain that the site's numerical score is a rule-based prioritisation score, not a conversion probability. "
    history = req.history[-8:]
    transcript = "\n".join([f"{m.get('role','user')}: {m.get('content','')}" for m in history])
    prompt = context + "\nConversation:\n" + transcript + "\nuser: " + req.message + "\nassistant:"
    try:
        answer = await gemini(prompt)
    except Exception as e:
        print("GEMINI CHAT ERROR:", repr(e))
        answer = None
    if not answer:
        answer = (
            "I'm running in **Demo Mode** because a Gemini API key hasn't been configured yet. "
            "I can still help with the basics: score leads using fit, buying intent, engagement, source and recency; "
            "prioritise HOT leads first; personalise follow-ups; and review the score reasons shown by LeadIQ. "
            "Add your key to the backend `.env` file and restart the server to enable Gemini-powered chat."
        )
    return {"reply": answer, "mode": "Gemini AI" if os.getenv("GEMINI_API_KEY", "").strip() not in ("", "PASTE_YOUR_GEMINI_API_KEY_HERE") else "Demo mode"}

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def home():
    return FileResponse("static/index.html")

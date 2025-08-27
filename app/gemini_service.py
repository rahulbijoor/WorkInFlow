import json
from typing import List, Optional
import google.generativeai as genai
from .config import GEN_MODEL, EMBED_MODEL
from fastapi import HTTPException
from .models import AISummary

SYSTEM_JSON = """You are an executive assistant.
Return STRICT JSON with keys:
summary_160 (<=160 chars),
importance ("low"|"medium"|"high"),
urgency ("low"|"medium"|"high"),
actionable (true|false),
next_steps (array of 1-3 terse steps),
suggested_due_iso (ISO-8601 string or null),
confidence (0..1).
Consider explicit deadlines, mentions of the user, and whether the sender is waiting on the user.
"""

def embed_batch(texts: List[str]) -> List[List[float]]:
    vecs = []
    for t in texts:
        r = genai.embed_content(model=EMBED_MODEL, content=t)
        vec = r.get("embedding") or r["embedding"]
        vecs.append(vec)
    return vecs

def gemini_summarize(message_text: str, subject: Optional[str], sender: Optional[str]) -> AISummary:
    prompt = f"""{SYSTEM_JSON}

Message:
<<<
Subject: {subject or ""}
From: {sender or ""}
Body: {message_text}
>>>"""
    model = genai.GenerativeModel(GEN_MODEL)
    resp = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=0.2,
            max_output_tokens=300,
            response_mime_type="application/json",
        ),
    )
    if not resp or not getattr(resp, "text", ""):
        raise HTTPException(status_code=502, detail="LLM returned empty.")
    try:
        data = json.loads(resp.text)
    except Exception:
        cleaned = resp.text.strip().strip("`").replace("json\n", "").strip()
        data = json.loads(cleaned)
    return AISummary(**data)

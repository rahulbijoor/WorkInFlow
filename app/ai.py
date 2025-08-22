import json
from typing import List, Optional
import google.generativeai as genai
from app import config
from app.models import AISummary

# Configure Gemini once
genai.configure(api_key=config.GEMINI_API_KEY)

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
        r = genai.embed_content(model=config.EMBED_MODEL, content=t)
        vecs.append(r.get("embedding") or r["embedding"])
    return vecs

def generate_text(prompt: str, temperature: float = 0.2, max_output_tokens: int = 400) -> str:
    model = genai.GenerativeModel(config.GEN_MODEL)
    resp = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_output_tokens
        )
    )
    if not resp or not getattr(resp, "text", ""):
        raise ValueError("LLM returned empty.")
    return resp.text

def generate_json(prompt: str, temperature: float = 0.2, max_output_tokens: int = 400) -> dict:
    model = genai.GenerativeModel(config.GEN_MODEL)
    resp = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            response_mime_type="application/json"
        )
    )
    if not resp or not getattr(resp, "text", ""):
        raise ValueError("LLM returned empty.")
    try:
        return json.loads(resp.text)
    except Exception:
        cleaned = resp.text.strip().strip("`").replace("json\n", "").strip()
        return json.loads(cleaned)

def gemini_summarize(message_text: str, subject: Optional[str], sender: Optional[str]) -> AISummary:
    prompt = f"""{SYSTEM_JSON}

Message:
<<<
Subject: {subject or ""}
From: {sender or ""}
Body: {message_text}
>>>"""
    data = generate_json(prompt, temperature=0.2, max_output_tokens=300)
    return AISummary(**data)

def parse_slack_send(query: str) -> dict:
    """
    Turn a natural instruction like:
      'tell tom I’m working on it' or 'dm @tom we’re on track'
    into JSON: {"targets":[{"type":"user","name":"tom"}], "text":"I'm working on it"}
    Supports #channel too.
    """
    schema = """Return STRICT JSON:
{
  "targets": [{"type":"user|channel","name":"string"}],
  "text": "string"
}"""
    prompt = f"""{schema}

Instruction:
{query}

Rules:
- Extract recipients as users (e.g., '@tom', 'tom') or channels (e.g., '#general').
- 'to', 'for', 'dm', 'message', 'tell' are hints.
- Put only the final message in 'text' (no extra quotes).
- If multiple recipients, include them all in targets.
"""
    return generate_json(prompt, temperature=0, max_output_tokens=200)

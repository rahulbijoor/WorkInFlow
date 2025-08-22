import math
from typing import Optional
from app.models import AISummary
from app.utils import now_ms

def map_level(lvl: str) -> float:
    lvl = (lvl or "").lower()
    return {"low": 0.2, "medium": 0.6, "high": 1.0}.get(lvl, 0.6)

def recency_decay(hours_since: float) -> float:
    return math.exp(-hours_since / 72.0)

def compute_priority(ai: AISummary, internal_ms: int, sender_role: Optional[str] = None, blocked_flag: bool = False) -> float:
    now = now_ms()
    hours_since = max(0, (now - internal_ms) / 3600000.0)
    urgency = map_level(ai.urgency)
    importance = map_level(ai.importance)

    deadline_proximity = 0.0
    if ai.suggested_due_iso:
        try:
            from datetime import datetime, timezone
            due = datetime.fromisoformat(ai.suggested_due_iso.replace("Z","+00:00"))
            hrs = (due.replace(tzinfo=timezone.utc).timestamp()*1000 - now) / 3600000.0
            deadline_proximity = max(0.0, min(1.0, (72 - hrs)/72))
        except Exception:
            pass

    sender_tier = {"exec":1.0, "customer":1.0, "pm":0.6, "ic":0.2}.get((sender_role or "").lower(), 0.2)
    rec = recency_decay(hours_since)
    blocker = 1.0 if blocked_flag else 0.0

    score = 35*urgency + 25*importance + 15*deadline_proximity + 10*blocker + 10*sender_tier + 5*rec
    return round(score, 3)

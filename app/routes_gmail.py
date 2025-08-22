from typing import List
from fastapi import APIRouter, HTTPException
from .models import InboxItem
from .gmail_service import list_recent_messages, get_message, header_lookup
from .gemini_service import gemini_summarize
from .priority import compute_priority

router = APIRouter()

@router.get("/gmail/recent", response_model=List[InboxItem])
def gmail_recent(max_results: int = 5):
    try:
        msgs = list_recent_messages(max_results=max_results)
        items: List[InboxItem] = []
        for m in msgs:
            full = get_message(m["id"])
            headers = full.get("payload", {}).get("headers", [])
            subject = header_lookup(headers, "Subject")
            sender = header_lookup(headers, "From")
            snippet = full.get("snippet", "") or ""
            internal_ts = int(full.get("internalDate", "0"))
            ai = gemini_summarize(snippet, subject, sender)
            lower = snippet.lower()
            blocked = any(k in lower for k in ["waiting on you", "blocked", "need by", "asap", "urgent", "eod", "by eod"])
            score = compute_priority(ai, internal_ts, sender_role=None, blocked_flag=blocked)

            items.append(InboxItem(
                source="gmail",
                id=full.get("id"),
                thread_id=full.get("threadId"),
                subject=subject,
                from_=sender,
                snippet=snippet,
                internal_ts=internal_ts,
                url=f"https://mail.google.com/mail/u/0/#inbox/{full.get('id')}",
                ai=ai,
                priority_score=score
            ))
        items.sort(key=lambda x: x.priority_score or 0, reverse=True)
        return items
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch Gmail: {e}")

@router.get("/summarize_email")
def summarize_email():
    items = gmail_recent(max_results=1)
    if not items:
        return {"email_snippet": "No emails found.", "summary": ""}
    first = items[0]
    return {
        "email_snippet": first.snippet,
        "summary_json": first.ai.dict() if first.ai else {},
        "priority_score": first.priority_score,
        "subject": first.subject,
        "from": first.from_,
        "url": first.url
    }

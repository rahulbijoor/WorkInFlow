from __future__ import annotations
from typing import Optional, List, Dict, Any
import uuid, json

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from app import config
from app.models import KBIngestResponse, KBAnswer, FlashcardSet, InboxItem, SlackSendRequest, SlackSendResult
from app.models import TaskListResponse, Task
from app.pm.aggregator import list_tasks_all
from app.pm.jira_provider import JiraProvider

from app import utils, ai, kb_store, priority, gmail_service

from pydantic import BaseModel
from app import slack_service
from app.ai import parse_slack_send


app = FastAPI(title=config.APP_TITLE, version=config.APP_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in config.ALLOWED_ORIGINS if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)

@app.get("/")
def home():
    return {"message": f"🚀 {config.APP_TITLE} is running", "version": config.APP_VERSION}

# ---------- KB: upload file ----------
@app.post("/kb/upload", response_model=KBIngestResponse)
async def kb_upload(file: UploadFile = File(...), title: Optional[str] = None, user_id: str = "demo"):
    text = utils.parse_file(file)
    title = title or file.filename
    if not text.strip():
        raise HTTPException(400, "No text extracted.")
    chunks = utils.chunk_text(text)
    vectors = ai.embed_batch(chunks)
    doc_id = str(uuid.uuid4())
    ids = [f"{doc_id}:{i}" for i in range(len(chunks))]
    metas = [utils.make_meta(doc_id, title, user_id, i) for i in range(len(chunks))]
    kb_store.add(ids=ids, documents=chunks, metadatas=metas, embeddings=vectors)
    return KBIngestResponse(document_id=doc_id, chunks=len(chunks), title=title)

# ---------- KB: link URL ----------
@app.post("/kb/link", response_model=KBIngestResponse)
async def kb_link(url: str = Form(...), user_id: str = "demo"):
    try:
        text = utils.fetch_url(url)
    except Exception as e:
        raise HTTPException(400, f"Fetch failed: {e}")
    title = text.split("\n", 1)[0][:120]
    chunks = utils.chunk_text(text)
    vectors = ai.embed_batch(chunks)
    doc_id = str(uuid.uuid4())
    ids = [f"{doc_id}:{i}" for i in range(len(chunks))]
    metas = [utils.make_meta(doc_id, title, user_id, i, url=url) for i in range(len(chunks))]
    kb_store.add(ids=ids, documents=chunks, metadatas=metas, embeddings=vectors)
    return KBIngestResponse(document_id=doc_id, chunks=len(chunks), title=title, source_url=url)

# ---------- KB: query ----------
@app.get("/kb/query", response_model=KBAnswer)
def kb_query(q: str, user_id: str = "demo", k: int = 6):
    qvec = ai.embed_batch([q])[0]
    res = kb_store.query(query_embedding=qvec, n_results=max(8, k+2), where={"user_id": user_id})
    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    ids = (res.get("ids") or [[]])[0]

    seen, picks = set(), []
    for doc, meta, _id in zip(docs, metas, ids):
        if not meta: continue
        key = (meta.get("doc_id"), int(meta.get("order", 0)) // 2)
        if key in seen: continue
        seen.add(key); picks.append((doc, meta, _id))
        if len(picks) >= k: break

    if not picks:
        return KBAnswer(answer="I don't have enough information to answer that yet.", citations=[], used_chunks=0)

    context_blocks, cits = [], []
    for i, (doc, meta, _id) in enumerate(picks, 1):
        context_blocks.append(f"[{i}] Title: {meta.get('title')}\nURL: {meta.get('url')}\nExcerpt:\n{doc}\n")
        cits.append({"doc_id": meta.get("doc_id"), "title": meta.get("title"),
                     "url": meta.get("url"), "chunk_preview": (doc or "")[:200]})

    system = ("You are a precise research assistant. Answer using ONLY the provided context. "
              "If missing, say you don't have enough info. Cite sources inline like [1], [2]. "
              "Provide a concise, actionable answer.")
    prompt = system + "\n\nCONTEXT:\n" + "\n\n".join(context_blocks) + f"\n\nQUESTION: {q}\n\nANSWER WITH CITATIONS:"

    answer = ai.generate_text(prompt, temperature=0.2, max_output_tokens=400)
    return KBAnswer(answer=answer.strip(), citations=cits, used_chunks=len(picks))

# ---------- KB: flashcards ----------
@app.get("/kb/flashcards", response_model=FlashcardSet)
def kb_flashcards(doc_id: str, user_id: str = "demo", n: int = 10):
    res = kb_store.get(where={"doc_id": doc_id, "user_id": user_id})
    docs = res.get("documents") or []
    metas = res.get("metadatas") or []
    if not docs:
        raise HTTPException(404, "Doc not found for this user.")
    text = "\n\n".join(docs)
    title = (metas[0].get("title") if metas and isinstance(metas[0], dict) else "Untitled")

    prompt = (
        f"Create {n} compact flashcards from the content below. "
        f"Focus on key definitions, decisions, and cause-effect.\n"
        f'Return JSON: {{ "cards": [{{"q":"...","a":"..."}}] }}\n'
        f"CONTENT:\n{text[:12000]}\n"
    )
    try:
        data = ai.generate_json(prompt, temperature=0.3, max_output_tokens=800)
        return FlashcardSet(source_title=title, cards=data["cards"])
    except Exception:
        return FlashcardSet(source_title=title, cards=[{"q": "What is the main idea?", "a": text[:200]}])

# ---------- Gmail: prioritized recent ----------
@app.get("/gmail/recent", response_model=List[InboxItem])
def gmail_recent(max_results: int = 5):
    try:
        msgs = gmail_service.list_recent_messages(max_results=max_results)
        items: List[InboxItem] = []
        for m in msgs:
            full = gmail_service.get_message(m["id"])
            headers = full.get("payload", {}).get("headers", [])
            subject = utils.header_lookup(headers, "Subject")
            sender = utils.header_lookup(headers, "From")
            snippet = full.get("snippet", "") or ""
            internal_ts = int(full.get("internalDate", "0"))

            ai_sum = ai.gemini_summarize(snippet, subject, sender)
            lower = snippet.lower()
            blocked = any(k in lower for k in ["waiting on you", "blocked", "need by", "asap", "urgent", "eod", "by eod"])

            score = priority.compute_priority(ai_sum, internal_ms=internal_ts, sender_role=None, blocked_flag=blocked)

            items.append(InboxItem(
                source="gmail",
                id=full.get("id"),
                thread_id=full.get("threadId"),
                subject=subject,
                from_=sender,
                snippet=snippet,
                internal_ts=internal_ts,
                url=f"https://mail.google.com/mail/u/0/#inbox/{full.get('id')}",
                ai=ai_sum,
                priority_score=score
            ))
        items.sort(key=lambda x: x.priority_score or 0, reverse=True)
        return items
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch Gmail: {e}")

# ---------- Gmail: single email summary ----------
@app.get("/summarize_email")
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

@app.post("/slack/send", response_model=SlackSendResult)
def slack_send(req: SlackSendRequest):
    # 1) Normalize into {targets:[{type,name}], text}
    if req.q:
        parsed = parse_slack_send(req.q)
        targets = parsed.get("targets", [])
        text = parsed.get("text", "").strip()
    else:
        targets, text = [], (req.text or "").strip()
        if req.to:
            t = req.to.strip()
            if t.startswith("#"):
                targets.append({"type":"channel","name":t})
            else:
                targets.append({"type":"user","name":t})
        if req.channel_id:
            targets.append({"type":"channel_id","name":req.channel_id})
    if not targets or not text:
        raise HTTPException(400, "Need a recipient and message text (provide 'q' or 'to' + 'text').")

    # 2) Resolve & send
    deliveries = []
    for tgt in targets:
        ttype = tgt.get("type"); name = tgt.get("name")
        try:
            if ttype == "channel_id":
                res = slack_service.send_message_channel(name, text, thread_ts=req.thread_ts)
            elif ttype == "channel":
                cid = slack_service.get_channel_id_by_name(name)
                if not cid: raise HTTPException(404, f"Channel {name} not found or bot not invited.")
                res = slack_service.send_message_channel(cid, text, thread_ts=req.thread_ts)
            elif ttype == "user":
                uid = slack_service.find_user_id_by_name(name)
                if not uid: raise HTTPException(404, f"User {name} not found.")
                res = slack_service.send_message_user(uid, text)
            else:
                raise HTTPException(400, f"Unsupported target type: {ttype}")
            # add a permalink if possible
            link = slack_service.permalink(res["channel"], res["ts"]) if "ts" in res else None
            deliveries.append({"target": tgt, "ok": True, "channel": res.get("channel"), "ts": res.get("ts"), "permalink": link})
        except HTTPException as he:
            raise he
        except Exception as e:
            deliveries.append({"target": tgt, "ok": False, "error": str(e)})
    return SlackSendResult(deliveries=deliveries)

# ---------- PM: unified prioritized tasks ----------
@app.get("/pm/tasks", response_model=TaskListResponse)
def pm_tasks(limit_per_provider: int = 30, assignee_me: bool = True):
    """
    Returns a unified, prioritized list of tasks across connected project tools.
    Currently supports Jira (add Trello/Asana providers similarly).
    """
    return list_tasks_all(limit_per_provider=limit_per_provider, assignee_me=assignee_me)

# ---------- PM: Jira actions (example) ----------
@app.post("/pm/jira/{issue_id}/comment")
def pm_jira_comment(issue_id: str, text: str):
    prov = JiraProvider()
    return prov.comment_task(issue_id, text)

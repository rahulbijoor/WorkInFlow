from typing import Optional, List, Dict, Any
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
import uuid
import json

from .models import KBIngestResponse, KBAnswer, FlashcardSet
from .utils import parse_file, chunk_text, make_meta, fetch_url
from .gemini_service import embed_batch
from .kb_store import kb
import google.generativeai as genai
from .config import GEN_MODEL

router = APIRouter()

@router.post("/kb/upload", response_model=KBIngestResponse)
async def kb_upload(file: UploadFile = File(...), title: Optional[str] = None, user_id: str = "demo"):
    text = parse_file(file)
    title = title or file.filename
    if not text.strip():
        raise HTTPException(400, "No text extracted.")
    chunks = chunk_text(text)
    vectors = embed_batch(chunks)
    doc_id = str(uuid.uuid4())
    ids = [f"{doc_id}:{i}" for i in range(len(chunks))]
    metas = [make_meta(doc_id, title, user_id, i) for i in range(len(chunks))]
    kb.add(ids=ids, documents=chunks, metadatas=metas, embeddings=vectors)
    return KBIngestResponse(document_id=doc_id, chunks=len(chunks), title=title)

@router.post("/kb/link", response_model=KBIngestResponse)
async def kb_link(url: str = Form(...), user_id: str = "demo"):
    try:
        text = fetch_url(url)
    except Exception as e:
        raise HTTPException(400, f"Fetch failed: {e}")
    title = text.split("\n", 1)[0][:120]
    chunks = chunk_text(text)
    vectors = embed_batch(chunks)
    doc_id = str(uuid.uuid4())
    ids = [f"{doc_id}:{i}" for i in range(len(chunks))]
    metas = [make_meta(doc_id, title, user_id, i, url=url) for i in range(len(chunks))]
    kb.add(ids=ids, documents=chunks, metadatas=metas, embeddings=vectors)
    return KBIngestResponse(document_id=doc_id, chunks=len(chunks), title=title, source_url=url)

@router.get("/kb/query", response_model=KBAnswer)
def kb_query(q: str, user_id: str = "demo", k: int = 6):
    qvec = embed_batch([q])[0]
    res = kb.query(query_embeddings=[qvec], n_results=max(8, k+2), where={"user_id": user_id})
    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    ids = (res.get("ids") or [[]])[0]

    seen = set(); picks = []
    for doc, meta, _id in zip(docs, metas, ids):
        if not meta:
            continue
        key = (meta.get("doc_id"), int(meta.get("order", 0)) // 2)
        if key in seen:
            continue
        seen.add(key)
        picks.append((doc, meta, _id))
        if len(picks) >= k:
            break

    if not picks:
        return KBAnswer(answer="I don't have enough information to answer that yet.", citations=[], used_chunks=0)

    context_blocks = []
    cits = []
    for i, (doc, meta, _id) in enumerate(picks, 1):
        context_blocks.append(f"[{i}] Title: {meta.get('title')}\nURL: {meta.get('url')}\nExcerpt:\n{doc}\n")
        cits.append({"doc_id": meta.get("doc_id"), "title": meta.get("title"), "url": meta.get("url"), "chunk_preview": (doc or "")[:200]})

    system = """You are a precise research assistant. Answer using ONLY the provided context. If missing, say you don't have enough info.
Cite sources inline like [1], [2]. Provide a concise, actionable answer."""
    prompt = system + "\n\nCONTEXT:\n" + "\n\n".join(context_blocks) + f"\n\nQUESTION: {q}\n\nANSWER WITH CITATIONS:"

    model = genai.GenerativeModel(GEN_MODEL)
    resp = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(temperature=0.2, max_output_tokens=400)
    )
    if not resp or not getattr(resp, "text", "").strip():
        raise HTTPException(502, "LLM returned empty.")
    return KBAnswer(answer=resp.text.strip(), citations=cits, used_chunks=len(picks))

@router.get("/kb/flashcards", response_model=FlashcardSet)
def kb_flashcards(doc_id: str, user_id: str = "demo", n: int = 10):
    res = kb.get(where={"doc_id": doc_id, "user_id": user_id})
    docs = res.get("documents") or []
    metas = res.get("metadatas") or []
    if not docs:
        raise HTTPException(404, "Doc not found for this user.")
    text = "\n\n".join(docs)
    title = (metas[0].get("title") if metas and isinstance(metas[0], dict) else "Untitled")

    prompt = f"""Create {n} compact flashcards from the content below. Focus on key definitions, decisions, and cause-effect.
Return JSON: {{ "cards": [{{"q":"...","a":"..."}}] }}
CONTENT:
{text[:12000]}
"""
    model = genai.GenerativeModel(GEN_MODEL)
    r = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(temperature=0.3, max_output_tokens=800, response_mime_type="application/json")
    )
    try:
        data = json.loads(r.text)
        return FlashcardSet(source_title=title, cards=data["cards"])
    except Exception:
        return FlashcardSet(source_title=title, cards=[{"q": "What is the main idea?", "a": text[:200]}])

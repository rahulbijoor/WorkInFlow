import os, re, uuid, time, requests
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from pypdf import PdfReader
from fastapi import UploadFile

def now_ms() -> int:
    return int(time.time() * 1000)

def chunk_text(text: str, size: int = 1200, overlap: int = 200) -> List[str]:
    text = re.sub(r"\s+\n", "\n", text).strip()
    chunks, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk)
        if end == len(text):
            break
        start = end - overlap
    return chunks

def parse_file(file: UploadFile) -> str:
    data = file.file.read()
    if file.filename.lower().endswith(".pdf"):
        tmp = f"/tmp/{uuid.uuid4()}.pdf"
        with open(tmp, "wb") as f:
            f.write(data)
        reader = PdfReader(tmp)
        return "\n\n".join((p.extract_text() or "") for p in reader.pages)
    else:
        return data.decode(errors="ignore")

def fetch_url(url: str) -> str:
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "noscript"]):
        tag.decompose()
    title = (soup.title.string.strip() if soup.title and soup.title.string else url)[:200]
    body = " ".join(soup.get_text(separator=" ").split())
    return f"{title}\n\n{body}"

def make_meta(doc_id: str, title: str, user_id: str, order: int, url: Optional[str] = None) -> dict:
    meta = {
        "doc_id": doc_id,
        "title": title,
        "user_id": user_id,
        "created_at": now_ms(),
        "order": int(order),
    }
    if url is not None:
        meta["url"] = url
    return meta

def header_lookup(headers: List[Dict[str, str]], name: str) -> Optional[str]:
    for h in headers or []:
        if h.get("name") == name:
            return h.get("value")
    return None

from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class AISummary(BaseModel):
    summary_160: str
    importance: str
    urgency: str
    actionable: bool
    next_steps: List[str]
    suggested_due_iso: Optional[str] = None
    confidence: float

class InboxItem(BaseModel):
    source: str
    id: str
    thread_id: Optional[str] = None
    subject: Optional[str] = None
    from_: Optional[str] = None
    snippet: str
    internal_ts: int
    url: Optional[str] = None
    ai: Optional[AISummary] = None
    priority_score: Optional[float] = None

class KBIngestResponse(BaseModel):
    document_id: str
    chunks: int
    title: str
    source_url: Optional[str] = None

class KBAnswer(BaseModel):
    answer: str
    citations: List[Dict[str, Any]]
    used_chunks: int

class FlashcardSet(BaseModel):
    source_title: str
    cards: List[Dict[str, str]]

class SlackSendRequest(BaseModel):
    # Option 1: natural language, e.g., "tell tom I'm working on it"
    q: Optional[str] = None
    # Option 2: structured
    to: Optional[str] = None          # "@tom" or "#general"
    text: Optional[str] = None
    thread_ts: Optional[str] = None   # reply in a thread (optional)
    channel_id: Optional[str] = None  # if you already have it

class SlackSendResult(BaseModel):
    deliveries: list[dict]

class Task(BaseModel):
    provider: str            # "jira" | "trello" | "asana" ...
    id: str                  # provider's internal id
    key: Optional[str] = None  # human key like JIRA issue key (e.g., ABC-123)
    title: str
    description: Optional[str] = None
    status: Optional[str] = None       # normalized: todo | in_progress | done | blocked | other
    priority: Optional[str] = None     # provider's priority label (e.g., Highest/High/Medium/Low)
    due_iso: Optional[str] = None
    url: Optional[str] = None
    project: Optional[str] = None

    # AI + scoring (reusing your AISummary)
    ai: Optional[AISummary] = None
    priority_score: Optional[float] = None

class TaskListResponse(BaseModel):
    tasks: List[Task]
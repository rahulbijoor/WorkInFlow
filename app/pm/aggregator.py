# app/pm/aggregator.py
from typing import List
from app.models import Task, TaskListResponse
from app.pm.jira_provider import JiraProvider
from app import config
from app import ai, priority, utils
from app.models import AISummary

def _summarize_task(task: Task) -> AISummary:
    """Use your Gemini JSON summary schema to classify importance/urgency from task context."""
    content = f"""
Title: {task.title}
Priority: {task.priority or "Unknown"}
Status: {task.status or "Unknown"}
Due: {task.due_iso or "None"}
Project: {task.project or "Unknown"}
Description:
{(task.description or "")[:3000]}
"""
    # Reuse your existing strict JSON summarizer prompt
    return ai.gemini_summarize(message_text=content, subject=f"[{task.provider}] {task.title}", sender="PM System")

def _score(task: Task, ai_sum: AISummary) -> float:
    # Use due date to shape deadline proximity; we pass internal_ms as "now" if no provider timestamp.
    internal_ms = utils.now_ms()
    return priority.compute_priority(ai_sum, internal_ms=internal_ms, sender_role="pm", blocked_flag=("blocked" in (task.status or "")))

def active_providers():
    provs = []
    if config.JIRA_BASE_URL and config.JIRA_EMAIL and config.JIRA_API_TOKEN:
        try:
            provs.append(JiraProvider())
        except Exception:
            pass
    # Add more providers here in the future (TrelloProvider, AsanaProvider, etc.)
    return provs

def list_tasks_all(limit_per_provider: int = 30, assignee_me: bool = True) -> TaskListResponse:
    tasks: List[Task] = []
    for p in active_providers():
        try:
            tasks.extend(p.list_tasks(assignee_me=assignee_me, limit=limit_per_provider))
        except Exception:
            continue

    # Enrich each task with AI summary + priority score
    enriched: List[Task] = []
    for t in tasks:
        try:
            ai_sum = _summarize_task(t)
            t.ai = ai_sum
            t.priority_score = _score(t, ai_sum)
        except Exception:
            # still include the task even if AI fails
            t.priority_score = 0.0
        enriched.append(t)

    enriched.sort(key=lambda x: x.priority_score or 0, reverse=True)
    return TaskListResponse(tasks=enriched)

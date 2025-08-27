# app/pm/base.py
from typing import List, Dict, Any, Optional
from app.models import Task

class PMProvider:
    name: str = "base"

    def list_tasks(self, assignee_me: bool = True, limit: int = 50) -> List[Task]:
        raise NotImplementedError

    def get_task(self, task_id: str) -> Task:
        raise NotImplementedError

    def comment_task(self, task_id: str, text: str) -> Dict[str, Any]:
        raise NotImplementedError

    def update_task_status(self, task_id: str, new_status: str) -> Dict[str, Any]:
        """new_status is provider-specific (e.g., a Jira transition)."""
        raise NotImplementedError

    # Optional helper to map provider fields → normalized status
    @staticmethod
    def normalize_status(raw: str) -> str:
        r = (raw or "").lower()
        if r in {"to do", "todo", "backlog"}: return "todo"
        if r in {"in progress", "doing"}: return "in_progress"
        if r in {"done", "closed", "resolved"}: return "done"
        if "block" in r: return "blocked"
        return "other"

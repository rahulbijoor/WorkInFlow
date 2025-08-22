# app/pm/jira_provider.py
import base64, requests
from typing import List, Dict, Any, Optional
from app.pm.base import PMProvider
from app import config
from app.models import Task

class JiraProvider(PMProvider):
    name = "jira"

    def __init__(self):
        if not (config.JIRA_BASE_URL and config.JIRA_EMAIL and config.JIRA_API_TOKEN):
            raise RuntimeError("Jira env vars missing. Set JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN.")
        self.base = config.JIRA_BASE_URL.rstrip("/")
        tok = f"{config.JIRA_EMAIL}:{config.JIRA_API_TOKEN}".encode()
        self._auth_header = {
            "Authorization": "Basic " + base64.b64encode(tok).decode(),
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None):
        url = f"{self.base}{path}"
        r = requests.get(url, headers=self._auth_header, params=params, timeout=20)
        r.raise_for_status()
        return r.json()

    def _post(self, path: str, payload: Dict[str, Any]):
        url = f"{self.base}{path}"
        r = requests.post(url, headers=self._auth_header, json=payload, timeout=20)
        r.raise_for_status()
        return r.json()

    def list_tasks(self, assignee_me: bool = True, limit: int = 50) -> List[Task]:
        jql = []
        if assignee_me:
            jql.append("assignee = currentUser()")
        jql.append('statusCategory != Done')
        jql_stmt = " AND ".join(jql) + " ORDER BY priority DESC, updated DESC"

        params = {
            "jql": jql_stmt,
            "maxResults": limit,
            "fields": "summary,description,priority,duedate,status,project"
        }
        data = self._get("/rest/api/3/search", params=params)
        issues = data.get("issues", [])
        out: List[Task] = []
        for it in issues:
            key = it.get("key")
            iid = it.get("id")
            f = it.get("fields", {})
            title = f.get("summary") or key
            desc = (f.get("description") or "")  # Jira Cloud returns rich text in v3; often stringified
            priority = (f.get("priority") or {}).get("name")
            status = (f.get("status") or {}).get("name")
            due = f.get("duedate")  # ISO date
            project = (f.get("project") or {}).get("name")
            url = f"{self.base}/browse/{key}"

            out.append(Task(
                provider=self.name,
                id=iid,
                key=key,
                title=title,
                description=desc if isinstance(desc, str) else str(desc),
                status=self.normalize_status(status),
                priority=priority,
                due_iso=due,
                url=url,
                project=project
            ))
        return out

    def get_task(self, task_id: str) -> Task:
        data = self._get(f"/rest/api/3/issue/{task_id}", params={"fields":"summary,description,priority,duedate,status,project"})
        key = data.get("key"); iid = data.get("id")
        f = data.get("fields", {})
        return Task(
            provider=self.name,
            id=iid,
            key=key,
            title=f.get("summary") or key,
            description=(f.get("description") or ""),
            status=self.normalize_status((f.get("status") or {}).get("name")),
            priority=(f.get("priority") or {}).get("name"),
            due_iso=f.get("duedate"),
            url=f"{self.base}/browse/{key}",
            project=(f.get("project") or {}).get("name")
        )

    def comment_task(self, task_id: str, text: str) -> Dict[str, Any]:
        return self._post(f"/rest/api/3/issue/{task_id}/comment", {"body": text})

    # NOTE: Jira transitions require the transition ID. For demo simplicity, we leave this unimplemented.
    def update_task_status(self, task_id: str, new_status: str) -> Dict[str, Any]:
        raise NotImplementedError("Map your desired status → Jira transition id, then POST /transitions")
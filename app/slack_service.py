import os, re
from typing import List, Dict, Any, Optional
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
if not SLACK_BOT_TOKEN:
    raise RuntimeError("Set SLACK_BOT_TOKEN to enable Slack integration.")
client = WebClient(token=SLACK_BOT_TOKEN)

# ---------- lookups ----------
def list_channels(types: str = "public_channel,private_channel") -> List[Dict[str, Any]]:
    chans, cursor = [], None
    while True:
        resp = client.conversations_list(types=types, cursor=cursor, limit=200)
        chans.extend(resp.get("channels", []))
        cursor = resp.get("response_metadata", {}).get("next_cursor")
        if not cursor: break
    return chans

def get_channel_id_by_name(name: str) -> Optional[str]:
    name = name.lstrip("#").lower()
    for c in list_channels():
        if (c.get("name") or c.get("name_normalized","")).lower() == name:
            return c["id"]
    return None

def users_list() -> List[Dict[str, Any]]:
    users, cursor = [], None
    while True:
        resp = client.users_list(cursor=cursor, limit=200)
        users.extend(resp.get("members", []))
        cursor = resp.get("response_metadata", {}).get("next_cursor")
        if not cursor: break
    return users

def find_user_id_by_name(name: str) -> Optional[str]:
    """
    Resolve 'tom' or '@tom' to a user ID by matching display/real name (case-insensitive).
    If multiple, returns the first match.
    """
    name = name.lstrip("@").strip().lower()
    for u in users_list():
        if u.get("deleted") or u.get("is_bot"): continue
        prof = u.get("profile", {})
        cand = [
            (prof.get("display_name_normalized") or "").lower(),
            (prof.get("display_name") or "").lower(),
            (prof.get("real_name_normalized") or "").lower(),
            (prof.get("real_name") or "").lower(),
            (u.get("name") or "").lower(),
        ]
        if name in cand:
            return u["id"]
    # fuzzy contains
    for u in users_list():
        if u.get("deleted") or u.get("is_bot"): continue
        prof = u.get("profile", {})
        hay = " ".join([
            prof.get("display_name",""), prof.get("real_name",""),
            prof.get("display_name_normalized",""), prof.get("real_name_normalized",""),
            u.get("name","")
        ]).lower()
        if name in hay:
            return u["id"]
    return None

# ---------- sending ----------
def open_dm(user_id: str) -> Optional[str]:
    """Open an IM channel with a user and return channel ID."""
    resp = client.conversations_open(users=[user_id])
    return resp.get("channel", {}).get("id")

def send_message_channel(channel_id: str, text: str, thread_ts: Optional[str] = None) -> Dict[str, Any]:
    resp = client.chat_postMessage(channel=channel_id, text=text, thread_ts=thread_ts)
    return {"ok": True, "channel": resp["channel"], "ts": resp["ts"]}

def send_message_user(user_id: str, text: str) -> Dict[str, Any]:
    cid = open_dm(user_id)
    if not cid:
        raise RuntimeError("Failed to open DM.")
    resp = client.chat_postMessage(channel=cid, text=text)
    return {"ok": True, "channel": resp["channel"], "ts": resp["ts"]}

def permalink(channel: str, ts: str) -> Optional[str]:
    try:
        return client.chat_getPermalink(channel=channel, message_ts=ts).get("permalink")
    except SlackApiError:
        return None

"""Turn meeting notes and emails into a summary and explicit action items.

The default path is a deterministic rules engine and does not call a network.
If FOTOOLKIT_LLM_API_KEY is set, the same function will try that API and fall
back to the rules engine if the call fails. Either way the result is a draft.
Nothing here is allowed to create a task until a person approves it.
"""

import hashlib
import json
import os
import re
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

ACTION_LINE = re.compile(
    r"^ACTION:\s*(?P<owner>.+?)\s+[—–\-]\s+(?P<text>.+?)\s+[—–\-]\s+due\s+(?P<due>\d{4}-\d{2}-\d{2})\s*$",
    re.IGNORECASE,
)
WILL_LINE = re.compile(
    r"^(?P<owner>[A-Z][a-z]+(?:\s[A-Z][a-z]+)*)\s+will\s+(?P<text>.+?)\s+by\s+(?P<due>\d{4}-\d{2}-\d{2})\.?$"
)
DECISION_LINE = re.compile(r"^Decision:\s*(?P<text>.+)$", re.IGNORECASE)
AGREED_LINE = re.compile(r"^We agreed\s+(?P<text>.+?)\.?$", re.IGNORECASE)
SUBJECT_LINE = re.compile(r"^Subject:\s*(?P<title>.+)$", re.IGNORECASE)


def normalize_text(text: str) -> str:
    lines = [line.strip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    return "\n".join(lines).strip()


def item_id(source: str, text: str) -> str:
    digest = hashlib.sha256(f"{source}\n{normalize_text(text)}".encode("utf-8")).hexdigest()
    return digest[:12]


def rules_summarize(text: str, source: str) -> dict:
    normalized = normalize_text(text)
    lines = normalized.split("\n")
    subject = next((SUBJECT_LINE.match(line) for line in lines if SUBJECT_LINE.match(line)), None)
    title = subject.group("title").strip() if subject else next(line for line in lines if line)
    decisions = []
    actions = []
    seen = set()
    for line in lines:
        decision = DECISION_LINE.match(line) or AGREED_LINE.match(line)
        if decision:
            decisions.append(decision.group("text").strip().rstrip("."))
            continue
        action = ACTION_LINE.match(line) or WILL_LINE.match(line)
        if not action:
            continue
        key = (action.group("owner").strip(), action.group("due"))
        if key in seen:
            continue
        seen.add(key)
        actions.append(
            {
                "owner": action.group("owner").strip(),
                "text": action.group("text").strip().rstrip("."),
                "due_date": action.group("due"),
            }
        )
    decision_sentence = " ".join(f"{item}." for item in decisions) if decisions else "No explicit decision line was found."
    summary = (
        f"{title}: {len(decisions)} explicit decision(s) and {len(actions)} explicit action(s). "
        f"{decision_sentence} "
        "Produced offline by the rules engine for human review. Not approved."
    )
    return {
        "id": item_id(source, normalized),
        "source": source,
        "title": title,
        "method": "rules",
        "fallback_reason": "",
        "summary": summary,
        "decisions": decisions,
        "action_items": actions,
    }


def _strip_fence(content: str) -> str:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def llm_summarize(text: str, source: str, api_key: str) -> dict:
    """Optional API path. The key is read from the environment and is not stored."""
    base = os.environ.get("FOTOOLKIT_LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.environ.get("FOTOOLKIT_LLM_MODEL", "gpt-4o-mini")
    payload = {
        "model": model,
        "temperature": 0,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Extract a short summary, decision sentences, and explicit action items. "
                    "Return JSON with keys summary, decisions, action_items. "
                    "Each action item has owner, text, and due_date (YYYY-MM-DD or empty). "
                    "Do not invent owners or dates. This draft will be reviewed by a person."
                ),
            },
            {"role": "user", "content": text},
        ],
    }
    request = Request(
        f"{base}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            body = json.loads(response.read().decode("utf-8"))
    except URLError:
        raise
    content = body["choices"][0]["message"]["content"]
    parsed = json.loads(_strip_fence(content))
    actions = []
    for action in parsed.get("action_items", []):
        actions.append(
            {
                "owner": str(action.get("owner", "")).strip() or "Unassigned",
                "text": str(action.get("text", "")).strip(),
                "due_date": str(action.get("due_date", "")).strip(),
            }
        )
    decisions = [str(item).strip() for item in parsed.get("decisions", []) if str(item).strip()]
    normalized = normalize_text(text)
    lines = normalized.split("\n")
    subject = next((SUBJECT_LINE.match(line) for line in lines if SUBJECT_LINE.match(line)), None)
    title = subject.group("title").strip() if subject else next(line for line in lines if line)
    summary = str(parsed.get("summary", "")).strip()
    if not summary.endswith("Not approved."):
        summary = summary.rstrip(".") + ". Draft from the language-model path. Not approved."
    return {
        "id": item_id(source, normalized),
        "source": source,
        "title": title,
        "method": "llm",
        "fallback_reason": "",
        "summary": summary,
        "decisions": decisions,
        "action_items": actions,
    }


def summarize_text(text: str, source: str, api_key: str | None = None) -> dict:
    if api_key is None:
        api_key = os.environ.get("FOTOOLKIT_LLM_API_KEY", "").strip() or None
    if not api_key:
        return rules_summarize(text, source)
    try:
        return llm_summarize(text, source, api_key)
    except Exception as exc:
        draft = rules_summarize(text, source)
        draft["method"] = "rules_fallback"
        draft["fallback_reason"] = type(exc).__name__
        return draft


def build_queue(notes_dir: Path, api_key: str | None = None) -> list[dict]:
    if not notes_dir.exists():
        raise FileNotFoundError(notes_dir)
    queue = []
    for path in sorted(notes_dir.glob("*.txt")):
        queue.append(summarize_text(path.read_text(encoding="utf-8"), path.name, api_key=api_key))
    return queue

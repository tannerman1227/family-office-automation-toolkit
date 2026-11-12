"""Human review gate.

The summarizer writes drafts. A person marks each draft approved or rejected.
Only approved action items are eligible for the task list. Re-running the
toolkit keeps decisions whose ids still match a current draft.
"""

import json
from pathlib import Path


def load_decisions(path: Path) -> dict:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8") or "{}")
    if not isinstance(data, dict):
        raise ValueError(f"Review decisions file must be an object: {path}")
    return data


def save_decisions(path: Path, decisions: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(decisions, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def apply_decision(decisions: dict, item_id: str, status: str, note: str, decided_at: str) -> dict:
    if status not in {"approved", "rejected"}:
        raise ValueError("status must be approved or rejected")
    updated = dict(decisions)
    updated[item_id] = {"status": status, "note": note.strip(), "decided_at": decided_at}
    return updated


def prune_decisions(decisions: dict, queue: list[dict]) -> dict:
    valid = {item["id"] for item in queue}
    return {key: value for key, value in decisions.items() if key in valid}


def effective_status(item: dict, decisions: dict) -> str:
    record = decisions.get(item["id"])
    if not record:
        return "pending"
    return record.get("status", "pending")


def merge_queue(queue: list[dict], decisions: dict) -> list[dict]:
    merged = []
    for item in queue:
        copy = dict(item)
        record = decisions.get(item["id"], {})
        copy["review_status"] = effective_status(item, decisions)
        copy["review_note"] = record.get("note", "")
        copy["decided_at"] = record.get("decided_at", "")
        merged.append(copy)
    return merged


def approved_tasks(queue: list[dict], decisions: dict) -> list[dict]:
    tasks = []
    for item in merge_queue(queue, decisions):
        if item["review_status"] != "approved":
            continue
        for index, action in enumerate(item["action_items"], start=1):
            tasks.append(
                {
                    "task_id": f"AI-{item['id']}-{index}",
                    "title": action["text"],
                    "owner": action["owner"],
                    "due_date": action["due_date"],
                    "status": "open",
                    "source": "AI summary — human approved",
                    "related": item["source"],
                    "review_note": item["review_note"],
                }
            )
    return tasks

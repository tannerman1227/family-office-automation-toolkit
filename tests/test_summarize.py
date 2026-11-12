from fotoolkit.config import DATA_DIR
from fotoolkit.review import apply_decision, approved_tasks, effective_status
from fotoolkit.summarize import build_queue, summarize_text


def test_rules_engine_extracts_explicit_actions_only():
    queue = build_queue(DATA_DIR / "notes", api_key="")
    assert [item["method"] for item in queue] == ["rules", "rules"]
    by_source = {item["source"]: item for item in queue}
    ic = by_source["ic_minutes_2026-11-10.txt"]
    ops = by_source["ops_email_2026-11-11.txt"]
    assert len(ic["decisions"]) == 3
    assert [action["owner"] for action in ic["action_items"]] == ["Priya Shah", "Jordan Hale", "Evan Cho"]
    assert ic["action_items"][0]["due_date"] == "2026-11-13"
    assert ops["title"] == "October close and stock"
    assert ops["decisions"] == ["the October management report should flag any SKU below its reorder point"]
    assert ops["action_items"] == [
        {
            "owner": "Luis Ortega",
            "text": "recount ABR-220 and PPE-118 and email the counts",
            "due_date": "2026-11-14",
        }
    ]
    assert "Please have the warehouse" not in " ".join(action["text"] for action in ops["action_items"])
    assert all(effective_status(item, {}) == "pending" for item in queue)
    assert approved_tasks(queue, {}) == []


def test_approval_is_required_before_a_task_exists():
    queue = build_queue(DATA_DIR / "notes", api_key="")
    item_id = queue[0]["id"]
    decided = apply_decision({}, item_id, "approved", "Checked the notice.", "2026-11-12")
    tasks = approved_tasks(queue, decided)
    assert tasks
    assert all(task["source"] == "AI summary — human approved" for task in tasks)
    assert all(task["related"] == queue[0]["source"] for task in tasks)
    rejected = apply_decision({}, queue[1]["id"], "rejected", "Duplicate of the operating list.", "2026-11-12")
    assert approved_tasks(queue, rejected) == []


def test_llm_failure_falls_back_and_stays_unapproved(monkeypatch):
    def explode(*args, **kwargs):
        raise RuntimeError("model unavailable")

    monkeypatch.setattr("fotoolkit.summarize.llm_summarize", explode)
    draft = summarize_text("Decision: Keep the draft in review.\n", "note.txt", api_key="test-key")
    assert draft["method"] == "rules_fallback"
    assert draft["fallback_reason"] == "RuntimeError"
    assert "Not approved." in draft["summary"]


def test_missing_key_never_selects_the_model(monkeypatch):
    monkeypatch.delenv("FOTOOLKIT_LLM_API_KEY", raising=False)
    called = {"hit": False}

    def explode(*args, **kwargs):
        called["hit"] = True
        raise AssertionError("should not be called")

    monkeypatch.setattr("fotoolkit.summarize.llm_summarize", explode)
    draft = summarize_text("Decision: Stay offline.\n", "note.txt", api_key=None)
    assert draft["method"] == "rules"
    assert called["hit"] is False

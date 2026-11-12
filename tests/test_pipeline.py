import json
import sqlite3

from fotoolkit.cli import main
from fotoolkit.config import DATA_DIR
from fotoolkit.pipeline import build_model, dashboard_payload, lede, write_outputs
from fotoolkit.review import apply_decision, save_decisions
from fotoolkit.star_schema import build_star, write_star


LEDE = (
    "As of 12 November 2026, 1 capital call is overdue, "
    "October revenue is $18,000 under budget, and 2 screening memos are marked Advance. "
    "2 AI summaries are waiting on a person."
)


def test_lede_matches_the_sample():
    model = build_model(DATA_DIR.parents[1])
    assert lede(model, 2) == LEDE
    payload = dashboard_payload(model, {})
    assert payload["lede"] == LEDE
    assert payload["data_label"] == "SYNTHETIC"
    assert payload["review"]["pending"] == 2
    assert payload["review"]["approved"] == 0


def test_run_all_writes_artifacts_and_keeps_a_decision(tmp_path, monkeypatch):
    monkeypatch.delenv("FOTOOLKIT_LLM_API_KEY", raising=False)
    model = build_model()
    decisions = tmp_path / "review" / "decisions.json"
    first = model.queue[0]["id"]
    save_decisions(decisions, apply_decision({}, first, "approved", "Kept across the rerun.", "2026-11-12"))
    payload = write_outputs(model, tmp_path, decisions_path=decisions)
    assert payload["review"]["approved"] == 1
    assert payload["review"]["pending"] == 1
    assert (tmp_path / "capital" / "capital_tracker.xlsx").exists()
    assert (tmp_path / "management" / "management_report.xlsx").exists()
    assert (tmp_path / "management" / "monthly_report.html").exists()
    assert (tmp_path / "screening" / "memos" / "CAD-01.html").exists()
    assert (tmp_path / "harborline.sqlite").exists()
    assert (tmp_path / "powerbi" / "fact_capital_call.csv").exists()
    stored = json.loads((tmp_path / "review" / "decisions.json").read_text())
    assert stored[first]["status"] == "approved"
    queue = json.loads((tmp_path / "review" / "queue.json").read_text())
    assert {item["id"]: item["review_status"] for item in queue}[first] == "approved"

    code = main(["--output", str(tmp_path / "cli"), "run-all"])
    assert code == 0
    cli_payload = json.loads((tmp_path / "cli" / "dashboard.json").read_text())
    assert cli_payload["lede"] == LEDE


def test_star_schema_overdue_call_and_sqlite(tmp_path):
    model = build_model()
    tables = build_star(model, {})
    assert tables["fact_capital_call"].loc[tables["fact_capital_call"]["status"] == "Overdue", "amount"].sum() == 400_000
    orphan_funds = set(tables["fact_capital_call"]["fund_key"]) - set(tables["dim_fund"]["fund_key"])
    assert orphan_funds == set()
    write_star(tables, tmp_path / "powerbi", tmp_path / "harborline.sqlite")
    connection = sqlite3.connect(tmp_path / "harborline.sqlite")
    try:
        amount = connection.execute(
            "SELECT SUM(amount) FROM fact_capital_call WHERE status = 'Overdue'"
        ).fetchone()[0]
    finally:
        connection.close()
    assert amount == 400_000

"""Build the office model once and write every artifact from it."""

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from fotoolkit.capital import CapitalModel, load_capital
from fotoolkit.config import DATA_LABEL, OFFICE_NAME, OPCO_NAME, OUTPUT_DIR, REPO_ROOT
from fotoolkit.format_util import json_number, money
from fotoolkit.html_reports import alerts_markdown, monthly_report_html, write_screening_pages
from fotoolkit.management import OperatingModel, load_operating
from fotoolkit.readers import read_table
from fotoolkit.review import load_decisions, merge_queue, prune_decisions, save_decisions
from fotoolkit.screening import ScreeningModel, load_screening
from fotoolkit.star_schema import build_star, write_star
from fotoolkit.summarize import build_queue
from fotoolkit.workbooks import write_capital_workbook, write_management_workbook, write_screening_workbook


@dataclass
class OfficeModel:
    capital: CapitalModel
    screening: ScreeningModel
    operating: OperatingModel
    queue: list
    priorities: pd.DataFrame
    tasks: pd.DataFrame
    cost_ratios: dict


def _dated_frame(rows: list[dict], date_columns: list[str]) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    for column in date_columns:
        frame[column] = pd.to_datetime(frame[column]).dt.date
    return frame


def build_model(root: Path | None = None, api_key: str | None = None) -> OfficeModel:
    root = root or REPO_ROOT
    data_dir = root / "data" / "sample"
    capital = load_capital(data_dir)
    screening = load_screening(data_dir, capital.totals["commitment"])
    operating = load_operating(data_dir)
    queue = build_queue(data_dir / "notes", api_key=api_key)
    priorities = _dated_frame(read_table(data_dir / "priorities.csv"), ["due_date"])
    priorities["rank"] = priorities["rank"].astype(int)
    tasks = _dated_frame(read_table(data_dir / "tasks.csv"), ["due_date"])
    ratios = {row["product_line"]: row["cogs_ratio"] for row in read_table(data_dir / "product_costs.csv")}
    return OfficeModel(
        capital=capital,
        screening=screening,
        operating=operating,
        queue=queue,
        priorities=priorities.sort_values("rank").reset_index(drop=True),
        tasks=tasks.sort_values("task_id").reset_index(drop=True),
        cost_ratios=ratios,
    )


def lede(model: OfficeModel, pending_reviews: int) -> str:
    calls = model.capital.totals["overdue_call_count"]
    call_text = "1 capital call is overdue" if calls == 1 else f"{calls} capital calls are overdue"
    variance = model.operating.kpis["october_revenue_variance"]
    if variance < 0:
        revenue_text = f"October revenue is {money(abs(variance))} under budget"
    elif variance > 0:
        revenue_text = f"October revenue is {money(variance)} over budget"
    else:
        revenue_text = "October revenue is in line with budget"
    advance = model.screening.counts["advance"]
    advance_text = (
        "1 screening memo is marked Advance" if advance == 1 else f"{advance} screening memos are marked Advance"
    )
    review_text = (
        "1 AI summary is waiting on a person"
        if pending_reviews == 1
        else f"{pending_reviews} AI summaries are waiting on a person"
    )
    return f"As of 12 November 2026, {call_text}, {revenue_text}, and {advance_text}. {review_text}."


def dashboard_payload(model: OfficeModel, decisions: dict) -> dict:
    queue = merge_queue(model.queue, decisions)
    pending = sum(item["review_status"] == "pending" for item in queue)
    approved = sum(item["review_status"] == "approved" for item in queue)
    rejected = sum(item["review_status"] == "rejected" for item in queue)
    capital = model.capital.totals
    kpis = model.operating.kpis
    counts = model.screening.counts
    return {
        "office": OFFICE_NAME,
        "operating_company": OPCO_NAME,
        "data_label": DATA_LABEL,
        "as_of": "2026-11-12",
        "lede": lede(model, pending),
        "capital": {key: json_number(value) if isinstance(value, float) else value for key, value in capital.items()},
        "operating": {
            key: (json_number(value) if isinstance(value, float) else value)
            for key, value in kpis.items()
            if key != "skus_below_reorder"
        },
        "skus_below_reorder": kpis["skus_below_reorder"],
        "pipeline": counts,
        "review": {"pending": pending, "approved": approved, "rejected": rejected, "drafts": len(queue)},
        "queue": queue,
    }


def _json_default(value):
    if hasattr(value, "isoformat"):
        return value.isoformat()
    raise TypeError(f"Cannot serialize {type(value)}")


def write_outputs(model: OfficeModel, output_dir: Path | None = None, decisions_path: Path | None = None) -> dict:
    output_dir = output_dir or OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    decisions_path = decisions_path or (output_dir / "review" / "decisions.json")
    decisions = prune_decisions(load_decisions(decisions_path), model.queue)
    if decisions_path.exists() or decisions:
        save_decisions(decisions_path, decisions)
    elif not decisions_path.exists():
        save_decisions(decisions_path, {})

    (output_dir / "capital").mkdir(parents=True, exist_ok=True)
    (output_dir / "management").mkdir(parents=True, exist_ok=True)
    write_capital_workbook(model.capital, output_dir / "capital" / "capital_tracker.xlsx")
    write_screening_workbook(model.screening, output_dir / "screening" / "pipeline.xlsx")
    write_management_workbook(model.operating, model.cost_ratios, output_dir / "management" / "management_report.xlsx")
    write_screening_pages(model.screening, output_dir / "screening", "12 November 2026")
    (output_dir / "management" / "monthly_report.html").write_text(
        monthly_report_html(model.operating, "12 November 2026"),
        encoding="utf-8",
    )
    (output_dir / "capital" / "alerts.md").write_text(alerts_markdown(model.capital), encoding="utf-8")

    payload = dashboard_payload(model, decisions)
    (output_dir / "dashboard.json").write_text(
        json.dumps(payload, indent=2, default=_json_default) + "\n",
        encoding="utf-8",
    )
    (output_dir / "review").mkdir(parents=True, exist_ok=True)
    (output_dir / "review" / "queue.json").write_text(
        json.dumps(payload["queue"], indent=2) + "\n",
        encoding="utf-8",
    )

    tables = build_star(model, decisions)
    write_star(tables, output_dir / "powerbi", output_dir / "harborline.sqlite")

    manifest = {
        "as_of": "2026-11-12",
        "data_label": DATA_LABEL,
        "lede": payload["lede"],
        "files": [
            "dashboard.json",
            "capital/capital_tracker.xlsx",
            "capital/alerts.md",
            "screening/pipeline.xlsx",
            "screening/index.html",
            "management/management_report.xlsx",
            "management/monthly_report.html",
            "review/queue.json",
            "review/decisions.json",
            "powerbi/",
            "harborline.sqlite",
        ],
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return payload

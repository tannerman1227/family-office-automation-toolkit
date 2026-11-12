"""Tidy tables for a Power BI model, plus a SQLite file with the same shape.

Facts carry keys. Names live on dimensions. Review items are included with
their current human decision, which is pending until someone approves them.
"""

import sqlite3
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from fotoolkit.format_util import as_date
from fotoolkit.review import merge_queue


def date_key(value) -> int | None:
    if isinstance(value, datetime):
        parsed = value.date()
    elif isinstance(value, date):
        parsed = value
    else:
        parsed = as_date(value)
    if parsed is None:
        return None
    return parsed.year * 10000 + parsed.month * 100 + parsed.day


def _collect_dates(*values) -> list[date]:
    found = set()
    for value in values:
        if isinstance(value, datetime):
            found.add(value.date())
        elif isinstance(value, date):
            found.add(value)
        else:
            parsed = as_date(value)
            if parsed is not None:
                found.add(parsed)
    return sorted(found)


def build_star(model, decisions: dict) -> dict[str, pd.DataFrame]:
    dates = [model.capital.as_of]
    for frame, columns in (
        (model.capital.commitments, []),
        (model.capital.calls, ["notice_date", "due_date"]),
        (model.capital.distributions, ["notice_date", "expected_date"]),
        (model.capital.deadlines, ["due_date", "received_date"]),
        (model.capital.irr_cashflows, ["flow_date"]),
        (model.operating.sales, ["invoice_date"]),
        (model.operating.purchasing, ["po_date"]),
        (model.operating.inventory, ["last_receipt_date"]),
    ):
        for column in columns:
            dates.extend(frame[column].tolist())
    for month in model.operating.monthly["month"]:
        year, month_number = (int(part) for part in str(month).split("-"))
        dates.append(date(year, month_number, 1))
    for frame, column in ((model.priorities, "due_date"), (model.tasks, "due_date")):
        dates.extend(frame[column].tolist())

    dim_date_rows = []
    for current in _collect_dates(*dates):
        dim_date_rows.append(
            {
                "date_key": date_key(current),
                "full_date": current.isoformat(),
                "year": current.year,
                "month": current.month,
                "month_name": current.strftime("%B"),
                "quarter": (current.month - 1) // 3 + 1,
                "year_month": current.strftime("%Y-%m"),
            }
        )
    dim_date = pd.DataFrame(dim_date_rows).drop_duplicates("date_key").sort_values("date_key")

    funds = model.capital.commitments.sort_values("fund_id").reset_index(drop=True)
    dim_fund = funds[["fund_id", "fund_name", "strategy", "vintage"]].copy()
    dim_fund.insert(0, "fund_key", dim_fund.index + 1)
    fund_key = dict(zip(dim_fund["fund_id"], dim_fund["fund_key"]))

    products = sorted(
        set(model.operating.sales["product_line"]).union(model.operating.october_products["product_line"])
    )
    dim_product = pd.DataFrame({"product_line": products})
    dim_product.insert(0, "product_key", dim_product.index + 1)
    product_key = dict(zip(dim_product["product_line"], dim_product["product_key"]))

    opportunities = model.screening.opportunities.sort_values("opp_id").reset_index(drop=True)
    dim_opportunity = opportunities[
        ["opp_id", "name", "sponsor", "asset_class", "geography", "stage"]
    ].copy()
    dim_opportunity.insert(0, "opportunity_key", dim_opportunity.index + 1)
    opp_key = dict(zip(dim_opportunity["opp_id"], dim_opportunity["opportunity_key"]))

    fact_commitment = funds[
        [
            "fund_id",
            "commitment",
            "called_to_date",
            "unfunded",
            "pct_called",
            "distributions_to_date",
            "nav",
            "dpi",
            "rvpi",
            "tvpi",
            "residual_irr",
        ]
    ].copy()
    fact_commitment.insert(0, "fund_key", fact_commitment["fund_id"].map(fund_key))
    fact_commitment.insert(1, "as_of_date_key", date_key(model.capital.as_of))
    fact_commitment = fact_commitment.drop(columns=["fund_id"])

    fact_capital_call = model.capital.calls.copy()
    fact_capital_call["fund_key"] = fact_capital_call["fund_id"].map(fund_key)
    fact_capital_call["notice_date_key"] = fact_capital_call["notice_date"].map(date_key)
    fact_capital_call["due_date_key"] = fact_capital_call["due_date"].map(date_key)
    fact_capital_call = fact_capital_call[
        [
            "call_id",
            "fund_key",
            "notice_date_key",
            "due_date_key",
            "amount",
            "purpose",
            "ledger_status",
            "status",
            "days_until_due",
        ]
    ]

    fact_distribution = model.capital.distributions.copy()
    fact_distribution["fund_key"] = fact_distribution["fund_id"].map(fund_key)
    fact_distribution["notice_date_key"] = fact_distribution["notice_date"].map(date_key)
    fact_distribution["expected_date_key"] = fact_distribution["expected_date"].map(date_key)
    fact_distribution = fact_distribution[
        [
            "dist_id",
            "fund_key",
            "notice_date_key",
            "expected_date_key",
            "amount",
            "dist_type",
            "ledger_status",
            "status",
            "days_until_due",
        ]
    ]

    fact_deadline = model.capital.deadlines.copy()
    fact_deadline["fund_key"] = fact_deadline["fund_id"].map(fund_key)
    fact_deadline["due_date_key"] = fact_deadline["due_date"].map(date_key)
    fact_deadline["received_date_key"] = fact_deadline["received_date"].map(date_key)
    fact_deadline = fact_deadline[
        [
            "deadline_id",
            "fund_key",
            "report_name",
            "period",
            "due_date_key",
            "received_date_key",
            "ledger_status",
            "status",
            "days_until_due",
        ]
    ]

    fact_sales = model.operating.sales.copy()
    fact_sales["product_key"] = fact_sales["product_line"].map(product_key)
    fact_sales["date_key"] = fact_sales["invoice_date"].map(date_key)
    fact_sales = fact_sales[
        ["invoice_id", "date_key", "product_key", "customer", "quantity", "unit_price", "amount", "cogs", "gross_profit", "month"]
    ]

    budget_rows = []
    for row in model.operating.budget.itertuples(index=False):
        year, month_number = (int(part) for part in str(row.month).split("-"))
        budget_rows.append(
            {
                "month_date_key": date_key(date(year, month_number, 1)),
                "product_key": product_key[row.product_line],
                "revenue": row.revenue,
                "cogs": row.cogs,
            }
        )
    fact_budget_revenue = pd.DataFrame(budget_rows)

    fact_month = model.operating.monthly.copy()
    fact_month["month_date_key"] = fact_month["month"].map(lambda value: date_key(date(int(value[:4]), int(value[5:7]), 1)))

    fact_purchasing = model.operating.purchasing.copy()
    fact_purchasing["date_key"] = fact_purchasing["po_date"].map(date_key)
    fact_purchasing = fact_purchasing[["po_id", "date_key", "vendor", "category", "amount", "status", "month"]]

    fact_inventory = model.operating.inventory.copy()
    fact_inventory["product_key"] = fact_inventory["product_line"].map(product_key)
    fact_inventory["as_of_date_key"] = date_key(model.capital.as_of)
    fact_inventory["last_receipt_date_key"] = fact_inventory["last_receipt_date"].map(date_key)
    fact_inventory = fact_inventory[
        [
            "sku",
            "product_key",
            "description",
            "on_hand_qty",
            "unit_cost",
            "extended_cost",
            "reorder_point",
            "below_reorder",
            "as_of_date_key",
            "last_receipt_date_key",
        ]
    ]

    fact_exception = model.operating.exceptions.copy()

    fact_opportunity = opportunities[
        [
            "opp_id",
            "ask_amount",
            "target_irr",
            "target_moic",
            "hold_years",
            "weighted_score",
            "recommendation",
            "hard_flag_count",
            "exposure_share",
            "track_record_years",
            "leverage_ltv",
        ]
    ].copy()
    fact_opportunity.insert(0, "opportunity_key", fact_opportunity["opp_id"].map(opp_key))
    fact_opportunity["red_flags"] = opportunities["red_flags"].map(lambda flags: " | ".join(flags))
    fact_opportunity = fact_opportunity.drop(columns=["opp_id"])

    fact_priority = model.priorities.copy()
    fact_priority["due_date_key"] = fact_priority["due_date"].map(date_key)
    fact_priority = fact_priority[["rank", "title", "owner", "due_date_key", "status", "theme"]]

    fact_task = model.tasks.copy()
    fact_task["due_date_key"] = fact_task["due_date"].map(date_key)
    fact_task = fact_task[["task_id", "title", "owner", "due_date_key", "status", "source", "related"]]

    review_rows = []
    for item in merge_queue(model.queue, decisions):
        review_rows.append(
            {
                "review_id": item["id"],
                "source": item["source"],
                "title": item["title"],
                "method": item["method"],
                "decision_count": len(item["decisions"]),
                "action_count": len(item["action_items"]),
                "review_status": item["review_status"],
            }
        )
    fact_review = pd.DataFrame(review_rows)

    tables = {
        "dim_date": dim_date,
        "dim_fund": dim_fund,
        "dim_product": dim_product,
        "dim_opportunity": dim_opportunity,
        "fact_commitment": fact_commitment,
        "fact_capital_call": fact_capital_call,
        "fact_distribution": fact_distribution,
        "fact_deadline": fact_deadline,
        "fact_sales": fact_sales,
        "fact_budget_revenue": fact_budget_revenue,
        "fact_month": fact_month,
        "fact_purchasing": fact_purchasing,
        "fact_inventory": fact_inventory,
        "fact_exception": fact_exception,
        "fact_opportunity": fact_opportunity,
        "fact_priority": fact_priority,
        "fact_task": fact_task,
        "fact_review": fact_review,
    }
    return {name: frame.reset_index(drop=True) for name, frame in tables.items()}


def write_star(tables: dict[str, pd.DataFrame], directory: Path, sqlite_path: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    if sqlite_path.exists():
        sqlite_path.unlink()
    connection = sqlite3.connect(sqlite_path)
    try:
        for name, frame in tables.items():
            exported = frame.copy()
            for column in exported.columns:
                exported[column] = exported[column].map(_plain)
            exported.to_csv(directory / f"{name}.csv", index=False)
            exported.to_sql(name, connection, index=False, if_exists="replace")
    finally:
        connection.close()


def _plain(value):
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except TypeError:
        pass
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, bool):
        return int(value)
    return value

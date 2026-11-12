"""Capital calls, distributions, reporting deadlines, and unfunded commitments.

Statuses are formulas in the Excel workbook and the same rules here, both
driven by the pinned as-of date in fotoolkit.config.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from fotoolkit.config import AS_OF, DUE_SOON_DAYS
from fotoolkit.finance import money_sum, xirr
from fotoolkit.format_util import money as format_money
from fotoolkit.readers import money_float, parse_date, parse_decimal, parse_int, read_table, require_columns


def call_status(ledger_status: str, due: date, as_of: date, soon_days: int = DUE_SOON_DAYS) -> str:
    if ledger_status.strip().lower() == "paid":
        return "Paid"
    if due < as_of:
        return "Overdue"
    if due <= as_of + timedelta(days=soon_days):
        return "Due in 30 days"
    return "Scheduled"


def distribution_status(ledger_status: str, due: date, as_of: date, soon_days: int = DUE_SOON_DAYS) -> str:
    if ledger_status.strip().lower() == "received":
        return "Received"
    if due < as_of:
        return "Past due"
    if due <= as_of + timedelta(days=soon_days):
        return "Expected in 30 days"
    return "Scheduled"


def deadline_status(ledger_status: str, due: date, as_of: date, soon_days: int = DUE_SOON_DAYS) -> str:
    if ledger_status.strip().lower() == "received":
        return "Received"
    if due < as_of:
        return "Overdue"
    if due <= as_of + timedelta(days=soon_days):
        return "Due in 30 days"
    return "Scheduled"


@dataclass
class CapitalModel:
    as_of: date
    soon_days: int
    commitments: pd.DataFrame
    calls: pd.DataFrame
    distributions: pd.DataFrame
    deadlines: pd.DataFrame
    irr_cashflows: pd.DataFrame
    alerts: pd.DataFrame
    totals: dict
    reconciliation_gaps: list[str]


def load_capital(data_dir: Path, as_of: date = AS_OF, soon_days: int = DUE_SOON_DAYS) -> CapitalModel:
    commitments = read_table(data_dir / "commitments.csv")
    calls = read_table(data_dir / "capital_calls.csv")
    distributions = read_table(data_dir / "distributions.csv")
    deadlines = read_table(data_dir / "reporting_deadlines.csv")
    cashflows = read_table(data_dir / "cashflows.csv")
    require_columns(
        commitments,
        ["fund_id", "fund_name", "strategy", "vintage", "commitment", "called_to_date", "distributions_to_date", "nav"],
        "commitments.csv",
    )
    require_columns(
        calls,
        ["call_id", "fund_id", "notice_date", "due_date", "amount", "purpose", "ledger_status"],
        "capital_calls.csv",
    )
    require_columns(
        distributions,
        ["dist_id", "fund_id", "notice_date", "expected_date", "amount", "dist_type", "ledger_status"],
        "distributions.csv",
    )
    require_columns(
        deadlines,
        ["deadline_id", "fund_id", "report_name", "period", "due_date", "received_date", "ledger_status"],
        "reporting_deadlines.csv",
    )
    require_columns(cashflows, ["fund_id", "flow_date", "amount", "kind"], "cashflows.csv")

    names = {row["fund_id"]: row["fund_name"] for row in commitments}
    commitment_rows = []
    gaps = []
    irr_rows = []
    irr_by_fund = {}

    flows_by_fund: dict[str, list[dict]] = {}
    for row in cashflows:
        flows_by_fund.setdefault(row["fund_id"], []).append(row)

    for row in commitments:
        fund_id = row["fund_id"]
        commitment = parse_decimal(row["commitment"])
        called = parse_decimal(row["called_to_date"])
        distributed = parse_decimal(row["distributions_to_date"])
        nav = parse_decimal(row["nav"])
        fund_flows = flows_by_fund.get(fund_id, [])
        contributed = money_sum(
            -parse_decimal(item["amount"])
            for item in fund_flows
            if item["kind"] == "contribution"
        )
        received = money_sum(
            parse_decimal(item["amount"])
            for item in fund_flows
            if item["kind"] == "distribution"
        )
        if contributed != called or received != distributed:
            gaps.append(fund_id)

        dated = []
        for item in fund_flows:
            dated.append((parse_date(item["flow_date"]), float(parse_decimal(item["amount"]))))
            irr_rows.append(
                {
                    "fund_id": fund_id,
                    "flow_date": parse_date(item["flow_date"]),
                    "amount": money_float(parse_decimal(item["amount"])),
                    "kind": item["kind"],
                    "note": "",
                }
            )
        irr_rows.append(
            {
                "fund_id": fund_id,
                "flow_date": as_of,
                "amount": money_float(nav),
                "kind": "residual_nav",
                "note": "Illustrative only: treats NAV as realized on the as-of date. Not a cash distribution.",
            }
        )
        dated.append((as_of, float(nav)))
        irr_by_fund[fund_id] = xirr(dated)

        unfunded = commitment - called
        commitment_rows.append(
            {
                "fund_id": fund_id,
                "fund_name": row["fund_name"],
                "strategy": row["strategy"],
                "vintage": parse_int(row["vintage"]),
                "commitment": money_float(commitment),
                "called_to_date": money_float(called),
                "unfunded": money_float(unfunded),
                "pct_called": None if commitment == 0 else float(called / commitment),
                "distributions_to_date": money_float(distributed),
                "nav": money_float(nav),
                "dpi": None if called == 0 else float(distributed / called),
                "rvpi": None if called == 0 else float(nav / called),
                "tvpi": None if called == 0 else float((distributed + nav) / called),
                "residual_irr": irr_by_fund[fund_id],
            }
        )

    call_rows = []
    for row in calls:
        due = parse_date(row["due_date"])
        call_rows.append(
            {
                "call_id": row["call_id"],
                "fund_id": row["fund_id"],
                "fund_name": names.get(row["fund_id"], ""),
                "notice_date": parse_date(row["notice_date"]),
                "due_date": due,
                "amount": money_float(parse_decimal(row["amount"])),
                "purpose": row["purpose"],
                "ledger_status": row["ledger_status"],
                "status": call_status(row["ledger_status"], due, as_of, soon_days),
                "days_until_due": (due - as_of).days,
            }
        )

    distribution_rows = []
    for row in distributions:
        due = parse_date(row["expected_date"])
        distribution_rows.append(
            {
                "dist_id": row["dist_id"],
                "fund_id": row["fund_id"],
                "fund_name": names.get(row["fund_id"], ""),
                "notice_date": parse_date(row["notice_date"]),
                "expected_date": due,
                "amount": money_float(parse_decimal(row["amount"])),
                "dist_type": row["dist_type"],
                "ledger_status": row["ledger_status"],
                "status": distribution_status(row["ledger_status"], due, as_of, soon_days),
                "days_until_due": (due - as_of).days,
            }
        )

    deadline_rows = []
    for row in deadlines:
        due = parse_date(row["due_date"])
        received = parse_date(row["received_date"])
        deadline_rows.append(
            {
                "deadline_id": row["deadline_id"],
                "fund_id": row["fund_id"],
                "fund_name": names.get(row["fund_id"], ""),
                "report_name": row["report_name"],
                "period": row["period"],
                "due_date": due,
                "received_date": received,
                "ledger_status": row["ledger_status"],
                "status": deadline_status(row["ledger_status"], due, as_of, soon_days),
                "days_until_due": (due - as_of).days,
            }
        )

    commitments_df = pd.DataFrame(commitment_rows).sort_values("fund_id").reset_index(drop=True)
    calls_df = pd.DataFrame(call_rows).sort_values(["due_date", "call_id"]).reset_index(drop=True)
    distributions_df = pd.DataFrame(distribution_rows).sort_values(["expected_date", "dist_id"]).reset_index(drop=True)
    deadlines_df = pd.DataFrame(deadline_rows).sort_values(["due_date", "deadline_id"]).reset_index(drop=True)
    irr_df = pd.DataFrame(irr_rows).sort_values(["fund_id", "flow_date", "kind"]).reset_index(drop=True)

    known_funds = set(commitments_df["fund_id"])
    orphan_alerts = []
    for label, frame, column in (
        ("capital call", calls_df, "call_id"),
        ("distribution", distributions_df, "dist_id"),
        ("reporting deadline", deadlines_df, "deadline_id"),
    ):
        orphans = sorted(set(frame.loc[~frame["fund_id"].isin(known_funds), column]))
        for item_id in orphans:
            orphan_alerts.append(
                {
                    "severity": "high",
                    "category": "Data quality",
                    "ref_id": item_id,
                    "title": f"{label.title()} {item_id} does not match a fund",
                    "detail": "The fund id is not on the commitment ledger.",
                    "amount": None,
                    "due_date": None,
                }
            )

    alerts = orphan_alerts + _build_alerts(commitments_df, calls_df, distributions_df, deadlines_df, gaps)
    for gap in gaps:
        alerts.append(
            {
                "severity": "high",
                "category": "Reconciliation",
                "ref_id": gap,
                "title": f"{names.get(gap, gap)} cash flows do not tie to the commitment ledger",
                "detail": "Contributions should equal called-to-date, and distributions received should equal distributions-to-date.",
                "amount": None,
                "due_date": None,
            }
        )
    alerts_df = pd.DataFrame(alerts)
    if not alerts_df.empty:
        rank = {"high": 0, "medium": 1, "info": 2}
        alerts_df["_rank"] = alerts_df["severity"].map(rank)
        alerts_df = alerts_df.sort_values(["_rank", "due_date", "ref_id"], na_position="last").drop(columns="_rank")
        alerts_df = alerts_df.reset_index(drop=True)

    commitment_total = money_sum(commitments_df["commitment"])
    called_total = money_sum(commitments_df["called_to_date"])
    unfunded_total = money_sum(commitments_df["unfunded"])
    overdue_calls = calls_df[calls_df["status"] == "Overdue"]
    soon_calls = calls_df[calls_df["status"] == "Due in 30 days"]
    past_dist = distributions_df[distributions_df["status"] == "Past due"]
    soon_dist = distributions_df[distributions_df["status"] == "Expected in 30 days"]
    overdue_deadlines = deadlines_df[deadlines_df["status"] == "Overdue"]
    soon_deadlines = deadlines_df[deadlines_df["status"] == "Due in 30 days"]

    totals = {
        "commitment": money_float(commitment_total),
        "called": money_float(called_total),
        "unfunded": money_float(unfunded_total),
        "pct_called": float(called_total / commitment_total) if commitment_total else None,
        "nav": money_float(money_sum(commitments_df["nav"])),
        "distributions_to_date": money_float(money_sum(commitments_df["distributions_to_date"])),
        "overdue_call_count": int(len(overdue_calls)),
        "overdue_call_amount": money_float(money_sum(overdue_calls["amount"])),
        "due_soon_call_count": int(len(soon_calls)),
        "due_soon_call_amount": money_float(money_sum(soon_calls["amount"])),
        "past_due_distribution_amount": money_float(money_sum(past_dist["amount"])),
        "expected_distribution_amount": money_float(money_sum(soon_dist["amount"])),
        "overdue_deadline_count": int(len(overdue_deadlines)),
        "due_soon_deadline_count": int(len(soon_deadlines)),
        "fund_count": int(len(commitments_df)),
    }
    return CapitalModel(
        as_of=as_of,
        soon_days=soon_days,
        commitments=commitments_df,
        calls=calls_df,
        distributions=distributions_df,
        deadlines=deadlines_df,
        irr_cashflows=irr_df,
        alerts=alerts_df,
        totals=totals,
        reconciliation_gaps=gaps,
    )


def _build_alerts(commitments, calls, distributions, deadlines, gaps) -> list[dict]:
    alerts = []
    for row in calls.itertuples(index=False):
        if row.status == "Overdue":
            alerts.append(
                {
                    "severity": "high",
                    "category": "Capital call",
                    "ref_id": row.call_id,
                    "title": f"{row.fund_name} call {row.call_id} is overdue",
                    "detail": f"{row.purpose}. Due {row.due_date.isoformat()}. {abs(row.days_until_due)} days past due.",
                    "amount": row.amount,
                    "due_date": row.due_date,
                }
            )
        elif row.status == "Due in 30 days":
            alerts.append(
                {
                    "severity": "medium",
                    "category": "Capital call",
                    "ref_id": row.call_id,
                    "title": f"{row.fund_name} call {row.call_id} is due within 30 days",
                    "detail": f"{row.purpose}. Due {row.due_date.isoformat()}.",
                    "amount": row.amount,
                    "due_date": row.due_date,
                }
            )
    for row in distributions.itertuples(index=False):
        if row.status == "Past due":
            alerts.append(
                {
                    "severity": "high",
                    "category": "Distribution",
                    "ref_id": row.dist_id,
                    "title": f"{row.fund_name} distribution {row.dist_id} is past the expected date",
                    "detail": f"{row.dist_type}. Expected {row.expected_date.isoformat()}.",
                    "amount": row.amount,
                    "due_date": row.expected_date,
                }
            )
        elif row.status == "Expected in 30 days":
            alerts.append(
                {
                    "severity": "medium",
                    "category": "Distribution",
                    "ref_id": row.dist_id,
                    "title": f"{row.fund_name} distribution {row.dist_id} is expected within 30 days",
                    "detail": f"{row.dist_type}. Expected {row.expected_date.isoformat()}.",
                    "amount": row.amount,
                    "due_date": row.expected_date,
                }
            )
    for row in deadlines.itertuples(index=False):
        if row.status == "Overdue":
            alerts.append(
                {
                    "severity": "high",
                    "category": "Reporting deadline",
                    "ref_id": row.deadline_id,
                    "title": f"{row.report_name} has not arrived",
                    "detail": f"{row.fund_name}. Due {row.due_date.isoformat()}.",
                    "amount": None,
                    "due_date": row.due_date,
                }
            )
        elif row.status == "Due in 30 days":
            alerts.append(
                {
                    "severity": "medium",
                    "category": "Reporting deadline",
                    "ref_id": row.deadline_id,
                    "title": f"{row.report_name} is due within 30 days",
                    "detail": f"{row.fund_name}. Due {row.due_date.isoformat()}.",
                    "amount": None,
                    "due_date": row.due_date,
                }
            )
    if len(commitments):
        largest = commitments.sort_values(["unfunded", "fund_id"], ascending=[False, True]).iloc[0]
        alerts.append(
            {
                "severity": "info",
                "category": "Liquidity",
                "ref_id": largest["fund_id"],
                "title": "Unfunded commitments still require a cash plan",
                "detail": (
                    f"Largest unfunded balance is {largest['fund_name']} "
                    f"at {format_money(largest['unfunded'])}."
                ),
                "amount": float(money_sum(commitments["unfunded"])),
                "due_date": None,
            }
        )
    return alerts

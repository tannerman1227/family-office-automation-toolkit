"""Monthly operating report for the fictional company Cedar Bend Supply.

Sales, purchasing, and inventory are validated first. Rows that fail a
check are excluded from KPIs and listed on the exception log. One primary
rule is recorded per bad row, in the order below, so the log stays short
enough to clear.

COGS is a standard cost (sales × product ratio). Purchasing is reported
beside the P&L because it is a cash and inventory signal, not the COGS line.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd

from fotoolkit.config import REPORTING_WINDOW_END, REPORTING_WINDOW_START, REPORT_MONTH, YTD_MONTHS
from fotoolkit.finance import money, money_sum
from fotoolkit.readers import money_float, parse_date, parse_decimal, read_table, require_columns

SALES_TOLERANCE = Decimal("1.00")


def _flag(source: str, rule_id: str, record_id: str, row_number: int, message: str) -> dict:
    return {
        "source": source,
        "rule_id": rule_id,
        "record_id": record_id,
        "row_number": row_number,
        "message": message,
    }


def validate_sales(rows: list[dict], window_start: date, window_end: date) -> tuple[list[dict], list[dict]]:
    require_columns(
        rows,
        ["invoice_id", "invoice_date", "customer", "product_line", "quantity", "unit_price", "amount"],
        "sales",
    )
    counts: dict[str, int] = {}
    for row in rows:
        if row["invoice_id"]:
            counts[row["invoice_id"]] = counts.get(row["invoice_id"], 0) + 1
    duplicates = {key for key, count in counts.items() if count > 1}
    clean = []
    exceptions = []
    for row_number, row in enumerate(rows, start=2):
        record_id = row["invoice_id"] or f"row {row_number}"
        if not row["invoice_id"] or not row["customer"] or not row["product_line"]:
            exceptions.append(
                _flag("sales", "S2", record_id, row_number, "Customer, product line, or invoice id is missing.")
            )
            continue
        parsed = parse_date(row["invoice_date"])
        if parsed is None or parsed < window_start or parsed > window_end:
            exceptions.append(
                _flag(
                    "sales",
                    "S4",
                    record_id,
                    row_number,
                    f"Invoice date is missing or outside {window_start.isoformat()} to {window_end.isoformat()}.",
                )
            )
            continue
        if row["invoice_id"] in duplicates:
            exceptions.append(
                _flag("sales", "S3", record_id, row_number, f"Invoice id {row['invoice_id']} is duplicated.")
            )
            continue
        amount = parse_decimal(row["amount"])
        quantity = parse_decimal(row["quantity"])
        price = parse_decimal(row["unit_price"])
        if amount is None or amount <= 0:
            exceptions.append(_flag("sales", "S1", record_id, row_number, "Amount must be greater than zero."))
            continue
        if quantity is None or price is None:
            exceptions.append(
                _flag("sales", "S5", record_id, row_number, "Quantity or unit price is not a number.")
            )
            continue
        extended = (quantity * price).quantize(Decimal("0.01"))
        if abs(extended - amount) > SALES_TOLERANCE:
            exceptions.append(
                _flag(
                    "sales",
                    "S5",
                    record_id,
                    row_number,
                    "Quantity times unit price does not match the amount (tolerance $1).",
                )
            )
            continue
        clean.append(
            {
                "invoice_id": row["invoice_id"],
                "invoice_date": parsed,
                "customer": row["customer"],
                "product_line": row["product_line"],
                "quantity": float(quantity),
                "unit_price": money_float(price),
                "amount": money_float(amount),
                "month": parsed.strftime("%Y-%m"),
            }
        )
    return clean, exceptions


def validate_purchasing(rows: list[dict], window_start: date, window_end: date) -> tuple[list[dict], list[dict]]:
    require_columns(rows, ["po_id", "po_date", "vendor", "category", "amount", "status"], "purchasing")
    counts: dict[str, int] = {}
    for row in rows:
        if row["po_id"]:
            counts[row["po_id"]] = counts.get(row["po_id"], 0) + 1
    duplicates = {key for key, count in counts.items() if count > 1}
    clean = []
    exceptions = []
    for row_number, row in enumerate(rows, start=2):
        record_id = row["po_id"] or f"row {row_number}"
        if not row["po_id"] or not row["vendor"]:
            exceptions.append(_flag("purchasing", "P2", record_id, row_number, "PO id or vendor is missing."))
            continue
        parsed = parse_date(row["po_date"])
        if parsed is None or parsed < window_start or parsed > window_end:
            exceptions.append(
                _flag(
                    "purchasing",
                    "P4",
                    record_id,
                    row_number,
                    f"PO date is missing or outside {window_start.isoformat()} to {window_end.isoformat()}.",
                )
            )
            continue
        if row["po_id"] in duplicates:
            exceptions.append(_flag("purchasing", "P3", record_id, row_number, f"PO id {row['po_id']} is duplicated."))
            continue
        amount = parse_decimal(row["amount"])
        if amount is None or amount <= 0:
            exceptions.append(_flag("purchasing", "P1", record_id, row_number, "Amount must be greater than zero."))
            continue
        clean.append(
            {
                "po_id": row["po_id"],
                "po_date": parsed,
                "vendor": row["vendor"],
                "category": row["category"],
                "amount": money_float(amount),
                "status": row["status"],
                "month": parsed.strftime("%Y-%m"),
            }
        )
    return clean, exceptions


def validate_inventory(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    require_columns(
        rows,
        ["sku", "product_line", "description", "on_hand_qty", "unit_cost", "reorder_point", "last_receipt_date"],
        "inventory",
    )
    clean = []
    exceptions = []
    for row_number, row in enumerate(rows, start=2):
        record_id = row["sku"] or f"row {row_number}"
        if not row["sku"] or not row["product_line"]:
            exceptions.append(_flag("inventory", "I3", record_id, row_number, "SKU or product line is missing."))
            continue
        on_hand = parse_decimal(row["on_hand_qty"])
        cost = parse_decimal(row["unit_cost"])
        reorder = parse_decimal(row["reorder_point"])
        if on_hand is None or on_hand < 0:
            exceptions.append(_flag("inventory", "I1", record_id, row_number, "On-hand quantity cannot be negative."))
            continue
        if cost is None or cost < 0:
            exceptions.append(_flag("inventory", "I2", record_id, row_number, "Unit cost cannot be negative."))
            continue
        extended = money(on_hand * cost)
        clean.append(
            {
                "sku": row["sku"],
                "product_line": row["product_line"],
                "description": row["description"],
                "on_hand_qty": float(on_hand),
                "unit_cost": money_float(cost),
                "reorder_point": float(reorder or 0),
                "extended_cost": money_float(extended),
                "below_reorder": bool(on_hand < (reorder or 0)),
                "last_receipt_date": parse_date(row["last_receipt_date"]),
            }
        )
    return clean, exceptions


@dataclass
class OperatingModel:
    sales: pd.DataFrame
    purchasing: pd.DataFrame
    inventory: pd.DataFrame
    exceptions: pd.DataFrame
    monthly: pd.DataFrame
    budget: pd.DataFrame
    october_products: pd.DataFrame
    october_opex: pd.DataFrame
    kpis: dict


def _sum_where(frame: pd.DataFrame, month: str, column: str = "amount") -> Decimal:
    if frame.empty:
        return Decimal("0.00")
    subset = frame.loc[frame["month"] == month, column]
    return money_sum(subset) if len(subset) else Decimal("0.00")


def load_operating(
    data_dir: Path,
    window_start: date = REPORTING_WINDOW_START,
    window_end: date = REPORTING_WINDOW_END,
) -> OperatingModel:
    sales_rows = read_table(data_dir / "sales.csv")
    purchase_rows = read_table(data_dir / "purchasing.csv")
    inventory_rows = read_table(data_dir / "inventory.csv")
    ratios = read_table(data_dir / "product_costs.csv")
    budget = read_table(data_dir / "revenue_budget.csv")
    opex = read_table(data_dir / "opex.csv")
    opex_budget = read_table(data_dir / "opex_budget.csv")
    purchase_budget = read_table(data_dir / "purchasing_budget.csv")

    ratio_map = {row["product_line"]: parse_decimal(row["cogs_ratio"]) for row in ratios}
    clean_sales, sales_flags = validate_sales(sales_rows, window_start, window_end)
    for row in clean_sales:
        ratio = ratio_map.get(row["product_line"])
        if ratio is None:
            raise ValueError(f"No COGS ratio for product line {row['product_line']}")
        row["cogs"] = money_float(money(Decimal(str(row["amount"])) * ratio))
        row["gross_profit"] = money_float(money(Decimal(str(row["amount"])) - Decimal(str(row["cogs"]))))

    clean_pos, po_flags = validate_purchasing(purchase_rows, window_start, window_end)
    clean_inventory, inventory_flags = validate_inventory(inventory_rows)
    exceptions = pd.DataFrame(sales_flags + po_flags + inventory_flags)

    sales = pd.DataFrame(clean_sales)
    purchasing = pd.DataFrame(clean_pos)
    inventory = pd.DataFrame(clean_inventory)

    budget_rows = []
    for row in budget:
        budget_rows.append(
            {
                "month": row["month"],
                "product_line": row["product_line"],
                "revenue": money_float(parse_decimal(row["revenue"])),
                "cogs": money_float(parse_decimal(row["cogs"])),
            }
        )
    budget_df = pd.DataFrame(budget_rows)

    opex_rows = [
        {"month": row["month"], "category": row["category"], "amount": money_float(parse_decimal(row["amount"]))}
        for row in opex
    ]
    opex_df = pd.DataFrame(opex_rows)
    opex_budget_rows = [
        {"month": row["month"], "category": row["category"], "amount": money_float(parse_decimal(row["amount"]))}
        for row in opex_budget
    ]
    opex_budget_df = pd.DataFrame(opex_budget_rows)
    purchase_budget_map = {row["month"]: parse_decimal(row["amount"]) for row in purchase_budget}

    monthly_rows = []
    for month in YTD_MONTHS:
        revenue = _sum_where(sales, month, "amount")
        cogs = _sum_where(sales, month, "cogs")
        gross = money(revenue - cogs)
        opex_actual = money_sum(opex_df.loc[opex_df["month"] == month, "amount"])
        opex_plan = money_sum(opex_budget_df.loc[opex_budget_df["month"] == month, "amount"])
        month_budget = budget_df[budget_df["month"] == month]
        revenue_plan = money_sum(month_budget["revenue"])
        cogs_plan = money_sum(month_budget["cogs"])
        gross_plan = money(revenue_plan - cogs_plan)
        purchases = _sum_where(purchasing, month, "amount")
        purchase_plan = purchase_budget_map.get(month, Decimal("0"))
        monthly_rows.append(
            {
                "month": month,
                "revenue": money_float(revenue),
                "revenue_budget": money_float(revenue_plan),
                "revenue_variance": money_float(money(revenue - revenue_plan)),
                "cogs": money_float(cogs),
                "cogs_budget": money_float(cogs_plan),
                "gross_profit": money_float(gross),
                "gross_profit_budget": money_float(gross_plan),
                "gross_margin": float(gross / revenue) if revenue else None,
                "gross_margin_budget": float(gross_plan / revenue_plan) if revenue_plan else None,
                "opex": money_float(opex_actual),
                "opex_budget": money_float(opex_plan),
                "opex_variance": money_float(money(opex_actual - opex_plan)),
                "operating_income": money_float(money(gross - opex_actual)),
                "operating_income_budget": money_float(money(gross_plan - opex_plan)),
                "operating_income_variance": money_float(money((gross - opex_actual) - (gross_plan - opex_plan))),
                "purchases": money_float(purchases),
                "purchases_budget": money_float(purchase_plan),
                "purchases_variance": money_float(money(purchases - purchase_plan)),
            }
        )
    monthly = pd.DataFrame(monthly_rows)

    product_lines = list(ratio_map)
    october_sales = sales[sales["month"] == REPORT_MONTH]
    october_budget = budget_df[budget_df["month"] == REPORT_MONTH]
    product_rows = []
    for line in product_lines:
        actual = october_sales[october_sales["product_line"] == line]
        plan = october_budget[october_budget["product_line"] == line]
        revenue = money_sum(actual["amount"]) if len(actual) else Decimal("0")
        cogs = money_sum(actual["cogs"]) if len(actual) else Decimal("0")
        revenue_plan = money_sum(plan["revenue"]) if len(plan) else Decimal("0")
        cogs_plan = money_sum(plan["cogs"]) if len(plan) else Decimal("0")
        product_rows.append(
            {
                "product_line": line,
                "revenue": money_float(revenue),
                "cogs": money_float(cogs),
                "gross_profit": money_float(money(revenue - cogs)),
                "revenue_budget": money_float(revenue_plan),
                "cogs_budget": money_float(cogs_plan),
                "gross_profit_budget": money_float(money(revenue_plan - cogs_plan)),
                "revenue_variance": money_float(money(revenue - revenue_plan)),
            }
        )
    october_products = pd.DataFrame(product_rows)

    october_opex_rows = []
    categories = list(dict.fromkeys(opex_df["category"].tolist()))
    for category in categories:
        actual = money_sum(
            opex_df.loc[(opex_df["month"] == REPORT_MONTH) & (opex_df["category"] == category), "amount"]
        )
        plan = money_sum(
            opex_budget_df.loc[
                (opex_budget_df["month"] == REPORT_MONTH) & (opex_budget_df["category"] == category),
                "amount",
            ]
        )
        october_opex_rows.append(
            {
                "category": category,
                "amount": money_float(actual),
                "budget": money_float(plan),
                "variance": money_float(money(actual - plan)),
            }
        )
    october_opex = pd.DataFrame(october_opex_rows)

    october = monthly[monthly["month"] == REPORT_MONTH].iloc[0]
    ytd_revenue = money_sum(monthly["revenue"])
    ytd_revenue_budget = money_sum(monthly["revenue_budget"])
    ytd_cogs = money_sum(monthly["cogs"])
    ytd_gross = money_sum(monthly["gross_profit"])
    ytd_opex = money_sum(monthly["opex"])
    ytd_oi = money_sum(monthly["operating_income"])
    ytd_oi_budget = money_sum(monthly["operating_income_budget"])
    inventory_value = money_sum(inventory["extended_cost"]) if len(inventory) else Decimal("0")
    days = (window_end - date(window_end.year, window_end.month, 1)).days + 1
    daily_cogs = Decimal(str(october["cogs"])) / Decimal(days)
    days_on_hand = float(inventory_value / daily_cogs) if daily_cogs else None
    below = inventory[inventory["below_reorder"]] if len(inventory) else inventory

    kpis = {
        "report_month": REPORT_MONTH,
        "october_revenue": float(october["revenue"]),
        "october_revenue_budget": float(october["revenue_budget"]),
        "october_revenue_variance": float(october["revenue_variance"]),
        "october_cogs": float(october["cogs"]),
        "october_gross_profit": float(october["gross_profit"]),
        "october_gross_profit_budget": float(october["gross_profit_budget"]),
        "october_gross_margin": float(october["gross_margin"]),
        "october_gross_margin_budget": float(october["gross_margin_budget"]),
        "october_opex": float(october["opex"]),
        "october_opex_budget": float(october["opex_budget"]),
        "october_operating_income": float(october["operating_income"]),
        "october_operating_income_budget": float(october["operating_income_budget"]),
        "october_operating_income_variance": float(october["operating_income_variance"]),
        "october_purchases": float(october["purchases"]),
        "october_purchases_budget": float(october["purchases_budget"]),
        "october_purchases_variance": float(october["purchases_variance"]),
        "ytd_revenue": money_float(ytd_revenue),
        "ytd_revenue_budget": money_float(ytd_revenue_budget),
        "ytd_revenue_variance": money_float(money(ytd_revenue - ytd_revenue_budget)),
        "ytd_cogs": money_float(ytd_cogs),
        "ytd_gross_profit": money_float(ytd_gross),
        "ytd_opex": money_float(ytd_opex),
        "ytd_operating_income": money_float(ytd_oi),
        "ytd_operating_income_budget": money_float(ytd_oi_budget),
        "ytd_operating_income_variance": money_float(money(ytd_oi - ytd_oi_budget)),
        "inventory_value": money_float(inventory_value),
        "days_on_hand": days_on_hand,
        "days_in_report_month": days,
        "skus_below_reorder": below["sku"].tolist() if len(below) else [],
        "exception_count": int(len(exceptions)),
        "sales_exception_count": int((exceptions["source"] == "sales").sum()) if len(exceptions) else 0,
        "purchasing_exception_count": int((exceptions["source"] == "purchasing").sum()) if len(exceptions) else 0,
        "inventory_exception_count": int((exceptions["source"] == "inventory").sum()) if len(exceptions) else 0,
    }
    return OperatingModel(
        sales=sales.reset_index(drop=True),
        purchasing=purchasing.reset_index(drop=True),
        inventory=inventory.reset_index(drop=True),
        exceptions=exceptions.reset_index(drop=True),
        monthly=monthly,
        budget=budget_df.reset_index(drop=True),
        october_products=october_products,
        october_opex=october_opex,
        kpis=kpis,
    )

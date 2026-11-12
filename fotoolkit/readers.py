"""CSV loading with explicit types.

Sample files are read as text first so a blank cell stays blank and is
not turned into NaN before the validation rules see it.
"""

from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd


def read_table(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"Sample file not found: {path}")
    frame = pd.read_csv(path, dtype=str, keep_default_na=False, index_col=False)
    rows = []
    for record in frame.to_dict(orient="records"):
        rows.append({key: str(value).strip() for key, value in record.items()})
    return rows


def require_columns(rows: list[dict], columns: list[str], name: str) -> None:
    if not rows:
        raise ValueError(f"{name} has no data rows")
    missing = [column for column in columns if column not in rows[0]]
    if missing:
        raise ValueError(f"{name} is missing columns: {', '.join(missing)}")


def parse_date(value: str):
    text = (value or "").strip()
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


def parse_decimal(value: str):
    text = (value or "").strip().replace(",", "").replace("$", "")
    if text == "":
        return None
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def parse_int(value: str):
    number = parse_decimal(value)
    if number is None or number != number.to_integral_value():
        return None
    return int(number)


def money_float(number: Decimal) -> float:
    return float(number.quantize(Decimal("0.01")))

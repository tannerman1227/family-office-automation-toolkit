"""Display helpers shared by the dashboard, HTML, and markdown."""

from datetime import date, datetime
from decimal import Decimal


def as_date(value):
    if value is None or value == "":
        return None
    if value.__class__.__name__ in {"NaTType", "NAType"}:
        return None
    if isinstance(value, float) and value != value:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value)[:10]
    return datetime.strptime(text, "%Y-%m-%d").date()


def iso(value) -> str:
    parsed = as_date(value)
    return "" if parsed is None else parsed.isoformat()


def money(value) -> str:
    number = Decimal(str(value)).quantize(Decimal("0.01"))
    sign = "-" if number < 0 else ""
    amount = abs(number)
    if amount == amount.to_integral_value():
        return f"{sign}${amount:,.0f}"
    return f"{sign}${amount:,.2f}"


def pct(value) -> str:
    return f"{Decimal(str(value)) * 100:.2f}%"


def json_number(value) -> float:
    """JSON-safe money or rate. Whole cents stay exact for dollar amounts."""
    quantized = Decimal(str(value)).quantize(Decimal("0.000001"))
    return float(quantized)


def plural(count: int, singular: str, plural_form: str | None = None) -> str:
    word = singular if count == 1 else (plural_form or f"{singular}s")
    return f"{count} {word}"

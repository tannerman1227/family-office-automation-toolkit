"""Small numeric helpers, including a 365-day XIRR.

Residual-value IRR in this project treats NAV as if it were realized on
the as-of date. That is a planning shortcut, not a partner-reported IRR.
"""

from datetime import date
from decimal import Decimal, ROUND_HALF_UP


def money(number) -> Decimal:
    return Decimal(str(number)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def money_sum(values) -> Decimal:
    total = Decimal("0")
    for value in values:
        total += Decimal(str(value))
    return money(total)


def _year_fraction(start: date, current: date) -> float:
    return (current - start).days / 365.0


def npv(flows: list[tuple[date, float]], rate: float) -> float:
    start = min(day for day, _ in flows)
    total = 0.0
    for day, amount in flows:
        total += amount / ((1.0 + rate) ** _year_fraction(start, day))
    return total


def xirr(flows: list[tuple[date, float]], guess: float = 0.10):
    """Excel-style XIRR. Returns None when the flows do not change sign."""
    if len(flows) < 2:
        return None
    amounts = [amount for _, amount in flows]
    if not any(amount < 0 for amount in amounts) or not any(amount > 0 for amount in amounts):
        return None

    def derivative(rate: float) -> float:
        start = min(day for day, _ in flows)
        total = 0.0
        for day, amount in flows:
            years = _year_fraction(start, day)
            if years == 0 or rate <= -0.999999:
                continue
            total += amount * (-years) / ((1.0 + rate) ** (years + 1.0))
        return total

    rate = guess
    for _ in range(80):
        if rate <= -0.999999:
            break
        value = npv(flows, rate)
        slope = derivative(rate)
        if abs(slope) < 1e-14:
            break
        nxt = rate - value / slope
        if nxt <= -0.999999:
            nxt = (rate - 0.999999) / 2.0
        if abs(nxt - rate) < 1e-10:
            if abs(npv(flows, nxt)) < 1e-5:
                return nxt
            break
        rate = nxt

    low, high = -0.90, 5.0
    low_value = npv(flows, low)
    high_value = npv(flows, high)
    if low_value * high_value > 0:
        return None
    for _ in range(80):
        mid = (low + high) / 2.0
        mid_value = npv(flows, mid)
        if abs(mid_value) < 1e-8:
            return mid
        if low_value * mid_value <= 0:
            high = mid
            high_value = mid_value
        else:
            low = mid
            low_value = mid_value
    return (low + high) / 2.0

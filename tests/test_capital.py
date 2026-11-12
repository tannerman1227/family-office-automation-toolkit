from datetime import date
from pathlib import Path

from openpyxl import load_workbook

from fotoolkit.capital import call_status, deadline_status, distribution_status, load_capital
from fotoolkit.config import DATA_DIR
from fotoolkit.finance import xirr
from fotoolkit.workbooks import write_capital_workbook

AS_OF = date(2026, 11, 12)


def test_textbook_xirr_is_ten_percent():
    rate = xirr([(date(2025, 1, 1), -1000.0), (date(2026, 1, 1), 1100.0)])
    assert rate == pytest_approx(0.10)


def pytest_approx(expected, tolerance=1e-8):
    class _Check:
        def __eq__(self, other):
            assert other is not None
            assert abs(other - expected) < tolerance, (other, expected)
            return True

    return _Check()


def test_commitment_totals_and_statuses():
    model = load_capital(DATA_DIR)
    assert model.reconciliation_gaps == []
    assert model.totals["commitment"] == 22_000_000
    assert model.totals["called"] == 13_850_000
    assert model.totals["unfunded"] == 8_150_000
    assert model.totals["overdue_call_count"] == 1
    assert model.totals["overdue_call_amount"] == 400_000
    assert model.totals["due_soon_call_amount"] == 1_150_000
    assert model.totals["past_due_distribution_amount"] == 25_000
    assert model.totals["expected_distribution_amount"] == 275_000
    assert model.totals["overdue_deadline_count"] == 2

    overdue = model.calls.loc[model.calls["status"] == "Overdue", "call_id"].tolist()
    assert overdue == ["CC-1041"]
    paid = set(model.calls.loc[model.calls["status"] == "Paid", "call_id"])
    assert paid == {"CC-1044", "CC-1046"}
    deadlines = set(model.deadlines.loc[model.deadlines["status"] == "Overdue", "deadline_id"])
    assert deadlines == {"RD-302", "RD-305"}
    trinity = model.commitments.loc[model.commitments["fund_id"] == "HL-EN-01"].iloc[0]
    assert trinity["unfunded"] == 0
    assert model.commitments["residual_irr"].notna().all()


def test_status_rules_do_not_use_the_machine_clock():
    assert call_status("open", date(2026, 10, 28), AS_OF) == "Overdue"
    assert call_status("paid", date(2026, 10, 28), AS_OF) == "Paid"
    assert call_status("open", date(2026, 11, 18), AS_OF) == "Due in 30 days"
    assert call_status("open", date(2027, 1, 15), AS_OF) == "Scheduled"
    assert distribution_status("expected", date(2026, 10, 31), AS_OF) == "Past due"
    assert distribution_status("received", date(2026, 9, 15), AS_OF) == "Received"
    assert deadline_status("pending", date(2026, 11, 5), AS_OF) == "Overdue"
    assert deadline_status("pending", date(2026, 11, 20), AS_OF) == "Due in 30 days"
    assert deadline_status("received", date(2026, 10, 31), AS_OF) == "Received"


def test_capital_workbook_has_live_formulas(tmp_path: Path):
    model = load_capital(DATA_DIR)
    path = tmp_path / "capital.xlsx"
    write_capital_workbook(model, path)
    workbook = load_workbook(path)
    assert "AsOfDate" in workbook.defined_names
    commitments = workbook["Commitments"]
    assert commitments["G2"].value == "=E2-F2"
    assert str(commitments["O2"].value).startswith("=XIRR(")
    calls = workbook["Calls"]
    assert "AsOfDate" in calls["H2"].value
    assert "DueSoonDays" in calls["H2"].value
    assert workbook["Calls"].conditional_formatting._cf_rules
    assert workbook["Calls"].data_validations.dataValidation

from fotoolkit.config import DATA_DIR
from fotoolkit.management import load_operating, validate_purchasing, validate_sales
from fotoolkit.config import REPORTING_WINDOW_END, REPORTING_WINDOW_START


def test_october_and_ytd_figures_exclude_bad_rows():
    model = load_operating(DATA_DIR)
    kpis = model.kpis
    assert kpis["october_revenue"] == 462_000
    assert kpis["october_revenue_budget"] == 480_000
    assert kpis["october_revenue_variance"] == -18_000
    assert kpis["october_cogs"] == 302_424
    assert kpis["october_gross_profit"] == 159_576
    assert kpis["october_opex"] == 100_000
    assert kpis["october_opex_budget"] == 96_000
    assert kpis["october_operating_income"] == 59_576
    assert kpis["october_operating_income_budget"] == 69_760
    assert kpis["october_operating_income_variance"] == -10_184
    assert kpis["october_purchases"] == 305_400
    assert kpis["october_purchases_variance"] == 15_400
    assert kpis["ytd_revenue"] == 1_765_000
    assert kpis["ytd_revenue_budget"] == 1_740_000
    assert kpis["ytd_revenue_variance"] == 25_000
    assert kpis["ytd_operating_income"] == 226_296
    assert kpis["ytd_operating_income_variance"] == -2_804
    assert kpis["inventory_value"] == 320_908
    assert round(kpis["days_on_hand"], 1) == 32.9
    assert kpis["skus_below_reorder"] == ["PPE-118", "ABR-220"]
    assert kpis["exception_count"] == 9
    rules = set(zip(model.exceptions["record_id"], model.exceptions["rule_id"]))
    assert ("NEG-01", "S1") in rules
    assert ("DUP-01", "S3") in rules
    assert ("BAD-DATE", "S4") in rules
    assert ("MISS-PROD", "S2") in rules
    assert ("MISMATCH", "S5") in rules
    assert ("PO-NEG", "P1") in rules
    assert ("PO-BLANK", "P2") in rules
    assert ("SKU-NEG", "I1") in rules
    valves = model.october_products.loc[
        model.october_products["product_line"] == "Valves & Fittings", "revenue"
    ].iloc[0]
    assert valves == 168_400
    assert "SKU-NEG" not in set(model.inventory["sku"])


def test_duplicate_purchase_order_is_excluded():
    rows = [
        {"po_id": "PO-1", "po_date": "2026-10-01", "vendor": "A", "category": "Valves & Fittings", "amount": "10", "status": "open"},
        {"po_id": "PO-1", "po_date": "2026-10-02", "vendor": "A", "category": "Valves & Fittings", "amount": "12", "status": "open"},
    ]
    clean, flags = validate_purchasing(rows, REPORTING_WINDOW_START, REPORTING_WINDOW_END)
    assert clean == []
    assert [flag["rule_id"] for flag in flags] == ["P3", "P3"]


def test_sales_tolerance_allows_one_dollar():
    rows = [
        {
            "invoice_id": "OK-1",
            "invoice_date": "2026-10-04",
            "customer": "Klein Fabrication",
            "product_line": "Fasteners",
            "quantity": "2",
            "unit_price": "10.40",
            "amount": "21.00",
        }
    ]
    clean, flags = validate_sales(rows, REPORTING_WINDOW_START, REPORTING_WINDOW_END)
    assert flags == []
    assert clean[0]["amount"] == 21.0

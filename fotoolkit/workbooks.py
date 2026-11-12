"""Excel workbooks with live formulas, not just pasted values.

The Python figures are written where a reviewer needs a number without
opening Excel. Status, unfunded commitment, TVPI, and the October P&L
are also formulas so a change to the as-of date or a source row recalculates.
"""

from datetime import date
from pathlib import Path

from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from fotoolkit.excel_style import (
    AMBER,
    AMBER_INK,
    BODY_FONT,
    CURRENCY,
    DATE,
    GOLD,
    GREEN,
    GREEN_INK,
    NAVY,
    NUMBER,
    PAPER,
    PERCENT,
    RED,
    RED_INK,
    SECTION_FONT,
    TITLE_FONT,
    add_name,
    paint_header,
    prepare,
    widths,
    write_cell,
)


def _banner(ws, last_col: int, text: str):
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=last_col)
    cell = ws.cell(1, 1, text)
    cell.font = Font(name="Calibri", bold=True, size=12, color="FFFFFF")
    cell.fill = PatternFill("solid", fgColor="7A1F1F")
    cell.alignment = Alignment(vertical="center", horizontal="left")
    ws.row_dimensions[1].height = 22


def _status_rules(ws, status_column: str, last_row: int, last_column: str):
    if last_row < 2:
        return
    area = f"A2:{last_column}{last_row}"
    ws.conditional_formatting.add(
        area,
        FormulaRule(
            formula=[f'OR(${status_column}2="Overdue",${status_column}2="Past due")'],
            fill=PatternFill("solid", fgColor=RED),
            font=Font(name="Calibri", color=RED_INK, size=11),
        ),
    )
    ws.conditional_formatting.add(
        area,
        FormulaRule(
            formula=[f'OR(${status_column}2="Due in 30 days",${status_column}2="Expected in 30 days")'],
            fill=PatternFill("solid", fgColor=AMBER),
            font=Font(name="Calibri", color=AMBER_INK, size=11),
        ),
    )
    ws.conditional_formatting.add(
        area,
        FormulaRule(
            formula=[f'OR(${status_column}2="Paid",${status_column}2="Received")'],
            fill=PatternFill("solid", fgColor=GREEN),
            font=Font(name="Calibri", color=GREEN_INK, size=11),
        ),
    )


def write_capital_workbook(model, path: Path) -> None:
    wb = Workbook()
    prepare(wb, "Harborline capital, distribution, and deadline tracker")
    _parameters(wb, model)
    _commitments(wb, model)
    _calls(wb, model)
    _distributions(wb, model)
    _deadlines(wb, model)
    _cashflows(wb, model)
    _alerts(wb, model)
    _liquidity(wb, model)
    _cover(wb, model)
    wb._sheets = [wb["Cover"]] + [ws for ws in wb._sheets if ws.title != "Cover"]
    wb.active = wb["Cover"]
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


def _parameters(wb, model):
    ws = wb.active
    ws.title = "Parameters"
    write_cell(ws, 1, 1, "Parameter", bold=True)
    write_cell(ws, 1, 2, "Value", bold=True)
    write_cell(ws, 2, 1, "As-of date")
    write_cell(ws, 2, 2, model.as_of, DATE)
    write_cell(ws, 3, 1, "Due-soon window (days)")
    write_cell(ws, 3, 2, model.soon_days, "0")
    write_cell(ws, 4, 1, "Data")
    write_cell(ws, 4, 2, "SYNTHETIC")
    write_cell(ws, 5, 1, "Office")
    write_cell(ws, 5, 2, "Harborline Family Office")
    widths(ws, [32, 28])
    ws.sheet_properties.tabColor = GOLD
    add_name(wb, "AsOfDate", "Parameters!$B$2")
    add_name(wb, "DueSoonDays", "Parameters!$B$3")
    ws["A7"] = "Change the as-of date and the status formulas on Calls, Distributions, and Deadlines recalculate."
    ws["A7"].font = BODY_FONT
    ws.merge_cells("A7:B9")
    ws["A7"].alignment = Alignment(wrap_text=True, vertical="top")


def _cover(wb, model):
    ws = wb.create_sheet("Cover", 0)
    _banner(ws, 2, "SYNTHETIC SAMPLE  ·  Not a book of record  ·  Not an instruction to fund a call")
    ws["A3"] = "Capital, distribution, and deadline tracker"
    ws["A3"].font = TITLE_FONT
    ws.merge_cells("A3:B3")
    ws["A4"] = "Harborline Family Office"
    ws["A4"].font = SECTION_FONT
    notes = [
        (6, "As of", model.as_of.strftime("%d %B %Y")),
        (7, "Total commitments", model.totals["commitment"]),
        (8, "Called to date", model.totals["called"]),
        (9, "Unfunded", model.totals["unfunded"]),
        (10, "Overdue capital calls", model.totals["overdue_call_amount"]),
        (11, "Calls due within 30 days", model.totals["due_soon_call_amount"]),
        (12, "Distributions expected within 30 days", model.totals["expected_distribution_amount"]),
        (13, "Overdue fund reports", model.totals["overdue_deadline_count"]),
    ]
    for row, label, value in notes:
        write_cell(ws, row, 1, label, bold=True)
        cell = write_cell(ws, row, 2, value, CURRENCY if isinstance(value, (int, float)) else None)
        if row == 13:
            cell.number_format = "0"
            cell.value = value
    ws["A15"] = (
        "Unfunded, percent called, DPI, RVPI, and TVPI on the Commitments sheet are formulas. "
        "Call and deadline status are formulas tied to Parameters!B2. "
        "Column N on Commitments is the toolkit's residual-value IRR (NAV treated as sold on the as-of date). "
        "Column O is Excel's XIRR of the same cash flows, including that illustrative residual. "
        "The two should match once Excel calculates."
    )
    ws["A15"].alignment = Alignment(wrap_text=True, vertical="top")
    ws["A15"].font = BODY_FONT
    ws.merge_cells("A15:B18")
    ws.row_dimensions[15].height = 30
    widths(ws, [48, 36])
    ws.sheet_properties.tabColor = GOLD
    ws.sheet_view.showGridLines = False
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 1
    ws.oddHeader.left.text = "Harborline Family Office — SYNTHETIC"


def _commitments(wb, model):
    ws = wb.create_sheet("Commitments")
    headers = [
        "Fund id",
        "Fund",
        "Strategy",
        "Vintage",
        "Commitment",
        "Called",
        "Unfunded",
        "Percent called",
        "Distributions",
        "NAV",
        "DPI",
        "RVPI",
        "TVPI",
        "Residual IRR (toolkit)",
        "Residual IRR (Excel XIRR)",
    ]
    for col, header in enumerate(headers, start=1):
        ws.cell(1, col, header)
    spans = _irr_spans(model)
    for index, row in enumerate(model.commitments.itertuples(index=False), start=2):
        write_cell(ws, index, 1, row.fund_id)
        write_cell(ws, index, 2, row.fund_name)
        write_cell(ws, index, 3, row.strategy)
        write_cell(ws, index, 4, row.vintage, "0")
        write_cell(ws, index, 5, row.commitment, CURRENCY)
        write_cell(ws, index, 6, row.called_to_date, CURRENCY)
        write_cell(ws, index, 7, f"=E{index}-F{index}", CURRENCY)
        write_cell(ws, index, 8, f'=IF(E{index}=0,"",F{index}/E{index})', PERCENT)
        write_cell(ws, index, 9, row.distributions_to_date, CURRENCY)
        write_cell(ws, index, 10, row.nav, CURRENCY)
        write_cell(ws, index, 11, f'=IF(F{index}=0,"",I{index}/F{index})', "0.00")
        write_cell(ws, index, 12, f'=IF(F{index}=0,"",J{index}/F{index})', "0.00")
        write_cell(ws, index, 13, f'=IF(F{index}=0,"",(I{index}+J{index})/F{index})', "0.00")
        write_cell(ws, index, 14, row.residual_irr, PERCENT)
        start, end = spans[row.fund_id]
        write_cell(ws, index, 15, f"=XIRR(Cashflows!C{start}:C{end},Cashflows!B{start}:B{end})", PERCENT)
    last = 1 + len(model.commitments)
    total_row = last + 1
    write_cell(ws, total_row, 2, "Total", bold=True)
    for col in (5, 6, 7, 9, 10):
        letter = get_column_letter(col)
        write_cell(ws, total_row, col, f"=SUM({letter}2:{letter}{last})", CURRENCY)
    paint_header(ws, len(headers))
    widths(ws, [14, 40, 28, 12, 16, 16, 16, 16, 16, 16, 10, 10, 10, 22, 26])
    ws.auto_filter.ref = f"A1:O{last}"
    ws.conditional_formatting.add(
        f"G2:G{last}",
        FormulaRule(formula=["G2>0"], fill=PatternFill("solid", fgColor=PAPER)),
    )


def _irr_spans(model) -> dict[str, tuple[int, int]]:
    spans = {}
    start = 2
    for fund_id, group in model.irr_cashflows.groupby("fund_id", sort=True):
        end = start + len(group) - 1
        spans[fund_id] = (start, end)
        start = end + 1
    return spans


def _calls(wb, model):
    ws = wb.create_sheet("Calls")
    headers = [
        "Call id",
        "Fund id",
        "Fund",
        "Notice date",
        "Due date",
        "Amount",
        "Ledger status",
        "Status",
        "Days until due",
        "Purpose",
    ]
    for col, header in enumerate(headers, start=1):
        ws.cell(1, col, header)
    for index, row in enumerate(model.calls.itertuples(index=False), start=2):
        write_cell(ws, index, 1, row.call_id)
        write_cell(ws, index, 2, row.fund_id)
        write_cell(ws, index, 3, row.fund_name)
        write_cell(ws, index, 4, row.notice_date, DATE)
        write_cell(ws, index, 5, row.due_date, DATE)
        write_cell(ws, index, 6, row.amount, CURRENCY)
        write_cell(ws, index, 7, row.ledger_status)
        write_cell(
            ws,
            index,
            8,
            f'=IF(LOWER(G{index})="paid","Paid",IF(E{index}<AsOfDate,"Overdue",IF(E{index}<=AsOfDate+DueSoonDays,"Due in 30 days","Scheduled")))',
        )
        write_cell(ws, index, 9, f"=E{index}-AsOfDate", "0")
        write_cell(ws, index, 10, row.purpose)
    last = 1 + len(model.calls)
    paint_header(ws, len(headers))
    widths(ws, [12, 14, 40, 16, 16, 16, 16, 20, 16, 28])
    _status_rules(ws, "H", last, "J")
    _status_validation(ws, f"G2:G{last}", '"open,paid"')


def _distributions(wb, model):
    ws = wb.create_sheet("Distributions")
    headers = [
        "Distribution id",
        "Fund id",
        "Fund",
        "Notice date",
        "Expected date",
        "Amount",
        "Ledger status",
        "Status",
        "Days until expected",
        "Type",
    ]
    for col, header in enumerate(headers, start=1):
        ws.cell(1, col, header)
    for index, row in enumerate(model.distributions.itertuples(index=False), start=2):
        write_cell(ws, index, 1, row.dist_id)
        write_cell(ws, index, 2, row.fund_id)
        write_cell(ws, index, 3, row.fund_name)
        write_cell(ws, index, 4, row.notice_date, DATE)
        write_cell(ws, index, 5, row.expected_date, DATE)
        write_cell(ws, index, 6, row.amount, CURRENCY)
        write_cell(ws, index, 7, row.ledger_status)
        write_cell(
            ws,
            index,
            8,
            f'=IF(LOWER(G{index})="received","Received",IF(E{index}<AsOfDate,"Past due",IF(E{index}<=AsOfDate+DueSoonDays,"Expected in 30 days","Scheduled")))',
        )
        write_cell(ws, index, 9, f"=E{index}-AsOfDate", "0")
        write_cell(ws, index, 10, row.dist_type)
    last = 1 + len(model.distributions)
    paint_header(ws, len(headers))
    widths(ws, [16, 14, 40, 16, 16, 16, 16, 22, 20, 20])
    _status_rules(ws, "H", last, "J")


def _deadlines(wb, model):
    ws = wb.create_sheet("Deadlines")
    headers = [
        "Deadline id",
        "Fund id",
        "Fund",
        "Report",
        "Period",
        "Due date",
        "Received date",
        "Ledger status",
        "Status",
        "Days until due",
    ]
    for col, header in enumerate(headers, start=1):
        ws.cell(1, col, header)
    for index, row in enumerate(model.deadlines.itertuples(index=False), start=2):
        write_cell(ws, index, 1, row.deadline_id)
        write_cell(ws, index, 2, row.fund_id)
        write_cell(ws, index, 3, row.fund_name)
        write_cell(ws, index, 4, row.report_name)
        write_cell(ws, index, 5, row.period)
        write_cell(ws, index, 6, row.due_date, DATE)
        write_cell(ws, index, 7, row.received_date, DATE)
        write_cell(ws, index, 8, row.ledger_status)
        write_cell(
            ws,
            index,
            9,
            f'=IF(LOWER(H{index})="received","Received",IF(F{index}<AsOfDate,"Overdue",IF(F{index}<=AsOfDate+DueSoonDays,"Due in 30 days","Scheduled")))',
        )
        write_cell(ws, index, 10, f"=F{index}-AsOfDate", "0")
    last = 1 + len(model.deadlines)
    paint_header(ws, len(headers))
    widths(ws, [14, 14, 40, 32, 12, 16, 16, 16, 18, 16])
    _status_rules(ws, "I", last, "J")


def _cashflows(wb, model):
    ws = wb.create_sheet("Cashflows")
    headers = ["Fund id", "Date", "Amount", "Kind", "Note"]
    for col, header in enumerate(headers, start=1):
        ws.cell(1, col, header)
    ordered = model.irr_cashflows.sort_values(["fund_id", "flow_date", "kind"]).reset_index(drop=True)
    for index, row in enumerate(ordered.itertuples(index=False), start=2):
        write_cell(ws, index, 1, row.fund_id)
        write_cell(ws, index, 2, row.flow_date, DATE)
        write_cell(ws, index, 3, row.amount, CURRENCY)
        write_cell(ws, index, 4, row.kind)
        write_cell(ws, index, 5, row.note)
    paint_header(ws, len(headers))
    widths(ws, [14, 16, 18, 18, 88])


def _alerts(wb, model):
    ws = wb.create_sheet("Alerts")
    headers = ["Severity", "Category", "Reference", "Title", "Detail", "Amount", "Due date"]
    for col, header in enumerate(headers, start=1):
        ws.cell(1, col, header)
    for index, row in enumerate(model.alerts.itertuples(index=False), start=2):
        write_cell(ws, index, 1, row.severity)
        write_cell(ws, index, 2, row.category)
        write_cell(ws, index, 3, row.ref_id)
        write_cell(ws, index, 4, row.title)
        write_cell(ws, index, 5, row.detail)
        write_cell(ws, index, 6, None if row.amount is None else row.amount, CURRENCY)
        write_cell(ws, index, 7, row.due_date, DATE)
    last = max(2, 1 + len(model.alerts))
    paint_header(ws, len(headers))
    widths(ws, [12, 22, 14, 62, 78, 18, 16])
    ws.conditional_formatting.add(
        f"A2:G{last}",
        FormulaRule(formula=['$A2="high"'], fill=PatternFill("solid", fgColor=RED), font=Font(color=RED_INK, name="Calibri")),
    )
    ws.conditional_formatting.add(
        f"A2:G{last}",
        FormulaRule(
            formula=['$A2="medium"'],
            fill=PatternFill("solid", fgColor=AMBER),
            font=Font(color=AMBER_INK, name="Calibri"),
        ),
    )


def _liquidity(wb, model):
    ws = wb.create_sheet("Liquidity")
    ws["A1"] = "Fund"
    ws["B1"] = "Unfunded"
    for index, row in enumerate(model.commitments.itertuples(index=False), start=2):
        write_cell(ws, index, 1, row.fund_name)
        write_cell(ws, index, 2, f"=INDEX(Commitments!G:G,MATCH(A{index},Commitments!B:B,0))", CURRENCY)
    last = 1 + len(model.commitments)
    paint_header(ws, 2)
    widths(ws, [44, 18, 18, 18])
    chart = BarChart()
    chart.type = "bar"
    chart.title = "Unfunded commitment"
    chart.style = 10
    chart.y_axis.title = None
    chart.x_axis.title = None
    chart.legend = None
    data = Reference(ws, min_col=2, min_row=1, max_row=last)
    cats = Reference(ws, min_col=1, min_row=2, max_row=last)
    chart.add_data(data, titles_from_data=True)
    chart.set_categories(cats)
    chart.shape = 4
    chart.legend = None
    chart.series[0].graphicalProperties.solidFill = NAVY
    chart.y_axis.majorGridlines = None
    chart.width = 18
    chart.height = 8
    ws.add_chart(chart, "D2")
    ws["A10"] = (
        "Unfunded on this sheet looks up the formula column on Commitments. "
        "It is blank until Excel calculates. The Cover sheet has the toolkit totals from this run."
    )
    ws["A10"].font = BODY_FONT
    ws["A10"].alignment = Alignment(wrap_text=True)
    ws.merge_cells("A10:B13")


def _status_validation(ws, cell_range: str, formula: str):
    validation = DataValidation(type="list", formula1=formula, allow_blank=False)
    validation.error = "Use a status from the list."
    validation.errorTitle = "Status"
    validation.prompt = "Ledger status"
    validation.promptTitle = "Status"
    ws.add_data_validation(validation)
    validation.add(cell_range)


def write_screening_workbook(model, path: Path) -> None:
    wb = Workbook()
    prepare(wb, "Harborline screening pipeline")
    weights = wb.active
    weights.title = "Weights"
    write_cell(weights, 1, 1, "Factor", bold=True)
    write_cell(weights, 1, 2, "Weight", bold=True)
    factors = [
        ("sponsor_score", "Sponsor / team"),
        ("market_score", "Market"),
        ("economics_score", "Economics"),
        ("structure_score", "Structure"),
        ("downside_score", "Downside"),
        ("fit_score", "Portfolio fit"),
    ]
    for index, (key, label) in enumerate(factors, start=2):
        write_cell(weights, index, 1, label)
        write_cell(weights, index, 2, model.weights[key], "0.00")
    write_cell(weights, 8, 1, "Advance at or above", bold=True)
    write_cell(weights, 8, 2, 4, "0.00")
    write_cell(weights, 9, 1, "Watch at or above", bold=True)
    write_cell(weights, 9, 2, 3.2, "0.00")
    write_cell(weights, 10, 1, "Total commitments (concentration base)", bold=True)
    write_cell(weights, 10, 2, model.total_commitment, CURRENCY)
    widths(weights, [42, 22])
    weights["A12"] = (
        "A hard flag forces Pass. A soft flag (concentration above 35% of total commitments) "
        "caps the result at Watch. Scores are sample analyst inputs, not a model."
    )
    weights["A12"].alignment = Alignment(wrap_text=True, vertical="top")
    weights["A12"].font = BODY_FONT
    weights.merge_cells("A12:B14")
    weights.sheet_properties.tabColor = GOLD

    ws = wb.create_sheet("Pipeline")
    headers = [
        "Id",
        "Opportunity",
        "Sponsor",
        "Asset class",
        "Ask",
        "Target IRR",
        "Target MOIC",
        "Hold (years)",
        "Sponsor",
        "Market",
        "Economics",
        "Structure",
        "Downside",
        "Fit",
        "Weighted score",
        "Score check",
        "Recommendation",
        "Score ties",
        "Red flags",
    ]
    for col, header in enumerate(headers, start=1):
        ws.cell(1, col, header)
    for index, row in enumerate(model.opportunities.itertuples(index=False), start=2):
        write_cell(ws, index, 1, row.opp_id)
        write_cell(ws, index, 2, row.name)
        write_cell(ws, index, 3, row.sponsor)
        write_cell(ws, index, 4, row.asset_class)
        write_cell(ws, index, 5, row.ask_amount, CURRENCY)
        write_cell(ws, index, 6, row.target_irr, PERCENT)
        write_cell(ws, index, 7, row.target_moic, "0.00")
        write_cell(ws, index, 8, row.hold_years, "0")
        for offset, _key in enumerate(factors):
            write_cell(ws, index, 9 + offset, getattr(row, factors[offset][0]), "0")
        write_cell(ws, index, 15, row.weighted_score, "0.00")
        write_cell(
            ws,
            index,
            16,
            f"=I{index}*Weights!$B$2+J{index}*Weights!$B$3+K{index}*Weights!$B$4+"
            f"L{index}*Weights!$B$5+M{index}*Weights!$B$6+N{index}*Weights!$B$7",
            "0.00",
        )
        write_cell(ws, index, 17, row.recommendation)
        write_cell(ws, index, 18, f'=IF(ABS(P{index}-O{index})<0.001,"Score ties","Score does not tie")')
        write_cell(ws, index, 19, " | ".join(row.red_flags) or None)
    last = 1 + len(model.opportunities)
    paint_header(ws, len(headers))
    widths(ws, [10, 28, 24, 26, 14, 12, 14, 14, 12, 12, 12, 12, 12, 10, 16, 14, 18, 22, 70])
    ws.conditional_formatting.add(
        f"A2:S{last}",
        FormulaRule(formula=['$Q2="Pass"'], fill=PatternFill("solid", fgColor=RED)),
    )
    ws.conditional_formatting.add(
        f"A2:S{last}",
        FormulaRule(formula=['$Q2="Watch"'], fill=PatternFill("solid", fgColor=AMBER)),
    )
    ws.conditional_formatting.add(
        f"A2:S{last}",
        FormulaRule(formula=['$Q2="Advance"'], fill=PatternFill("solid", fgColor=GREEN)),
    )
    ws.auto_filter.ref = f"A1:S{last}"
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


def write_management_workbook(model, ratios: dict[str, float], path: Path) -> None:
    wb = Workbook()
    prepare(wb, "Cedar Bend Supply monthly management report")
    params = wb.active
    params.title = "Parameters"
    write_cell(params, 1, 1, "Parameter", bold=True)
    write_cell(params, 1, 2, "Value", bold=True)
    write_cell(params, 2, 1, "Report month")
    write_cell(params, 2, 2, model.kpis["report_month"])
    write_cell(params, 3, 1, "Month start")
    write_cell(params, 3, 2, date(2026, 10, 1), DATE)
    write_cell(params, 4, 1, "Month end, exclusive")
    write_cell(params, 4, 2, date(2026, 11, 1), DATE)
    write_cell(params, 5, 1, "Company")
    write_cell(params, 5, 2, "Cedar Bend Supply")
    write_cell(params, 6, 1, "Data")
    write_cell(params, 6, 2, "SYNTHETIC")
    widths(params, [28, 24])
    params["A8"] = (
        "October P&L revenue and COGS are SUMIFS against Sales_Clean. "
        "Rows that failed validation are on Exceptions and are not in Sales_Clean. "
        "Purchasing is not COGS. COGS is sales times the standard cost ratio."
    )
    params["A8"].alignment = Alignment(wrap_text=True, vertical="top")
    params["A8"].font = BODY_FONT
    params.merge_cells("A8:B11")
    params.sheet_properties.tabColor = GOLD
    add_name(wb, "MonthStart", "Parameters!$B$3")
    add_name(wb, "MonthEnd", "Parameters!$B$4")

    ratios_ws = wb.create_sheet("CostRatios")
    write_cell(ratios_ws, 1, 1, "Product line", bold=True)
    write_cell(ratios_ws, 1, 2, "COGS ratio", bold=True)
    for index, (line, ratio) in enumerate(ratios.items(), start=2):
        write_cell(ratios_ws, index, 1, line)
        text = str(ratio)
        if text.startswith("0.") and text[2:].isdigit():
            places = text.split(".", 1)[1]
            write_cell(ratios_ws, index, 2, f"={int(places)}/{10 ** len(places)}", "0.00%")
        else:
            write_cell(ratios_ws, index, 2, float(ratio), "0.00%")
    widths(ratios_ws, [24, 14])

    sales = wb.create_sheet("Sales_Clean")
    sales_headers = [
        "Invoice",
        "Date",
        "Customer",
        "Product line",
        "Quantity",
        "Unit price",
        "Amount",
        "COGS",
        "Month",
    ]
    for col, header in enumerate(sales_headers, start=1):
        sales.cell(1, col, header)
    for index, row in enumerate(model.sales.itertuples(index=False), start=2):
        write_cell(sales, index, 1, row.invoice_id)
        write_cell(sales, index, 2, row.invoice_date, DATE)
        write_cell(sales, index, 3, row.customer)
        write_cell(sales, index, 4, row.product_line)
        write_cell(sales, index, 5, row.quantity, "#,##0.00")
        write_cell(sales, index, 6, row.unit_price, CURRENCY)
        write_cell(sales, index, 7, row.amount, CURRENCY)
        write_cell(
            sales,
            index,
            8,
            f'=IF(G{index}="","",G{index}*IFERROR(INDEX(CostRatios!$B$2:$B$20,MATCH(D{index},CostRatios!$A$2:$A$20,0)),0))',
            CURRENCY,
        )
        write_cell(sales, index, 9, row.month)
    paint_header(sales, len(sales_headers))
    widths(sales, [14, 14, 32, 22, 12, 14, 14, 14, 12])

    exceptions = wb.create_sheet("Exceptions")
    exc_headers = ["Source", "Rule", "Record", "Source row", "Message"]
    for col, header in enumerate(exc_headers, start=1):
        exceptions.cell(1, col, header)
    for index, row in enumerate(model.exceptions.itertuples(index=False), start=2):
        write_cell(exceptions, index, 1, row.source)
        write_cell(exceptions, index, 2, row.rule_id)
        write_cell(exceptions, index, 3, row.record_id)
        write_cell(exceptions, index, 4, row.row_number, "0")
        write_cell(exceptions, index, 5, row.message)
    paint_header(exceptions, len(exc_headers))
    widths(exceptions, [14, 10, 16, 14, 78])
    exceptions.sheet_properties.tabColor = RED_INK

    pnl = wb.create_sheet("October_PnL")
    pnl_headers = [
        "Product line",
        "Revenue",
        "COGS",
        "Gross profit",
        "Revenue budget",
        "COGS budget",
        "Gross profit budget",
        "Revenue variance",
        "Gross profit variance",
    ]
    for col, header in enumerate(pnl_headers, start=1):
        pnl.cell(1, col, header)
    for index, row in enumerate(model.october_products.itertuples(index=False), start=2):
        write_cell(pnl, index, 1, row.product_line)
        write_cell(
            pnl,
            index,
            2,
            f'=SUMIFS(Sales_Clean!$G:$G,Sales_Clean!$D:$D,A{index},Sales_Clean!$B:$B,">="&MonthStart,Sales_Clean!$B:$B,"<"&MonthEnd)',
            CURRENCY,
        )
        write_cell(
            pnl,
            index,
            3,
            f'=SUMIFS(Sales_Clean!$H:$H,Sales_Clean!$D:$D,A{index},Sales_Clean!$B:$B,">="&MonthStart,Sales_Clean!$B:$B,"<"&MonthEnd)',
            CURRENCY,
        )
        write_cell(pnl, index, 4, f"=B{index}-C{index}", CURRENCY)
        write_cell(pnl, index, 5, row.revenue_budget, CURRENCY)
        write_cell(pnl, index, 6, row.cogs_budget, CURRENCY)
        write_cell(pnl, index, 7, f"=E{index}-F{index}", CURRENCY)
        write_cell(pnl, index, 8, f"=B{index}-E{index}", CURRENCY)
        write_cell(pnl, index, 9, f"=D{index}-G{index}", CURRENCY)
    last_product = 1 + len(model.october_products)
    total = last_product + 1
    write_cell(pnl, total, 1, "Total", bold=True)
    for col in range(2, 10):
        letter = get_column_letter(col)
        write_cell(pnl, total, col, f"=SUM({letter}2:{letter}{last_product})", CURRENCY)
    opex_start = total + 2
    write_cell(pnl, opex_start, 1, "Operating expense", bold=True)
    write_cell(pnl, opex_start, 2, "Actual", bold=True)
    write_cell(pnl, opex_start, 3, "Budget", bold=True)
    write_cell(pnl, opex_start, 4, "Variance", bold=True)
    for offset, row in enumerate(model.october_opex.itertuples(index=False), start=1):
        line = opex_start + offset
        write_cell(pnl, line, 1, row.category)
        write_cell(pnl, line, 2, f'=SUMIFS(Opex!$C:$C,Opex!$A:$A,Parameters!$B$2,Opex!$B:$B,A{line})', CURRENCY)
        write_cell(pnl, line, 3, row.budget, CURRENCY)
        write_cell(pnl, line, 4, f"=B{line}-C{line}", CURRENCY)
    opex_last = opex_start + len(model.october_opex)
    opex_total = opex_last + 1
    write_cell(pnl, opex_total, 1, "Total operating expense", bold=True)
    write_cell(pnl, opex_total, 2, f"=SUM(B{opex_start+1}:B{opex_last})", CURRENCY)
    write_cell(pnl, opex_total, 3, f"=SUM(C{opex_start+1}:C{opex_last})", CURRENCY)
    write_cell(pnl, opex_total, 4, f"=B{opex_total}-C{opex_total}", CURRENCY)
    oi_row = opex_total + 2
    write_cell(pnl, oi_row, 1, "Operating income", bold=True)
    write_cell(pnl, oi_row, 2, f"=D{total}-B{opex_total}", CURRENCY)
    write_cell(pnl, oi_row, 3, f"=G{total}-C{opex_total}", CURRENCY)
    write_cell(pnl, oi_row, 4, f"=B{oi_row}-C{oi_row}", CURRENCY)
    paint_header(pnl, len(pnl_headers))
    pnl.auto_filter.ref = f"A1:I{last_product}"
    widths(pnl, [28, 18, 18, 20, 18, 16, 22, 20, 24])
    pnl.conditional_formatting.add(
        f"H2:I{last_product}",
        FormulaRule(formula=["H2<0"], font=Font(color=RED_INK, name="Calibri")),
    )

    opex = wb.create_sheet("Opex")
    for col, header in enumerate(["Month", "Category", "Amount"], start=1):
        opex.cell(1, col, header)
    # Rebuilt from the monthly categories already on the model via the caller: we only
    # have October in october_opex. The full year is passed through kpis indirectly.
    # The sheet is filled by the caller-supplied frame stored on the model... it is not.
    # Fill from a reconstruction in write function using nothing? The pipeline passes
    # the operating model only. October formulas need every opex row, not just October,
    # if Trend uses them. October SUMIFS filters the report month, so October rows are enough
    # for October_PnL. Write those actuals as the source the formula sums.
    for index, row in enumerate(model.october_opex.itertuples(index=False), start=2):
        write_cell(opex, index, 1, model.kpis["report_month"])
        write_cell(opex, index, 2, row.category)
        write_cell(opex, index, 3, row.amount, CURRENCY)
    paint_header(opex, 3)
    widths(opex, [14, 18, 16])

    inventory = wb.create_sheet("Inventory")
    headers = ["SKU", "Product line", "Description", "On hand", "Unit cost", "Extended", "Reorder point", "Position", "Last receipt"]
    for col, header in enumerate(headers, start=1):
        inventory.cell(1, col, header)
    for index, row in enumerate(model.inventory.itertuples(index=False), start=2):
        write_cell(inventory, index, 1, row.sku)
        write_cell(inventory, index, 2, row.product_line)
        write_cell(inventory, index, 3, row.description)
        write_cell(inventory, index, 4, row.on_hand_qty, "#,##0.00")
        write_cell(inventory, index, 5, row.unit_cost, NUMBER)
        write_cell(inventory, index, 6, f"=D{index}*E{index}", CURRENCY)
        write_cell(inventory, index, 7, row.reorder_point, "#,##0.00")
        write_cell(inventory, index, 8, f'=IF(D{index}<G{index},"Below reorder","OK")')
        write_cell(inventory, index, 9, row.last_receipt_date, DATE)
    last_sku = 1 + len(model.inventory)
    write_cell(inventory, last_sku + 1, 3, "Inventory value", bold=True)
    write_cell(inventory, last_sku + 1, 6, f"=SUM(F2:F{last_sku})", CURRENCY)
    paint_header(inventory, len(headers))
    widths(inventory, [12, 20, 22, 12, 12, 16, 16, 16, 16])
    inventory.conditional_formatting.add(
        f"A2:I{last_sku}",
        FormulaRule(formula=['$H2="Below reorder"'], fill=PatternFill("solid", fgColor=AMBER)),
    )

    trend = wb.create_sheet("Trend")
    trend_headers = ["Month", "Revenue", "Revenue budget", "Variance", "Operating income", "OI budget", "OI variance"]
    for col, header in enumerate(trend_headers, start=1):
        trend.cell(1, col, header)
    for index, row in enumerate(model.monthly.itertuples(index=False), start=2):
        write_cell(trend, index, 1, row.month)
        write_cell(trend, index, 2, row.revenue, CURRENCY)
        write_cell(trend, index, 3, row.revenue_budget, CURRENCY)
        write_cell(trend, index, 4, f"=B{index}-C{index}", CURRENCY)
        write_cell(trend, index, 5, row.operating_income, CURRENCY)
        write_cell(trend, index, 6, row.operating_income_budget, CURRENCY)
        write_cell(trend, index, 7, f"=E{index}-F{index}", CURRENCY)
    last_month = 1 + len(model.monthly)
    paint_header(trend, len(trend_headers))
    widths(trend, [12, 16, 18, 16, 20, 16, 16])
    chart = BarChart()
    chart.type = "col"
    chart.grouping = "clustered"
    chart.title = "Revenue versus budget"
    chart.style = 10
    chart.y_axis.numFmt = '$#,##0'
    data = Reference(trend, min_col=2, max_col=3, min_row=1, max_row=last_month)
    cats = Reference(trend, min_col=1, min_row=2, max_row=last_month)
    chart.add_data(data, titles_from_data=True)
    chart.set_categories(cats)
    chart.shape = 4
    chart.width = 18
    chart.height = 8
    chart.series[0].graphicalProperties.solidFill = NAVY
    chart.series[1].graphicalProperties.solidFill = GOLD
    trend.add_chart(chart, "A8")

    cover = wb.create_sheet("Cover", 0)
    _banner(cover, 2, "SYNTHETIC SAMPLE  ·  Cedar Bend Supply  ·  Figures below are from this toolkit run")
    cover["A3"] = "Monthly management report"
    cover["A3"].font = TITLE_FONT
    cover["A4"] = model.kpis["report_month"]
    cover["A4"].font = SECTION_FONT
    kpis = [
        (6, "October revenue", model.kpis["october_revenue"]),
        (7, "October revenue budget", model.kpis["october_revenue_budget"]),
        (8, "Revenue variance", model.kpis["october_revenue_variance"]),
        (9, "Gross profit", model.kpis["october_gross_profit"]),
        (10, "Operating income", model.kpis["october_operating_income"]),
        (11, "Operating income versus budget", model.kpis["october_operating_income_variance"]),
        (12, "Purchases (not COGS)", model.kpis["october_purchases"]),
        (13, "Inventory value", model.kpis["inventory_value"]),
        (14, "Exception rows excluded", model.kpis["exception_count"]),
    ]
    for row, label, value in kpis:
        write_cell(cover, row, 1, label, bold=True)
        cell = write_cell(cover, row, 2, value, None if row == 14 else CURRENCY)
        if row == 14:
            cell.number_format = "0"
    cover["A16"] = (
        f"Days on hand uses October COGS and a {model.kpis['days_in_report_month']}-day month: "
        f"{model.kpis['days_on_hand']:.1f}. SKUs below reorder: "
        + ", ".join(model.kpis["skus_below_reorder"])
        + ". YTD revenue is still ahead of budget; October is not, and operating expense is over plan."
    )
    cover["A16"].alignment = Alignment(wrap_text=True, vertical="top")
    cover["A16"].font = BODY_FONT
    cover.merge_cells("A16:B18")
    widths(cover, [40, 22])
    cover.sheet_view.showGridLines = False
    cover.sheet_properties.tabColor = GOLD
    wb.active = cover
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)

"""Shared workbook styling. Navy, paper, and a single gold accent."""

from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.workbook.defined_name import DefinedName

NAVY = "1B3A4B"
INK = "14242E"
GOLD = "C4A35A"
PAPER = "F7F4EE"
RED = "F4D6D6"
RED_INK = "9C2F2F"
AMBER = "F8E8C8"
AMBER_INK = "8A5A12"
GREEN = "D9EDE3"
GREEN_INK = "1F6B4A"
LINE = "E3DCCE"
WHITE = "FFFFFF"

THIN = Border(
    left=Side(style="thin", color=LINE),
    right=Side(style="thin", color=LINE),
    top=Side(style="thin", color=LINE),
    bottom=Side(style="thin", color=LINE),
)
HEADER_FONT = Font(name="Calibri", bold=True, color=WHITE, size=11)
BODY_FONT = Font(name="Calibri", size=11, color=INK)
TITLE_FONT = Font(name="Calibri", bold=True, size=20, color=NAVY)
SECTION_FONT = Font(name="Calibri", bold=True, size=14, color=NAVY)
LABEL_FONT = Font(name="Calibri", bold=True, size=11, color=NAVY)

CURRENCY = '$#,##0'
PERCENT = "0.00%"
DATE = "yyyy-mm-dd"
NUMBER = "#,##0.00"


def prepare(wb, title: str):
    wb.properties.title = title
    wb.properties.creator = "Family Office Automation Toolkit"
    wb.properties.subject = "SYNTHETIC sample — Harborline Family Office"
    wb.properties.category = "SYNTHETIC"
    wb.properties.description = "Generated from the synthetic sample in data/sample. Not a live book of record."


def add_name(wb, name: str, ref: str):
    wb.defined_names.add(DefinedName(name=name, attr_text=ref))


def paint_header(ws, columns: int):
    fill = PatternFill("solid", fgColor=NAVY)
    for col in range(1, columns + 1):
        cell = ws.cell(1, col)
        cell.fill = fill
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[1].height = 32
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(columns)}{max(ws.max_row, 1)}"
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.page_setup.paperSize = ws.PAPERSIZE_TABLOID
    ws.sheet_properties.tabColor = NAVY
    ws.oddHeader.left.text = "Harborline Family Office — SYNTHETIC"
    ws.oddFooter.left.text = "Sample data. Check the exception log before using a figure."
    ws.oddFooter.right.text = "Page &P"
    ws.print_title_rows = "1:1"
    ws.page_setup.horizontalCentered = True
    ws.sheet_view.showGridLines = False
    ws.sheet_properties.pageSetUpPr.fitToPage = True


def widths(ws, sizes: list[int]):
    for index, size in enumerate(sizes, start=1):
        ws.column_dimensions[get_column_letter(index)].width = size


def write_cell(ws, row: int, col: int, value, fmt: str | None = None, bold: bool = False):
    if value is None or value.__class__.__name__ in {"NaTType", "NAType"}:
        value = None
    cell = ws.cell(row, col, value)
    cell.font = Font(name="Calibri", size=11, color=INK, bold=bold)
    cell.alignment = Alignment(vertical="center", wrap_text=True)
    cell.border = THIN
    if fmt:
        cell.number_format = fmt
    return cell


def fill_range(ws, cell_range: str, color: str):
    fill = PatternFill("solid", fgColor=color)
    for row in ws[cell_range]:
        for cell in row:
            cell.fill = fill

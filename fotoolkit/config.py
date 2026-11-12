"""Fixed settings for the synthetic Harborline sample.

The as-of date is pinned so every run and test classifies the same
items as overdue. It is not "today" on the machine that happens to run the code.
"""

from datetime import date
from pathlib import Path

AS_OF = date(2026, 11, 12)
DUE_SOON_DAYS = 30
OFFICE_NAME = "Harborline Family Office"
OPCO_NAME = "Cedar Bend Supply"
DATA_LABEL = "SYNTHETIC"

REPORT_MONTH = "2026-10"
YTD_MONTHS = ("2026-07", "2026-08", "2026-09", "2026-10")
REPORTING_WINDOW_START = date(2026, 7, 1)
REPORTING_WINDOW_END = date(2026, 10, 31)

# Screening rubric. Weights must sum to 1. Scores are analyst inputs on a 1–5 scale.
SCORE_WEIGHTS = {
    "sponsor_score": "0.20",
    "market_score": "0.15",
    "economics_score": "0.20",
    "structure_score": "0.15",
    "downside_score": "0.15",
    "fit_score": "0.15",
}
ADVANCE_MIN = "4.0"
WATCH_MIN = "3.2"
CONCENTRATION_LIMIT = "0.35"
MIN_TRACK_YEARS = 3
MAX_LTV = "0.65"
HIGH_IRR = "0.25"
WEAK_DOWNSIDE = 2

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data" / "sample"
OUTPUT_DIR = REPO_ROOT / "outputs"

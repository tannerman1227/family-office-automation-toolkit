"""Capture README screenshots with the system Chrome.

Not part of the test run. Requires the `playwright` package and a local
Streamlit server on port 8501 for the dashboard pages.
"""

from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "images"
BASE = "http://127.0.0.1:8501"
CHROME = "/usr/bin/google-chrome-stable"


def shot(page, url, filename, wait_for: str, full_page: bool = False):
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_selector(f"text={wait_for}", timeout=60000)
    page.wait_for_timeout(800)
    page.screenshot(path=str(OUT / filename), full_page=full_page)
    print(filename)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=CHROME, headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1200})
        shot(page, f"{BASE}/?page=Overview", "dashboard_overview.png", "Needs a person")
        shot(page, f"{BASE}/?page=Capital", "dashboard_capital.png", "Commitments")
        shot(page, f"{BASE}/?page=Review", "dashboard_review.png", "Approve and add to tasks", full_page=True)
        memo = (ROOT / "outputs" / "screening" / "memos" / "CAD-01.html").as_uri()
        shot(page, memo, "screening_memo.png", "PASS", full_page=True)
        report = (ROOT / "outputs" / "management" / "monthly_report.html").as_uri()
        shot(page, report, "monthly_report.png", "October close", full_page=True)
        browser.close()


if __name__ == "__main__":
    main()

"""One-page HTML memos. Same numbers as the Excel workbooks and the dashboard."""

import html
from pathlib import Path

from fotoolkit.format_util import money, pct


MEMO_CSS = """
:root { color-scheme: light; }
* { box-sizing: border-box; }
body { margin: 0; background: #e7e1d6; color: #14242e; font-family: Georgia, "Iowan Old Style", serif; }
.page { max-width: 820px; margin: 24px auto; background: #fff; padding: 36px 42px 28px; }
.banner { background: #7a1f1f; color: #fff; font-family: "Source Sans 3", "Segoe UI", sans-serif;
  font-size: 12px; letter-spacing: .04em; padding: 8px 12px; margin: -36px -42px 22px; }
.kicker { font-family: "Source Sans 3", "Segoe UI", sans-serif; letter-spacing: .14em;
  text-transform: uppercase; font-size: 12px; color: #1b3a4b; margin: 0; }
h1 { font-size: 28px; line-height: 1.15; margin: 6px 0 4px; font-weight: 600; }
.meta { font-family: "Source Sans 3", "Segoe UI", sans-serif; color: #5c5348; font-size: 14px; margin-bottom: 16px; }
.stamp { float: right; border: 2px solid; padding: 8px 12px; font-family: "Source Sans 3", "Segoe UI", sans-serif;
  letter-spacing: .12em; font-weight: 700; }
.advance { color: #1f6b4a; border-color: #1f6b4a; }
.watch { color: #8a5a12; border-color: #8a5a12; }
.pass { color: #9c2f2f; border-color: #9c2f2f; }
h2 { font-family: "Source Sans 3", "Segoe UI", sans-serif; font-size: 13px; letter-spacing: .08em;
  text-transform: uppercase; color: #1b3a4b; border-bottom: 1px solid #e3dcce; padding-bottom: 4px; margin: 22px 0 8px; }
p { font-size: 15px; line-height: 1.45; margin: 0 0 8px; }
table { width: 100%; border-collapse: collapse; font-family: "Source Sans 3", "Segoe UI", sans-serif; font-size: 14px; }
th { text-align: left; font-weight: 600; color: #5c5348; padding: 4px 8px 4px 0; }
td { padding: 4px 8px 4px 0; vertical-align: top; }
td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
.bar { height: 8px; background: #f4f1ea; width: 120px; display: inline-block; vertical-align: middle; }
.bar span { display: block; height: 8px; background: #1b3a4b; }
ul { margin: 6px 0 0; padding-left: 18px; }
li { margin: 3px 0; font-size: 15px; }
.footer { margin-top: 22px; font-family: "Source Sans 3", "Segoe UI", sans-serif; font-size: 12px; color: #5c5348; }
.cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 12px 0 4px; }
.card { background: #f7f4ee; padding: 10px 12px; }
.card .label { font-family: "Source Sans 3", "Segoe UI", sans-serif; font-size: 11px; letter-spacing: .06em;
  text-transform: uppercase; color: #5c5348; }
.card .value { font-family: "Source Sans 3", "Segoe UI", sans-serif; font-size: 20px; color: #1b3a4b; margin-top: 2px; }
.neg { color: #9c2f2f; }
a { color: #1b3a4b; }
"""


def _page(title: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{html.escape(title)}</title>
<style>{MEMO_CSS}</style>
</head>
<body>
<article class="page">
{body}
</article>
</body>
</html>
"""


def _score_row(label: str, score: int) -> str:
    width = int(score) * 20
    return (
        "<tr>"
        f"<th>{html.escape(label)}</th>"
        f"<td>{score} / 5</td>"
        f'<td><span class="bar"><span style="width:{width}%"></span></span></td>'
        "</tr>"
    )


def screening_memo(row, as_of_label: str) -> str:
    flags = list(row.red_flags)
    flag_html = "".join(f"<li>{html.escape(flag)}</li>" for flag in flags) or "<li>None under the published rules.</li>"
    questions = "".join(f"<li>{html.escape(question)}</li>" for question in row.questions)
    band = row.recommendation.lower()
    scores = "".join(
        [
            _score_row("Sponsor / team", row.sponsor_score),
            _score_row("Market", row.market_score),
            _score_row("Economics", row.economics_score),
            _score_row("Structure", row.structure_score),
            _score_row("Downside", row.downside_score),
            _score_row("Portfolio fit", row.fit_score),
        ]
    )
    body = f"""
<div class="banner">SYNTHETIC SAMPLE · Harborline Family Office · Not a recommendation to transact</div>
<p class="kicker">Investment committee screening memo · {html.escape(as_of_label)}</p>
<div class="stamp {band}">{html.escape(row.recommendation.upper())}</div>
<h1>{html.escape(row.name)}</h1>
<p class="meta">{html.escape(row.sponsor)} · {html.escape(row.asset_class)} · {html.escape(row.geography)} · {html.escape(row.stage)}</p>
<p>{html.escape(row.thesis)}</p>
<h2>Key metrics</h2>
<table>
<tr><th>Ask</th><td class="num">{money(row.ask_amount)}</td><th>Target IRR</th><td class="num">{pct(row.target_irr)}</td></tr>
<tr><th>Target MOIC</th><td class="num">{row.target_moic:.2f}x</td><th>Hold</th><td class="num">{row.hold_years} years</td></tr>
<tr><th>Sleeve exposure today</th><td class="num">{money(row.sleeve_exposure)}</td><th>Pro forma sleeve</th><td class="num">{pct(row.exposure_share)} of commitments</td></tr>
<tr><th>Sponsor track record</th><td class="num">{row.track_record_years} years</td><th>Leverage (LTV)</th><td class="num">{pct(row.leverage_ltv)}</td></tr>
<tr><th>Weighted score</th><td class="num">{row.weighted_score:.2f} / 5.00</td><th>Hard flags</th><td class="num">{row.hard_flag_count}</td></tr>
</table>
<h2>Rubric</h2>
<table>{scores}</table>
<p class="meta">Weights: sponsor 20%, market 15%, economics 20%, structure 15%, downside 15%, fit 15%. Advance is 4.00 or higher with no hard or soft flag. A hard flag is a pass. Concentration above 35% of total commitments caps the result at Watch.</p>
<h2>Red flags</h2>
<ul>{flag_html}</ul>
<h2>Questions before a sponsor call</h2>
<ul>{questions}</ul>
<p class="footer">Scores are sample analyst inputs for this exercise. The band is the published rule, not a discretion call. A person still decides whether the name goes to committee. Memo id {html.escape(row.opp_id)}.</p>
"""
    return _page(f"{row.name} screening memo", body)


def write_screening_pages(model, directory: Path, as_of_label: str) -> None:
    memo_dir = directory / "memos"
    memo_dir.mkdir(parents=True, exist_ok=True)
    links = []
    for row in model.opportunities.itertuples(index=False):
        filename = f"{row.opp_id}.html"
        (memo_dir / filename).write_text(screening_memo(row, as_of_label), encoding="utf-8")
        links.append(
            f"<tr><td><a href=\"memos/{html.escape(filename)}\">{html.escape(row.name)}</a></td>"
            f"<td>{html.escape(row.recommendation)}</td>"
            f"<td class=\"num\">{row.weighted_score:.2f}</td>"
            f"<td class=\"num\">{money(row.ask_amount)}</td></tr>"
        )
    body = f"""
<div class="banner">SYNTHETIC SAMPLE · Screening pipeline · Not a recommendation to transact</div>
<p class="kicker">Harborline Family Office · {html.escape(as_of_label)}</p>
<h1>Opportunity pipeline</h1>
<p>{model.counts['advance']} advance, {model.counts['watch']} watch, {model.counts['pass']} pass. Total ask {money(model.counts['ask_amount'])}.</p>
<table>
<tr><th>Opportunity</th><th>Band</th><th class="num">Score</th><th class="num">Ask</th></tr>
{''.join(links)}
</table>
<p class="footer">Open a memo for the rubric, flags, and questions. The Excel pipeline has the same score as a formula.</p>
"""
    (directory / "index.html").write_text(_page("Harborline screening pipeline", body), encoding="utf-8")


def monthly_report_html(operating, as_of_label: str) -> str:
    kpis = operating.kpis
    variance_class = "neg" if kpis["october_revenue_variance"] < 0 else ""
    product_rows = []
    for row in operating.october_products.itertuples(index=False):
        klass = "neg" if row.revenue_variance < 0 else ""
        product_rows.append(
            "<tr>"
            f"<td>{html.escape(row.product_line)}</td>"
            f"<td class=\"num\">{money(row.revenue)}</td>"
            f"<td class=\"num\">{money(row.revenue_budget)}</td>"
            f"<td class=\"num {klass}\">{money(row.revenue_variance)}</td>"
            f"<td class=\"num\">{money(row.gross_profit)}</td>"
            "</tr>"
        )
    opex_rows = []
    for row in operating.october_opex.itertuples(index=False):
        klass = "neg" if row.variance > 0 else ""
        opex_rows.append(
            f"<tr><td>{html.escape(row.category)}</td><td class=\"num\">{money(row.amount)}</td>"
            f"<td class=\"num\">{money(row.budget)}</td><td class=\"num {klass}\">{money(row.variance)}</td></tr>"
        )
    exceptions = []
    for row in operating.exceptions.itertuples(index=False):
        exceptions.append(
            f"<li><strong>{html.escape(row.rule_id)}</strong> {html.escape(row.source)} "
            f"{html.escape(str(row.record_id))} (source row {row.row_number}): {html.escape(row.message)}</li>"
        )
    reorder = ", ".join(html.escape(sku) for sku in kpis["skus_below_reorder"]) or "none"
    body = f"""
<div class="banner">SYNTHETIC SAMPLE · Cedar Bend Supply · Exception rows are excluded from these figures</div>
<p class="kicker">Monthly management report · {html.escape(kpis['report_month'])} · {html.escape(as_of_label)}</p>
<h1>October close</h1>
<p>Revenue is {money(abs(kpis['october_revenue_variance']))} under budget. The gross-margin rate held ({pct(kpis['october_gross_margin'])} versus {pct(kpis['october_gross_margin_budget'])} budget), so the dollar miss is volume. Operating expense is over plan. Year to date, revenue is still {money(kpis['ytd_revenue_variance'])} ahead of budget and operating income is {money(kpis['ytd_operating_income_variance'])} versus budget.</p>
<div class="cards">
  <div class="card"><div class="label">Revenue</div><div class="value">{money(kpis['october_revenue'])}</div></div>
  <div class="card"><div class="label">Versus budget</div><div class="value {variance_class}">{money(kpis['october_revenue_variance'])}</div></div>
  <div class="card"><div class="label">Operating income</div><div class="value">{money(kpis['october_operating_income'])}</div></div>
  <div class="card"><div class="label">Inventory</div><div class="value">{money(kpis['inventory_value'])}</div></div>
</div>
<h2>October by product line</h2>
<table>
<tr><th>Line</th><th class="num">Revenue</th><th class="num">Budget</th><th class="num">Variance</th><th class="num">Gross profit</th></tr>
{''.join(product_rows)}
</table>
<h2>Operating expense</h2>
<table>
<tr><th>Category</th><th class="num">Actual</th><th class="num">Budget</th><th class="num">Variance</th></tr>
{''.join(opex_rows)}
</table>
<p>Purchases were {money(kpis['october_purchases'])} against a {money(kpis['october_purchases_budget'])} budget ({money(kpis['october_purchases_variance'])}). Purchasing is cash and inventory, not the COGS line. COGS here is the standard cost ratio on valid sales.</p>
<h2>Inventory</h2>
<p>On-hand value {money(kpis['inventory_value'])}. Days on hand {kpis['days_on_hand']:.1f}, using October COGS and {kpis['days_in_report_month']} days. Below reorder: {reorder}.</p>
<h2>Rows kept out of the totals ({kpis['exception_count']})</h2>
<ul>{''.join(exceptions)}</ul>
<p class="footer">July through September sales are product-level rollups. October is invoice-level. The Excel workbook repeats this P&amp;L with SUMIFS formulas.</p>
"""
    return _page("Cedar Bend October management report", body)


def alerts_markdown(capital) -> str:
    lines = [
        "# Harborline alerts",
        "",
        "Synthetic sample. As of 12 November 2026. Status uses that date, not the day the file was generated.",
        "",
        f"- Commitments: {money(capital.totals['commitment'])}",
        f"- Called: {money(capital.totals['called'])} ({pct(capital.totals['pct_called'])})",
        f"- Unfunded: {money(capital.totals['unfunded'])}",
        f"- Overdue calls: {money(capital.totals['overdue_call_amount'])}",
        f"- Calls due within 30 days: {money(capital.totals['due_soon_call_amount'])}",
        f"- Distributions expected within 30 days: {money(capital.totals['expected_distribution_amount'])}",
        f"- Past-due distributions: {money(capital.totals['past_due_distribution_amount'])}",
        f"- Overdue fund reports: {capital.totals['overdue_deadline_count']}",
        "",
        "| Severity | Reference | Amount | What |",
        "| --- | --- | ---: | --- |",
    ]
    for row in capital.alerts.itertuples(index=False):
        amount = row.amount
        blank = amount is None or str(amount) in {"nan", "NaT", "None", "<NA>"}
        try:
            blank = blank or amount != amount
        except TypeError:
            blank = True
        lines.append(
            f"| {row.severity} | {row.ref_id} | {'' if blank else money(amount)} | {row.title} |"
        )
    lines.append("")
    return "\n".join(lines)

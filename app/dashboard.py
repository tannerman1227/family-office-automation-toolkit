"""Executive dashboard for the synthetic Harborline sample.

The page reads the same functions as the CLI. It does not call a language
model. Approving a summary writes outputs/review/decisions.json. Re-running
`python -m fotoolkit run-all` keeps that decision.
"""

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

from fotoolkit.config import OUTPUT_DIR
from fotoolkit.format_util import money, pct
from fotoolkit.pipeline import build_model, dashboard_payload
from fotoolkit.review import apply_decision, approved_tasks, load_decisions, save_decisions

PAGES = ["Overview", "Capital", "Operating", "Pipeline", "Review", "Tasks"]
DECISIONS = OUTPUT_DIR / "review" / "decisions.json"

st.set_page_config(
    page_title="Harborline Executive Dashboard",
    page_icon="H",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    [data-testid="stToolbar"] { display: none; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header[data-testid="stHeader"] { background: transparent; }
    .block-container { padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1180px; }
    .banner { background: #7a1f1f; color: white; padding: 8px 12px; font-size: 13px;
              letter-spacing: .03em; border-radius: 2px; margin-bottom: 14px; }
    .lede { font-size: 1.15rem; line-height: 1.45; color: #14242e; margin: 0 0 14px; }
    .kpi { background: white; border: 1px solid #e3dcce; border-top: 3px solid #1b3a4b;
           padding: 12px 14px 10px; min-height: 108px; }
    .kpi-label { font-size: 12px; letter-spacing: .06em; text-transform: uppercase; color: #5c5348; }
    .kpi-value { font-size: 26px; color: #1b3a4b; font-weight: 650; margin-top: 4px; line-height: 1.15; }
    .kpi-note { font-size: 13px; color: #5c5348; margin-top: 4px; }
    .section { font-size: 13px; letter-spacing: .08em; text-transform: uppercase;
               color: #1b3a4b; font-weight: 700; margin: 18px 0 6px; }
    section[data-testid="stSidebar"] { background: #14242e; }
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] label { color: #f4f1ea; }
    section[data-testid="stSidebar"] .stRadio label { color: #f4f1ea; }
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_resource(show_spinner=False)
def load_office():
    # Empty key keeps the dashboard on the rules engine even if a key is set in the shell.
    return build_model(ROOT, api_key="")


def decisions_now() -> dict:
    return load_decisions(DECISIONS)


def kpi(label: str, value: str, note: str):
    st.markdown(
        f'<div class="kpi"><div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{value}</div><div class="kpi-note">{note}</div></div>',
        unsafe_allow_html=True,
    )


COLUMN_LABELS = {
    "fund_name": "Fund",
    "called_to_date": "Called",
    "residual_irr": "Residual IRR",
    "dpi": "DPI",
    "rvpi": "RVPI",
    "tvpi": "TVPI",
    "call_id": "Call",
    "due_date": "Due",
    "dist_id": "Distribution",
    "expected_date": "Expected",
    "dist_type": "Type",
    "deadline_id": "Deadline",
    "report_name": "Report",
    "ref_id": "Reference",
    "product_line": "Product",
    "revenue_budget": "Budget",
    "revenue_variance": "Variance",
    "gross_profit": "Gross profit",
    "on_hand_qty": "On hand",
    "reorder_point": "Reorder point",
    "extended_cost": "Value",
    "rule_id": "Rule",
    "record_id": "Record",
    "row_number": "Source row",
    "task_id": "Task",
    "ask_amount": "Ask",
    "target_irr": "Target IRR",
    "weighted_score": "Score",
    "red_flags": "Flags",
    "asset_class": "Asset class",
    "due_date_key": "Due",
}


def show_table(frame: pd.DataFrame, money_columns: list[str] | None = None, percent_columns: list[str] | None = None):
    view = frame.copy()
    for column in money_columns or []:
        if column in view.columns:
            view[column] = view[column].map(lambda value: "" if pd.isna(value) else money(value))
    for column in percent_columns or []:
        if column in view.columns:
            view[column] = view[column].map(lambda value: "" if pd.isna(value) else pct(value))
    for column in view.columns:
        if view[column].dtype == object:
            view[column] = view[column].map(lambda value: value.isoformat() if hasattr(value, "isoformat") else value)
    view = view.rename(columns=lambda column: COLUMN_LABELS.get(column, column.replace("_", " ").capitalize()))
    st.dataframe(view, use_container_width=True, hide_index=True)


def page_overview(model, payload):
    capital = payload["capital"]
    operating = payload["operating"]
    pipeline = payload["pipeline"]
    review = payload["review"]
    columns = st.columns(5)
    cards = [
        ("Unfunded", money(capital["unfunded"]), f"of {money(capital['commitment'])} committed"),
        ("Overdue call", money(capital["overdue_call_amount"]), f"{capital['overdue_call_count']} notice still open"),
        ("October revenue", money(operating["october_revenue"]), f"{money(operating['october_revenue_variance'])} vs budget"),
        ("Pipeline", f"{pipeline['advance']} advance", f"{pipeline['watch']} watch · {pipeline['pass']} pass"),
        ("Awaiting review", str(review["pending"]), "Not on the task list yet"),
    ]
    for column, card in zip(columns, cards):
        with column:
            kpi(*card)
    left, right = st.columns([1.15, 1])
    with left:
        st.markdown('<div class="section">Needs a person</div>', unsafe_allow_html=True)
        alerts = model.capital.alerts[model.capital.alerts["severity"].isin(["high", "medium"])].copy()
        show_table(alerts[["severity", "ref_id", "amount", "due_date", "title"]], ["amount"])
    with right:
        st.markdown('<div class="section">Priorities</div>', unsafe_allow_html=True)
        show_table(model.priorities[["rank", "due_date", "owner", "title"]])
    with st.expander("Where these numbers come from"):
        st.markdown(
            """
- **Unfunded** is commitment minus capital called, from `data/sample/commitments.csv`.
- **Overdue** uses the pinned as-of date, 12 November 2026, not the clock on this computer.
- **October revenue** sums valid October invoices. Nine source rows failed a check and are excluded.
- **Pipeline bands** apply the published rubric to the sample scores. The scores are inputs, not a model.
- **Awaiting review** counts drafts. Approving one on the Review page is what puts its actions on the task list.
            """
        )


def page_capital(model):
    totals = model.capital.totals
    columns = st.columns(4)
    with columns[0]:
        kpi("Called", money(totals["called"]), pct(totals["pct_called"]) + " of commitments")
    largest = model.capital.commitments.sort_values("unfunded", ascending=False).iloc[0]
    with columns[1]:
        kpi("Unfunded", money(totals["unfunded"]), f"Largest is {largest.fund_name}")
    with columns[2]:
        kpi("Due in 30 days", money(totals["due_soon_call_amount"]), f"{totals['due_soon_call_count']} open notices")
    with columns[3]:
        kpi("Distributions expected", money(totals["expected_distribution_amount"]), "Within 30 days, not yet received")
    st.markdown('<div class="section">Commitments</div>', unsafe_allow_html=True)
    commitments = model.capital.commitments[
        ["fund_name", "strategy", "commitment", "called_to_date", "unfunded", "dpi", "rvpi", "tvpi", "residual_irr"]
    ].copy()
    for column in ("dpi", "rvpi", "tvpi"):
        commitments[column] = commitments[column].map(lambda value: "" if pd.isna(value) else f"{value:.2f}x")
    show_table(
        commitments,
        ["commitment", "called_to_date", "unfunded"],
        ["residual_irr"],
    )
    st.caption("Residual IRR treats NAV as if it were sold on 12 November 2026. It is a planning figure, not a partner-reported IRR. DPI, RVPI, and TVPI use called capital as the denominator.")
    left, right = st.columns(2)
    with left:
        st.markdown('<div class="section">Capital calls</div>', unsafe_allow_html=True)
        show_table(
            model.capital.calls[["call_id", "status", "due_date", "amount", "fund_name"]],
            ["amount"],
        )
    with right:
        st.markdown('<div class="section">Reporting deadlines</div>', unsafe_allow_html=True)
        show_table(
            model.capital.deadlines[["deadline_id", "status", "due_date", "report_name"]],
        )
    st.markdown('<div class="section">Distributions</div>', unsafe_allow_html=True)
    show_table(
        model.capital.distributions[["dist_id", "status", "expected_date", "amount", "fund_name"]],
        ["amount"],
    )


def page_operating(model):
    kpis = model.operating.kpis
    columns = st.columns(4)
    with columns[0]:
        kpi("October revenue", money(kpis["october_revenue"]), f"Budget {money(kpis['october_revenue_budget'])}")
    with columns[1]:
        kpi("Gross margin", pct(kpis["october_gross_margin"]), f"Budget {pct(kpis['october_gross_margin_budget'])}")
    with columns[2]:
        kpi("Operating income", money(kpis["october_operating_income"]), f"{money(kpis['october_operating_income_variance'])} vs budget")
    with columns[3]:
        kpi("Days on hand", f"{kpis['days_on_hand']:.1f}", "October COGS, 31-day month")
    st.markdown('<div class="section">Revenue and operating income, July–October</div>', unsafe_allow_html=True)
    trend = model.operating.monthly[["month", "revenue", "revenue_budget", "operating_income", "operating_income_budget"]]
    melted = trend.melt(id_vars="month", var_name="series", value_name="amount")
    import altair as alt

    chart = (
        alt.Chart(melted)
        .mark_bar()
        .encode(
            x=alt.X("month:N", title=None),
            y=alt.Y("amount:Q", title=None, axis=alt.Axis(format="$,.0f")),
            color=alt.Color(
                "series:N",
                title=None,
                scale=alt.Scale(
                    domain=["revenue", "revenue_budget", "operating_income", "operating_income_budget"],
                    range=["#1B3A4B", "#C4A35A", "#1F6B4A", "#8A5A12"],
                ),
            ),
            xOffset="series:N",
        )
        .properties(height=260)
    )
    st.altair_chart(chart, use_container_width=True)
    st.caption(
        f"Year to date revenue is {money(kpis['ytd_revenue'])} against a {money(kpis['ytd_revenue_budget'])} budget "
        f"({money(kpis['ytd_revenue_variance'])}). Year-to-date operating income is {money(kpis['ytd_operating_income'])}, "
        f"{money(kpis['ytd_operating_income_variance'])} versus budget. October is the weak month, not the year."
    )
    left, right = st.columns(2)
    with left:
        st.markdown('<div class="section">October by product</div>', unsafe_allow_html=True)
        show_table(
            model.operating.october_products[["product_line", "revenue", "revenue_budget", "revenue_variance", "gross_profit"]],
            ["revenue", "revenue_budget", "revenue_variance", "gross_profit"],
        )
    with right:
        st.markdown('<div class="section">October operating expense</div>', unsafe_allow_html=True)
        show_table(model.operating.october_opex, ["amount", "budget", "variance"])
    st.markdown('<div class="section">Purchasing and inventory</div>', unsafe_allow_html=True)
    st.write(
        f"October purchases {money(kpis['october_purchases'])} versus a {money(kpis['october_purchases_budget'])} budget. "
        "That figure is not in COGS. COGS is the standard cost on valid sales. "
        f"Inventory on hand is {money(kpis['inventory_value'])}. "
        f"Below reorder: {', '.join(kpis['skus_below_reorder'])}."
    )
    below = model.operating.inventory[model.operating.inventory["below_reorder"]]
    show_table(below[["sku", "description", "on_hand_qty", "reorder_point", "extended_cost"]], ["extended_cost"])
    st.markdown('<div class="section">Excluded rows</div>', unsafe_allow_html=True)
    show_table(model.operating.exceptions)


def page_pipeline(model):
    counts = model.screening.counts
    columns = st.columns(3)
    with columns[0]:
        kpi("Advance", str(counts["advance"]), "Score at least 4.00 and no flag")
    with columns[1]:
        kpi("Watch", str(counts["watch"]), "Between 3.20 and 4.00, or a concentration flag")
    with columns[2]:
        kpi("Pass", str(counts["pass"]), "Below 3.20 or a hard flag")
    frame = model.screening.opportunities[
        ["name", "sponsor", "asset_class", "ask_amount", "target_irr", "weighted_score", "recommendation", "red_flags"]
    ].copy()
    frame["red_flags"] = frame["red_flags"].map(lambda flags: " | ".join(flags) if flags else "—")
    show_table(frame, ["ask_amount"], ["target_irr"])
    st.caption("Open the one-page memos in outputs/screening/memos after `python -m fotoolkit run-all`. The Excel file repeats the weighted score as a formula against the Weights sheet.")


def page_review(model, decisions):
    payload = dashboard_payload(model, decisions)
    pending = [item for item in payload["queue"] if item["review_status"] == "pending"]
    settled = [item for item in payload["queue"] if item["review_status"] != "pending"]
    st.write(
        "These drafts are not tasks. The rules engine only promotes lines that start with ACTION, "
        "and sentences of the form “Name will … by YYYY-MM-DD.” A request buried in a paragraph stays in the summary "
        "so a person can add it. Nothing here calls a model unless you run the CLI with an API key, and even then the result waits in this queue."
    )
    if not pending:
        st.success("The queue is clear.")
    for item in pending:
        with st.container(border=True):
            st.markdown(f"**{item['title']}**")
            st.caption(f"{item['source']} · {item['method']}")
            st.write(item["summary"])
            if item["decisions"]:
                st.markdown("Decisions")
                for decision in item["decisions"]:
                    st.markdown(f"- {decision}")
            if item["action_items"]:
                show_table(pd.DataFrame(item["action_items"]))
            note = st.text_input("Note for the file", key=f"note-{item['id']}", placeholder="Optional")
            approve, reject = st.columns(2)
            with approve:
                if st.button("Approve and add to tasks", key=f"yes-{item['id']}", type="primary"):
                    updated = apply_decision(decisions, item["id"], "approved", note, date.today().isoformat())
                    save_decisions(DECISIONS, updated)
                    st.rerun()
            with reject:
                if st.button("Reject", key=f"no-{item['id']}"):
                    updated = apply_decision(decisions, item["id"], "rejected", note, date.today().isoformat())
                    save_decisions(DECISIONS, updated)
                    st.rerun()
    if settled:
        st.markdown('<div class="section">Already decided</div>', unsafe_allow_html=True)
        for item in settled:
            st.markdown(f"**{item['review_status'].title()}** · {item['title']}")
            if item["review_note"]:
                st.caption(item["review_note"])


def page_tasks(model, decisions):
    ai_tasks = approved_tasks(model.queue, decisions)
    st.markdown('<div class="section">Priorities for the principal</div>', unsafe_allow_html=True)
    show_table(model.priorities)
    st.markdown('<div class="section">Operating follow-ups</div>', unsafe_allow_html=True)
    show_table(model.tasks)
    st.markdown('<div class="section">From approved summaries</div>', unsafe_allow_html=True)
    if not ai_tasks:
        pending = dashboard_payload(model, decisions)["review"]["pending"]
        st.info(f"None yet. {pending} draft(s) are still in review, so their action lines are not tasks.")
    else:
        show_table(pd.DataFrame(ai_tasks)[["task_id", "title", "owner", "due_date", "status", "source"]])


def main():
    model = load_office()
    decisions = decisions_now()
    payload = dashboard_payload(model, decisions)
    if "page" not in st.session_state:
        requested = st.query_params.get("page", "Overview")
        if isinstance(requested, list):
            requested = requested[0] if requested else "Overview"
        st.session_state.page = requested if requested in PAGES else "Overview"

    st.sidebar.markdown("**Harborline**")
    st.sidebar.caption("Family office toolkit")
    st.sidebar.radio("Navigate", PAGES, key="page")
    if st.query_params.get("page") != st.session_state.page:
        st.query_params["page"] = st.session_state.page
    st.sidebar.markdown("---")
    st.sidebar.caption("As of 12 November 2026")
    st.sidebar.caption(f"{payload['review']['pending']} drafts waiting")
    st.sidebar.caption("Rules engine · offline")

    st.markdown(
        '<div class="banner">SYNTHETIC DATA · Harborline Family Office and Cedar Bend Supply are fictional · Not an instruction to fund, invest, or pay</div>',
        unsafe_allow_html=True,
    )
    st.markdown(f"### {st.session_state.page}")
    st.markdown(f'<p class="lede">{payload["lede"]}</p>', unsafe_allow_html=True)

    page = st.session_state.page
    if page == "Overview":
        page_overview(model, payload)
    elif page == "Capital":
        page_capital(model)
    elif page == "Operating":
        page_operating(model)
    elif page == "Pipeline":
        page_pipeline(model)
    elif page == "Review":
        page_review(model, decisions)
    else:
        page_tasks(model, decisions)


main()

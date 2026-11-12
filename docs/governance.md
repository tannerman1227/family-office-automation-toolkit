# Governance

This note is the operating manual for the toolkit: what it is allowed to see, who owns it, how it is kept, and where it stops.

## Data in this repository

Every file under `data/sample` is synthetic. Harborline Family Office, Cedar Bend Supply, the funds, the customers, the vendors, and the people named in the notes are fictional. There are no account numbers, tax ids, or bank details. The as-of date is pinned at 12 November 2026 so a result does not change because the laptop clock moved.

Do not replace the sample with a real extract and commit it. A real drop belongs outside git, in a folder listed in `.gitignore`, on a machine the family controls.

## If this pattern is used on real records

| Rule | Why |
| --- | --- |
| Process files locally. The default summarizer makes no network call. | Meeting notes and capital-call amounts are confidential. |
| An API key is read from `FOTOOLKIT_LLM_API_KEY` and is never written to disk or to the repo. | A key in a commit is a leaked credential. |
| Leave the key unset unless the family has agreed, in writing, that those notes may be sent to that provider. | The optional model path sends the note text to the endpoint in `FOTOOLKIT_LLM_BASE_URL`. |
| Draft summaries do not become tasks until a person approves them in the dashboard. | The rules engine misses implied requests, and a model can mis-state a decision. |
| Keep approval notes out of git if they ever contain real content. `outputs/review/decisions.json` in this repo is an empty object. | The file is the audit trail. On real data it is an operational file, not source code. |
| SharePoint permissions, if the designs in `docs/power-automate-design.md` are built, should follow role: principal, CIO, controller, operating-company GM, analyst. | The flow designs assume the tenant owner sets those groups. This repo cannot. |

The Streamlit app has no login. It is a local view of local files. It is not a multi-user system and it should not be exposed to the internet.

## Who owns the solution

| Piece | Owner | What they are responsible for |
| --- | --- | --- |
| This repository: rules, tests, Excel formulas, sample data | The analyst | The business rules match what leadership asked for, the tests still pass, and a figure can be traced to a source row. |
| Microsoft 365 tenant, SharePoint sites, Power Automate connections, Power BI workspace | The company's IT or whoever holds tenant admin | Identity, permissions, connectors, and retention. Nothing in this repo is deployed there. |
| A published Power BI report | Whoever builds it from `docs/power-bi-guide.md` | The guide is a spec. There is no `.pbix` in the repo. |
| The decision to fund, invest, or pay | The person in that seat | The toolkit prepares the page. It does not sign. |

If a formula and a narrative disagree, the formula and the test win, and the narrative gets corrected. `tests/` locks the sample totals for that reason.

## Maintenance

- The as-of date lives in `fotoolkit/config.py`. Changing it changes which items are overdue. Change it on purpose, then run `pytest` and `python -m fotoolkit run-all`.
- A new fund needs a commitment row and cash flows that tie: contributions equal called-to-date, and distributions received equal distributions-to-date. The capital loader raises an alert when they do not.
- A new screening name is a row in `opportunities.csv`. Scores are entered by an analyst on the 1–5 scale. The toolkit applies the weights. It does not invent the scores.
- Each month, replace the operating extracts, run the toolkit, and clear the exception log before the review meeting. Nine planted rows in the sample are there so that step is visible.
- Human decisions survive a rerun when the draft id still matches. Editing the source note changes the id, and the old decision is dropped on the next `run-all`. That is intentional: the approval was of that text.

## Limitations

- This is not a system of record. The commitment ledger, the broker, and the accounting system remain the sources. The toolkit reads copies.
- This is not investment advice and not an instruction to wire funds. Screening bands are a sort order for a meeting.
- Residual-value IRR treats NAV as if it were sold on the as-of date. It will not match a general partner's reported net IRR. DPI, RVPI, and TVPI use called capital as the denominator and ignore the timing of cash, which is why IRR is shown beside them.
- COGS is a standard ratio on valid sales. Purchasing is reported next to the P&L and is not the COGS line. July through September sales are product-level rollups; October is invoice-level.
- The concentration flag uses the `sleeve_exposure` figure on the opportunity row. It does not infer the sleeve by matching strategy names.
- The rules engine only creates action items from lines that start with `ACTION:` and from sentences of the form "Name will … by YYYY-MM-DD." A request written as ordinary prose stays in the summary. That is a limitation, and it is why a person reviews the draft.
- If a model is called, a failed call falls back to the rules engine and labels the method `rules_fallback`. The draft is still unapproved.
- The dashboard does not lock `decisions.json`. Two people clicking Approve at once can overwrite each other. For a real office, that file would move to a list with item-level permissions.
- Power Automate, Power Apps, and the SharePoint lists are designs. They are not running. Power BI is a folder of tidy tables and a build guide, not a published report.
- Time savings in `docs/workflows.md` are illustrative counts for the fictional processes.

## Adoption

Ship one workflow at a time, in this order: the capital-call tracker, then the monthly report, then screening memos. Keep the old spreadsheet for one close and tie the totals before retiring it. The exception log is the adoption tool. If people trust that bad rows are named, they will use the page. If the first report hides a bad row inside a total, they will go back to the export.

The analyst should sit with the controller for that first close, not send a link and leave.

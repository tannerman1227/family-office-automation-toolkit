# Sample data (synthetic)

Harborline Family Office and Cedar Bend Supply are fictional. Nothing in this folder is a real client, fund, invoice, or person. The as-of date used by the toolkit is **12 November 2026**.

| File | Grain | What it is |
| --- | --- | --- |
| `commitments.csv` | One row per fund | Signed commitment, capital called to date, distributions received, and NAV |
| `cashflows.csv` | One row per historical cash movement | Contributions (negative) and distributions (positive). Contributions sum to `called_to_date`. Received distributions sum to `distributions_to_date` |
| `capital_calls.csv` | One row per notice | Open and paid calls. Open calls are not included in `called_to_date` |
| `distributions.csv` | One row per distribution notice | Received and still-expected distributions |
| `reporting_deadlines.csv` | One row per report due | Quarterly reporting calendar |
| `opportunities.csv` | One row per deal in the pipeline | Screening inputs. Scores are sample judgments on a 1–5 scale, not model output |
| `sales.csv` | July–September: one row per product line (monthly rollup). October: one row per invoice, plus planted bad rows | Cedar Bend revenue |
| `purchasing.csv` | July–September: one receipt per month. October: purchase orders, plus planted bad rows | Cedar Bend purchasing |
| `inventory.csv` | One row per SKU, snapshot at the as-of date | On-hand units, cost, reorder point. One planted negative count |
| `revenue_budget.csv` | Month × product line | Revenue and COGS budget |
| `opex.csv` | Month × category | Actual operating expenses |
| `opex_budget.csv` | Month × category | Operating-expense budget |
| `purchasing_budget.csv` | Month | Purchasing budget |
| `product_costs.csv` | Product line | Standard COGS ratio applied to valid sales |
| `priorities.csv` | One row per principal priority | Hand-authored operating list, not AI output |
| `tasks.csv` | One row per follow-up | Hand-authored task list |
| `notes/` | One file per meeting or email | Source text for the summarizer |

## Planted data-quality problems

These rows are intentional. The management-report job should flag them and keep them out of KPIs.

| Record | Problem |
| --- | --- |
| `NEG-01` | Negative sales amount |
| `DUP-01` (two rows) | Duplicate invoice id |
| `BAD-DATE` | Invoice date outside the July–October 2026 window |
| `MISS-PROD` | Missing product line |
| `MISMATCH` | Quantity × unit price does not equal the amount |
| `PO-NEG` | Negative purchase amount |
| `PO-BLANK` | Missing vendor |
| `SKU-NEG` | Negative on-hand quantity |

July through September sales are product-level rollups, so those months show the trend without pretending every historical invoice was typed in. October is invoice-level because that is the month the report closes.

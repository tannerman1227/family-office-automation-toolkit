-- Run against outputs/harborline.sqlite after python -m fotoolkit run-all.
-- The figures below are what the synthetic sample produces on 12 November 2026.

-- Overdue capital calls. Expect one row, CC-1041, amount 400000.
SELECT c.call_id, f.fund_name, c.amount, c.status
FROM fact_capital_call AS c
JOIN dim_fund AS f ON f.fund_key = c.fund_key
WHERE c.status = 'Overdue';

-- Unfunded by fund, largest first. Pecan Growth Equity IV is 2100000 of 8150000.
SELECT f.fund_name, c.unfunded, c.tvpi, c.residual_irr
FROM fact_commitment AS c
JOIN dim_fund AS f ON f.fund_key = c.fund_key
ORDER BY c.unfunded DESC;

-- October revenue from valid invoices only. Expect 462000.
SELECT SUM(amount) AS october_revenue
FROM fact_sales
WHERE month = '2026-10';

-- Rows the management report refused.
SELECT source, rule_id, record_id, message
FROM fact_exception
ORDER BY source, rule_id;

-- Screening bands.
SELECT d.name, f.recommendation, f.weighted_score, f.ask_amount, f.red_flags
FROM fact_opportunity AS f
JOIN dim_opportunity AS d ON d.opportunity_key = f.opportunity_key
ORDER BY f.weighted_score DESC;

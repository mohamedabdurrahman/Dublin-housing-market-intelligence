-- Production model for a curated Dublin housing fact table.
-- Expected source columns:
--   local_authority, period, completions, planning_permissions, price_index
-- Dialect: PostgreSQL-compatible SQL.

WITH quarterly AS (
    SELECT
        local_authority,
        CAST(SUBSTRING(period FROM 1 FOR 4) AS INTEGER) AS calendar_year,
        CAST(SUBSTRING(period FROM 6 FOR 1) AS INTEGER) AS quarter_number,
        completions,
        planning_permissions,
        price_index
    FROM dublin_housing_summary
    WHERE CAST(SUBSTRING(period FROM 1 FOR 4) AS INTEGER) BETWEEN 2020 AND 2026
),
annual_authority AS (
    SELECT
        local_authority,
        calendar_year,
        SUM(completions) AS annual_completions,
        SUM(planning_permissions) AS annual_planning_permissions,
        AVG(price_index) AS average_price_index
    FROM quarterly
    GROUP BY local_authority, calendar_year
),
with_lag AS (
    SELECT
        annual_authority.*,
        LAG(annual_completions) OVER (
            PARTITION BY local_authority ORDER BY calendar_year
        ) AS prior_year_completions,
        LAG(annual_planning_permissions) OVER (
            PARTITION BY local_authority ORDER BY calendar_year
        ) AS prior_year_planning_permissions
    FROM annual_authority
),
with_growth AS (
    SELECT
        with_lag.*,
        CASE
            WHEN prior_year_completions IS NULL
              OR prior_year_completions = 0 THEN NULL
            ELSE 100.0 * (annual_completions - prior_year_completions)
                 / prior_year_completions
        END AS completion_growth_yoy_pct,
        CASE
            WHEN prior_year_planning_permissions IS NULL
              OR prior_year_planning_permissions = 0 THEN NULL
            ELSE 100.0 * (annual_planning_permissions - prior_year_planning_permissions)
                 / prior_year_planning_permissions
        END AS planning_growth_yoy_pct
    FROM with_lag
),
annual_totals AS (
    SELECT
        calendar_year,
        SUM(annual_completions) AS total_dublin_completions
    FROM annual_authority
    GROUP BY calendar_year
)
SELECT
    growth.local_authority,
    growth.calendar_year,
    growth.annual_completions,
    growth.annual_planning_permissions,
    growth.average_price_index,
    growth.prior_year_completions,
    growth.completion_growth_yoy_pct,
    growth.planning_growth_yoy_pct,
    totals.total_dublin_completions,
    100.0 * growth.annual_completions
        / NULLIF(totals.total_dublin_completions, 0) AS delivery_share_pct
FROM with_growth AS growth
JOIN annual_totals AS totals USING (calendar_year)
ORDER BY growth.calendar_year, growth.local_authority;

-- Optional QA check: one row per authority and year.
-- SELECT local_authority, calendar_year, COUNT(*)
-- FROM annual_authority
-- GROUP BY local_authority, calendar_year
-- HAVING COUNT(*) > 1;
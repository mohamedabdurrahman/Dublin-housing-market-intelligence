-- Annual analytical table for the four Dublin local authorities.
-- DuckDB reads the quarterly CSV directly and keeps the model bounded to 2020-2026.

WITH filtered_base AS (
    SELECT
        local_authority,
        CAST(SUBSTRING(period, 1, 4) AS INTEGER) AS calendar_year,
        CAST(completions AS DOUBLE) AS completions,
        CAST(planning_permissions AS DOUBLE) AS planning_permissions,
        CAST(price_index AS DOUBLE) AS price_index
    FROM read_csv_auto('data/dublin_housing_summary.csv', HEADER = TRUE)
    WHERE CAST(SUBSTRING(period, 1, 4) AS INTEGER) BETWEEN 2020 AND 2026
      AND local_authority IN ('Dublin City', 'Fingal', 'South Dublin', 'Dún Laoghaire-Rathdown')
),
annual_totals AS (
    SELECT calendar_year, local_authority,
        SUM(COALESCE(completions, 0)) AS completions,
        SUM(COALESCE(planning_permissions, 0)) AS planning_permissions,
        AVG(price_index) AS average_price_index
    FROM filtered_base
    GROUP BY calendar_year, local_authority
),
dublin_wide_totals AS (
    SELECT annual_totals.*,
        SUM(completions) OVER (PARTITION BY calendar_year) AS total_dublin_completions
    FROM annual_totals
),
metrics_calculation AS (
    SELECT dublin_wide_totals.*,
        LAG(completions, 1) OVER (PARTITION BY local_authority ORDER BY calendar_year)
            AS prior_year_completions,
        (completions - LAG(completions, 1) OVER (PARTITION BY local_authority ORDER BY calendar_year))
            / NULLIF(LAG(completions, 1) OVER (PARTITION BY local_authority ORDER BY calendar_year), 0)
            AS completion_yoy_growth,
        completions / NULLIF(total_dublin_completions, 0) AS delivery_share,
        LAG(planning_permissions, 2) OVER (PARTITION BY local_authority ORDER BY calendar_year)
            / NULLIF(completions, 0) AS lead_time_gap_ratio
    FROM dublin_wide_totals
)
SELECT local_authority, calendar_year,
    COALESCE(completions, 0) AS completions,
    COALESCE(planning_permissions, 0) AS planning_permissions,
    COALESCE(average_price_index, 0) AS average_price_index,
    COALESCE(total_dublin_completions, 0) AS total_dublin_completions,
    COALESCE(prior_year_completions, 0) AS prior_year_completions,
    COALESCE(completion_yoy_growth, 0) AS completion_yoy_growth,
    COALESCE(delivery_share, 0) AS delivery_share,
    COALESCE(lead_time_gap_ratio, 0) AS lead_time_gap_ratio
FROM metrics_calculation
ORDER BY calendar_year, local_authority;
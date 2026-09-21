# Power BI Executive Dashboard Layout

## Model Contract

Use `data/fact_housing_transformed.csv` (generated via `process_housing_data.py`) as the primary analytical dataset. Relate `Dim_Date[calendar_year]` to `calendar_year` and join `dim_infrastructure_risk` via `local_authority`. Retain `local_authority` as the primary geography. The core measures are completions, planning permissions (planning grants), completion YoY growth, delivery share, and the permissions-to-completions lead-time proxy.

## Page 1: Executive KPI Overview

Purpose: give senior decision-makers a fast read on supply delivery and forward pipeline.

- KPI cards: latest completions, Total Planning Grants, completion YoY growth, and four-authority delivery share.
- Line chart: annual completions versus planning permissions (2020–2026), with a slicer for authority.
- Column chart: annual completions by local authority, sorted descending.
- Small narrative panel: explain that permissions are an upstream signal and completions follow after design, finance, procurement, construction, and certification.
- Slicers: reporting year, local authority, and quarter.

## Page 2: Local Authority Conversion Lags

Purpose: compare how quickly the planning pipeline appears to convert into delivered homes.

- Matrix: authority by year showing planning permissions, completions, completion YoY growth, and delivery share.
- Scatter plot: annual planning permissions on the x-axis and completions on the y-axis; bubble size is delivery share and colour is local authority.
- Small-multiple lines: permissions and completions for each authority.
- Tooltip fields: prior-year completions, YoY growth, price index, and latest available quarter.
- Interpretation note: this is an indicative pipeline relationship, not a project-level construction lead-time measure.

## Page 3: Infrastructure Bottleneck Heatmap

Purpose: connect delivery performance to infrastructure-readiness risks for investment and policy discussions.

- Heatmap rows: local authorities; columns: year, completion growth, delivery share, and permissions-to-completions gap.
- Conditional formatting: red for deteriorating delivery or widening gaps, amber for mixed signals, green for improving delivery.
- Overlay callouts: water-treatment capacity and electrical-grid connection risk areas, especially Fingal and South Dublin.
- Drill-through: authority detail with the quarterly trend, latest KPIs, and policy-risk notes.
- Disclaimer: infrastructure risks are policy hypotheses and require validation against Uisce Éireann and ESB project-level connection data.

## Interaction Rules

- Cross-filter all visuals by authority and year.
- Keep the executive page uncluttered; move diagnostic detail to Pages 2 and 3.
- Show data refresh date and CSO source cube codes in the footer.
- Use a consistent Dublin authority colour mapping across all pages.

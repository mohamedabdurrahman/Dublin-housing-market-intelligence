"""Transform Dublin housing data and write Power BI CSV tables."""

from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
SQL_PATH = ROOT / "transform_housing_data.sql"

RISK_ROWS = [
    {"local_authority": "Dublin City", "water_connection_risk": "Medium", "grid_connection_risk": "Medium"},
    {"local_authority": "Fingal", "water_connection_risk": "High", "grid_connection_risk": "High"},
    {"local_authority": "South Dublin", "water_connection_risk": "High", "grid_connection_risk": "Medium"},
    {"local_authority": "Dún Laoghaire-Rathdown", "water_connection_risk": "Medium", "grid_connection_risk": "Low"},
]


def main() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    connection = duckdb.connect()
    try:
        transformed = connection.execute(SQL_PATH.read_text(encoding="utf-8")).fetchdf()
    finally:
        connection.close()

    transformed.to_csv(DATA_DIR / "fact_housing_transformed.csv", index=False)
    pd.DataFrame(RISK_ROWS).to_csv(DATA_DIR / "dim_infrastructure_risk.csv", index=False)
    print(f"Wrote {len(transformed):,} rows to {DATA_DIR / 'fact_housing_transformed.csv'}")
    print(f"Wrote {len(RISK_ROWS):,} rows to {DATA_DIR / 'dim_infrastructure_risk.csv'}")


if __name__ == "__main__":
    main()
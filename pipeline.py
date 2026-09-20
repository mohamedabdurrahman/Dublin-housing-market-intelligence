"""Build a Dublin housing market summary from CSO PxStat datasets."""

from __future__ import annotations

import io
import json
import os
from itertools import product
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
ASSETS_DIR = ROOT / "assets"
API_ROOT = os.getenv(
    "CSO_API_ROOT",
    "https://ws.cso.ie/public/api.restful/PxStat.Data.Cube_API.ReadDataset",
)
START_YEAR = 2020
END_YEAR = 2026

def canonical_authority(value: str) -> str | None:
    key = value.strip().lower()
    if "dublin city" in key:
        return "Dublin City"
    if "south dublin" in key:
        return "South Dublin"
    if "fingal" in key:
        return "Fingal"
    if "laoghaire" in key and "rathdown" in key:
        return "Dún Laoghaire-Rathdown"
    return None


def _category_values(category: dict[str, Any]) -> list[str]:
    labels = category.get("label", {})
    index = category.get("index", {})
    if isinstance(index, dict):
        keys = [key for key, _ in sorted(index.items(), key=lambda item: item[1])]
    elif isinstance(index, list):
        keys = index
    else:
        keys = list(labels)
    return [str(labels.get(key, key)) for key in keys]


def jsonstat_to_frame(payload: dict[str, Any]) -> pd.DataFrame:
    """Convert JSON-stat 1 or 2 data into a tidy dataframe."""
    dimensions = payload["id"]
    sizes = payload["size"]
    categories = [
        _category_values(payload["dimension"][dimension]["category"])
        for dimension in dimensions
    ]
    values = payload.get("value", [])
    rows = []
    for position, coordinates in enumerate(product(*categories)):
        row = dict(zip(dimensions, coordinates))
        row["value"] = values[position] if position < len(values) else None
        rows.append(row)
    frame = pd.DataFrame(rows)
    expected_rows = 1
    for size in sizes:
        expected_rows *= size
    if len(frame) != expected_rows:
        raise ValueError("CSO JSON-stat dimensions and values have different sizes")
    return frame


def fetch_dataset(dataset_code: str) -> pd.DataFrame:
    """Fetch a PxStat dataset, accepting JSON-stat or CSV responses."""
    response_urls = (
        f"{API_ROOT}/{dataset_code}/JSON-stat/1.0/en",
        f"{API_ROOT}/{dataset_code}/CSV/1.0/en",
        f"{API_ROOT}/JSON-stat/{dataset_code}",
        f"{API_ROOT}/CSV/{dataset_code}",
    )
    errors = []
    for url in response_urls:
        try:
            response = requests.get(url, timeout=60)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "").lower()
            if "json" in content_type or response.text.lstrip().startswith("{"):
                return jsonstat_to_frame(response.json())
            return pd.read_csv(io.StringIO(response.text))
        except (requests.RequestException, ValueError, KeyError) as error:
            errors.append(f"{url}: {error}")
    raise RuntimeError(
        f"Could not download CSO dataset {dataset_code}. Tried JSON-stat and CSV.\n"
        + "\n".join(errors)
    )


def _find_column(frame: pd.DataFrame, aliases: tuple[str, ...]) -> str:
    normalized = {
        str(column).strip().lower().replace("_", " "): column
        for column in frame.columns
    }
    for alias in aliases:
        for candidate, original in normalized.items():
            if alias in candidate:
                return original
    raise KeyError(f"Could not find a column matching {aliases}; got {list(frame.columns)}")


def tidy_metric(
    frame: pd.DataFrame, metric: str, authority_required: bool = True
) -> pd.DataFrame:
    frame = frame.rename(
        columns=lambda column: str(column).lstrip("\ufeff").strip()
    )
    try:
        authority_column = _find_column(
            frame, ("local authority", "county", "administrative area", "area")
        )
    except KeyError:
        if authority_required:
            raise
        authority_column = None
    time_column = _find_column(
        frame, ("quarter", "month", "year", "period", "time")
    )
    value_column = next(
        (column for column in frame.columns if str(column).lower() == "value"),
        None,
    )
    if value_column is None:
        value_column = _find_column(
            frame, ("number", "count", "price", "amount", "total")
        )
    rename_columns = {time_column: "period", value_column: metric}
    if authority_column is not None:
        rename_columns[authority_column] = "local_authority"
    tidy = frame.rename(columns=rename_columns)[
        (["local_authority"] if authority_column is not None else [])
        + ["period", metric]
    ].copy()
    if authority_column is not None:
        tidy["authority_key"] = (
            tidy["local_authority"].astype(str).str.strip().str.lower()
        )
        tidy["local_authority"] = tidy["local_authority"].map(canonical_authority)
        tidy = tidy.dropna(subset=["local_authority"])
    else:
        tidy["local_authority"] = "Dublin-wide"
    tidy[metric] = pd.to_numeric(
        tidy[metric].astype(str).str.replace(",", "", regex=False), errors="coerce"
    )
    tidy["period"] = tidy["period"].astype(str).str.strip()
    month_parts = tidy["period"].str.extract(r"^(\d{4})M(\d{1,2})$")
    month_mask = month_parts[0].notna()
    tidy.loc[month_mask, "period"] = (
        month_parts.loc[month_mask, 0]
        + "Q"
        + ((month_parts.loc[month_mask, 1].astype(int) - 1) // 3 + 1).astype(str)
    )
    named_months = pd.to_datetime(tidy["period"], format="%Y %B", errors="coerce")
    named_month_mask = named_months.notna()
    tidy.loc[named_month_mask, "period"] = (
        named_months.loc[named_month_mask].dt.year.astype(str)
        + "Q"
        + named_months.loc[named_month_mask].dt.quarter.astype(str)
    )
    return tidy.drop(columns=["authority_key"], errors="ignore").groupby(
        ["local_authority", "period"], as_index=False
    )[metric].sum(min_count=1)


def build_summary() -> pd.DataFrame:
    completions = tidy_metric(fetch_dataset("NDQ06"), "completions")
    price_frame = fetch_dataset("HPM06")
    price_type_column = _find_column(price_frame, ("type of residential property",))
    price_frame = price_frame[
        price_frame[price_type_column].astype(str).str.contains(
            "Dublin City|Fingal|South Dublin|Laoghaire|Rathdown",
            case=False,
            regex=True,
        )
    ]
    prices = tidy_metric(
        price_frame, "price_index", authority_required=False
    ).groupby("period", as_index=False)["price_index"].median()
    permissions = tidy_metric(fetch_dataset("BHQ12"), "planning_permissions")
    summary = completions.merge(
        permissions, on=["local_authority", "period"], how="outer"
    ).merge(prices, on="period", how="left")
    summary["year"] = pd.to_numeric(
        summary["period"].str.extract(r"^(\d{4})")[0], errors="coerce"
    )
    summary = summary[summary["year"].between(START_YEAR, END_YEAR)].drop(
        columns="year"
    )
    return summary.sort_values(["period", "local_authority"]).reset_index(drop=True)


def save_outputs(summary: pd.DataFrame) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    ASSETS_DIR.mkdir(exist_ok=True)
    summary.to_csv(DATA_DIR / "dublin_housing_summary.csv", index=False)
    trends = summary.groupby("period", as_index=False)[
        ["completions", "planning_permissions"]
    ].sum(min_count=1).sort_values("period")
    fig, axis = plt.subplots(figsize=(11, 6), dpi=300)
    quarter_positions = range(len(trends))
    axis.plot(
        quarter_positions,
        trends["completions"],
        color="#005A9C",
        linewidth=2.2,
        marker="o",
        label="Completions",
    )
    axis.plot(
        quarter_positions,
        trends["planning_permissions"],
        color="#E65100",
        linewidth=2.2,
        marker="o",
        label="Planning permissions",
    )
    tick_positions = list(range(0, len(trends), 2))
    axis.set_xticks(tick_positions, trends["period"].iloc[tick_positions], rotation=0)
    axis.set_title("Dublin housing pipeline: permissions and completions")
    axis.set_xlabel("CSO reporting period")
    axis.set_ylabel("Units")
    axis.grid(axis="y", alpha=0.25, linewidth=0.8)
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    axis.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(
        ASSETS_DIR / "dublin_housing_trends.png", dpi=300, bbox_inches="tight"
    )
    plt.close(fig)


def main() -> None:
    summary = build_summary()
    save_outputs(summary)
    print(
        f"Wrote {len(summary):,} rows for {START_YEAR}-{END_YEAR} to "
        f"{DATA_DIR / 'dublin_housing_summary.csv'}"
    )
    print(f"Wrote chart to {ASSETS_DIR / 'dublin_housing_trends.png'}")


if __name__ == "__main__":
    main()

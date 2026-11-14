
"""
NASA Space Apps Challenge 2026
Global Two-City Comparison Module

Compare any two cities from the configured NASA dataset.
Historical period: 1981-2025
Future projections: 2026-2035
"""

import re
from pathlib import Path

import pandas as pd

from config import (
    CITIES,
    PROCESSED_DIR,
    OUTPUT_DIR
)


# ============================================================
# 1. SETTINGS
# ============================================================

VARIABLES = [
    "precipitation",
    "soil_moisture"
]

MIN_VALID_MONTHS = 9

COMPARISON_DIR = OUTPUT_DIR / "city_comparisons"


# ============================================================
# 2. CITY NAME VALIDATION
# ============================================================

def get_city_name(user_city):

    city_lookup = {
        str(location["city"]).strip().casefold(): str(location["city"]).strip()
        for location in CITIES
    }

    requested = str(user_city).strip().casefold()

    if requested not in city_lookup:
        available = ", ".join(city_lookup.values())

        raise ValueError(
            f"City '{user_city}' is not available. "
            f"Available cities: {available}"
        )

    return city_lookup[requested]


# ============================================================
# 3. LOAD HISTORICAL DATA
# ============================================================

def load_city_data(city):

    file_path = (
        PROCESSED_DIR / f"{city.lower()}_cleaned.csv"
    )

    if not file_path.exists():
        raise FileNotFoundError(
            f"Cleaned data not found for {city}: {file_path}"
        )

    df = pd.read_csv(file_path)

    required_columns = [
        "date",
        "precipitation",
        "soil_moisture"
    ]

    missing = [
        col for col in required_columns
        if col not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing columns for {city}: {missing}"
        )

    df["date"] = pd.to_datetime(
        df["date"],
        errors="coerce"
    )

    for variable in VARIABLES:
        df[variable] = pd.to_numeric(
            df[variable],
            errors="coerce"
        )

    df = df.dropna(subset=["date"])

    df["date"] = (
        df["date"].dt.to_period("M").dt.to_timestamp()
    )

    df = df.sort_values("date")

    df = df.drop_duplicates(
        subset=["date"],
        keep="first"
    )

    return df


# ============================================================
# 4. MONTHLY COMPARISON
# ============================================================

def create_monthly_comparison(
    city1,
    city2,
    df1,
    df2
):

    first = df1[
        ["date"] + VARIABLES
    ].copy()

    second = df2[
        ["date"] + VARIABLES
    ].copy()

    first = first.rename(
        columns={
            variable: f"{city1}_{variable}"
            for variable in VARIABLES
        }
    )

    second = second.rename(
        columns={
            variable: f"{city2}_{variable}"
            for variable in VARIABLES
        }
    )

    comparison = pd.merge(
        first,
        second,
        on="date",
        how="outer"
    )

    comparison = comparison.sort_values("date")

    return comparison.reset_index(drop=True)


# ============================================================
# 5. ANNUAL COMPARISON
# ============================================================

def calculate_annual_comparison(
    city1,
    city2,
    df1,
    df2
):

    def annual_average(df, city):

        data = df.copy()

        data["year"] = data["date"].dt.year

        annual = (
            data.groupby("year")[VARIABLES]
            .agg(["mean", "count"])
        )

        records = []

        for year in annual.index:

            record = {
                "year": year,
                "city": city
            }

            for variable in VARIABLES:

                valid_months = annual.loc[
                    year, (variable, "count")
                ]

                average = annual.loc[
                    year, (variable, "mean")
                ]

                record[variable] = (
                    average
                    if valid_months >= MIN_VALID_MONTHS
                    else float("nan")
                )

                record[f"{variable}_valid_months"] = int(
                    valid_months
                )

            records.append(record)

        return pd.DataFrame(records)

    first = annual_average(df1, city1)
    second = annual_average(df2, city2)

    first = first.drop(columns="city").rename(
        columns={
            variable: f"{city1}_{variable}"
            for variable in VARIABLES
        }
    )

    second = second.drop(columns="city").rename(
        columns={
            variable: f"{city2}_{variable}"
            for variable in VARIABLES
        }
    )

    return pd.merge(
        first,
        second,
        on="year",
        how="outer"
    ).sort_values("year").reset_index(drop=True)


# ============================================================
# 6. TREND COMPARISON
# ============================================================

def load_trend_comparison(city1, city2):

    trend_file = (
        OUTPUT_DIR / "all_cities_trend_results.csv"
    )

    if not trend_file.exists():
        raise FileNotFoundError(
            f"Trend results not found: {trend_file}"
        )

    trends = pd.read_csv(trend_file)

    required = [
        "city",
        "variable",
        "trend",
        "significant",
        "mk_p_value",
        "sen_slope",
        "pct_per_decade"
    ]

    missing = [
        col for col in required
        if col not in trends.columns
    ]

    if missing:
        raise ValueError(
            f"Missing trend columns: {missing}"
        )

    selected = trends[
        trends["city"].astype(str).str.casefold().isin(
            [city1.casefold(), city2.casefold()]
        )
    ].copy()

    selected["city"] = selected["city"].astype(str)

    selected = selected[
        selected["city"].str.casefold().isin(
            [city1.casefold(), city2.casefold()]
        )
    ]

    return selected.reset_index(drop=True)


# ============================================================
# 7. FUTURE FORECAST COMPARISON
# ============================================================

def load_forecast_comparison(city1, city2):

    forecast_file = (
        OUTPUT_DIR / "monthly_10_year_forecasts.csv"
    )

    if not forecast_file.exists():
        raise FileNotFoundError(
            f"Monthly forecasts not found: {forecast_file}"
        )

    forecasts = pd.read_csv(forecast_file)

    required = [
        "city",
        "date",
        "variable",
        "predicted"
    ]

    missing = [
        col for col in required
        if col not in forecasts.columns
    ]

    if missing:
        raise ValueError(
            f"Missing forecast columns: {missing}"
        )

    forecasts["date"] = pd.to_datetime(
        forecasts["date"],
        errors="coerce"
    )

    forecasts["predicted"] = pd.to_numeric(
        forecasts["predicted"],
        errors="coerce"
    )

    forecasts["city"] = forecasts["city"].astype(str)

    selected = forecasts[
        forecasts["city"].str.casefold().isin(
            [city1.casefold(), city2.casefold()]
        )
    ].copy()

    selected = selected[
        selected["variable"].isin(VARIABLES)
    ]

    selected["comparison_column"] = (
        selected["city"] + "_" + selected["variable"]
    )

    comparison = selected.pivot_table(
        index="date",
        columns="comparison_column",
        values="predicted",
        aggfunc="first"
    ).reset_index()

    comparison.columns.name = None

    return comparison.sort_values("date").reset_index(drop=True)


# ============================================================
# 8. SAVE COMPARISON RESULTS
# ============================================================

def save_comparison_results(
    city1,
    city2,
    monthly,
    annual,
    trends,
    forecasts
):

    COMPARISON_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    safe_city1 = re.sub(
        r"[^A-Za-z0-9_-]+", "_", city1
    )

    safe_city2 = re.sub(
        r"[^A-Za-z0-9_-]+", "_", city2
    )

    prefix = f"{safe_city1}_vs_{safe_city2}"

    files = {
        "monthly": COMPARISON_DIR / f"{prefix}_monthly.csv",
        "annual": COMPARISON_DIR / f"{prefix}_annual.csv",
        "trends": COMPARISON_DIR / f"{prefix}_trends.csv",
        "forecasts": COMPARISON_DIR / f"{prefix}_forecasts.csv"
    }

    monthly.to_csv(files["monthly"], index=False)
    annual.to_csv(files["annual"], index=False)
    trends.to_csv(files["trends"], index=False)
    forecasts.to_csv(files["forecasts"], index=False)

    print("\nComparison files saved:")

    for file_path in files.values():
        print(file_path)

    return files


# ============================================================
# 9. MAIN PUBLIC FUNCTION
# ============================================================

def compare_two_cities(city1, city2):

    city1 = get_city_name(city1)
    city2 = get_city_name(city2)

    if city1.casefold() == city2.casefold():
        raise ValueError(
            "Please select two different cities."
        )

    print("\n" + "=" * 60)
    print("GLOBAL TWO-CITY COMPARISON")
    print("=" * 60)

    print(f"City 1: {city1}")
    print(f"City 2: {city2}")

    # Load existing cleaned NASA data
    df1 = load_city_data(city1)
    df2 = load_city_data(city2)

    # Historical monthly comparison
    monthly = create_monthly_comparison(
        city1, city2, df1, df2
    )

    # Annual comparison
    annual = calculate_annual_comparison(
        city1, city2, df1, df2
    )

    # Statistical trends
    trends = load_trend_comparison(
        city1, city2
    )

    # Future projections
    forecasts = load_forecast_comparison(
        city1, city2
    )

    # Save all comparison files
    files = save_comparison_results(
        city1,
        city2,
        monthly,
        annual,
        trends,
        forecasts
    )

    print("\n" + "=" * 60)
    print("COMPARISON COMPLETED SUCCESSFULLY")
    print("=" * 60)

    print(f"Monthly records: {len(monthly)}")
    print(f"Annual records: {len(annual)}")
    print(f"Trend records: {len(trends)}")
    print(f"Forecast records: {len(forecasts)}")

    return {
        "city1": city1,
        "city2": city2,
        "monthly": monthly,
        "annual": annual,
        "trends": trends,
        "forecasts": forecasts,
        "files": files
    }


# ============================================================
# 10. TEST EXAMPLE
# ============================================================

if __name__ == "__main__":

    try:
        result = compare_two_cities(
            "Islamabad",
            "London"
        )

        print("\nTrend comparison:")
        print(result["trends"].to_string(index=False))

    except Exception as error:
        print("\nCOMPARISON ERROR:", error)

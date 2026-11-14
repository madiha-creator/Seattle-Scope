
"""
Manual Validation
NASA Earth System Trend Detective
"""

from pathlib import Path
import itertools

import numpy as np
import pandas as pd
from scipy.stats import norm


PROJECT_ROOT = Path(__file__).resolve().parent.parent

ANNUAL_FILE = PROJECT_ROOT / "outputs" / "all_cities_annual_averages.csv"
TREND_FILE = PROJECT_ROOT / "outputs" / "all_cities_trend_results.csv"
OUTPUT_FILE = PROJECT_ROOT / "outputs" / "manual_validation_report.csv"

TEST_CITIES = ["Islamabad", "London", "Cairo"]
VARIABLES = ["precipitation", "soil_moisture"]


def manual_mann_kendall(values):

    values = np.asarray(values, dtype=float)
    values = values[~np.isnan(values)]
    n = len(values)

    S = 0

    for i in range(n - 1):
        for j in range(i + 1, n):
            difference = values[j] - values[i]

            if difference > 0:
                S += 1
            elif difference < 0:
                S -= 1

    _, tie_counts = np.unique(values, return_counts=True)

    tie_sum = sum(
        count * (count - 1) * (2 * count + 5)
        for count in tie_counts if count > 1
    )

    variance = (
        n * (n - 1) * (2 * n + 5) - tie_sum
    ) / 18

    tau = S / (n * (n - 1) / 2)

    if variance == 0:
        z = 0
        p_value = 1.0
    else:
        sd = np.sqrt(variance)

        if S > 0:
            z = (S - 1) / sd
        elif S < 0:
            z = (S + 1) / sd
        else:
            z = 0

        p_value = 2 * norm.sf(abs(z))

    if p_value < 0.05 and S > 0:
        trend = "increasing"
    elif p_value < 0.05 and S < 0:
        trend = "decreasing"
    else:
        trend = "no trend"

    return {
        "S": S,
        "variance": variance,
        "tau": tau,
        "Z": z,
        "p_value": p_value,
        "trend": trend
    }


def manual_sen_slope(years, values):

    slopes = []

    for i, j in itertools.combinations(range(len(values)), 2):
        if years[j] != years[i]:
            slope = (
                values[j] - values[i]
            ) / (years[j] - years[i])

            slopes.append(slope)

    return float(np.median(slopes))


def main():

    annual = pd.read_csv(ANNUAL_FILE)
    trends = pd.read_csv(TREND_FILE)

    results = []

    for city in TEST_CITIES:

        city_data = annual[
            annual["city"].astype(str).str.lower() == city.lower()
        ].copy()

        for variable in VARIABLES:

            selected = city_data[["year", variable]].copy()

            selected["year"] = pd.to_numeric(
                selected["year"], errors="coerce"
            )

            selected[variable] = pd.to_numeric(
                selected[variable], errors="coerce"
            )

            selected = selected.dropna().sort_values("year")

            years = selected["year"].to_numpy(dtype=float)
            values = selected[variable].to_numpy(dtype=float)

            if len(values) < 2:
                print(f"Not enough data: {city} - {variable}")
                continue

            manual_mk = manual_mann_kendall(values)
            manual_slope = manual_sen_slope(years, values)

            existing = trends[
                (trends["city"].astype(str).str.lower() == city.lower())
                &
                (
                    trends["variable"].astype(str).str.lower()
                    == variable.lower()
                )
            ]

            if existing.empty:
                print(f"Library result missing: {city} - {variable}")
                continue

            row = existing.iloc[0]

            library_tau = float(row["mk_tau"])
            library_p = float(row["mk_p_value"])
            library_slope = float(row["sen_slope"])

            tau_difference = abs(manual_mk["tau"] - library_tau)
            p_difference = abs(manual_mk["p_value"] - library_p)
            slope_difference = abs(manual_slope - library_slope)

            results.append({
                "city": city,
                "variable": variable,
                "valid_years": len(values),

                "manual_MK_S": manual_mk["S"],
                "manual_MK_variance": manual_mk["variance"],
                "manual_MK_tau_a": manual_mk["tau"],
                "manual_MK_Z": manual_mk["Z"],
                "manual_MK_p_value": manual_mk["p_value"],
                "manual_MK_trend": manual_mk["trend"],

                "manual_Sen_slope": manual_slope,

                "library_MK_tau": library_tau,
                "library_MK_p_value": library_p,
                "library_Sen_slope": library_slope,

                "tau_difference": tau_difference,
                "p_value_difference": p_difference,
                "Sen_slope_difference": slope_difference,

                "Sen_slope_match": np.isclose(
                    manual_slope, library_slope, atol=1e-10
                ),

                "p_value_match": np.isclose(
                    manual_mk["p_value"], library_p, atol=1e-10
                )
            })

            print("\n" + "-" * 50)
            print(f"City: {city} | Variable: {variable}")
            print(f"Manual MK trend: {manual_mk['trend']}")
            print(f"Manual MK p-value: {manual_mk['p_value']:.6f}")
            print(f"Library MK p-value: {library_p:.6f}")
            print(f"Tau difference: {tau_difference:.8f}")
            print(f"p-value difference: {p_difference:.8f}")
            print(f"Manual Sen slope: {manual_slope:.10f}")
            print(f"Library Sen slope: {library_slope:.10f}")
            print(f"Sen slope match: {np.isclose(manual_slope, library_slope, atol=1e-10)}")

    if not results:
        print("No validation results generated.")
        return

    report = pd.DataFrame(results)
    report.to_csv(OUTPUT_FILE, index=False)

    print("\n" + "=" * 55)
    print("CORRECTED MANUAL VALIDATION COMPLETED")
    print("=" * 55)
    print(f"Total comparisons: {len(report)}")
    print(f"Report saved: {OUTPUT_FILE}")

    print("\nFinal comparison:")
    print(report.to_string(index=False))


if __name__ == "__main__":
    main()

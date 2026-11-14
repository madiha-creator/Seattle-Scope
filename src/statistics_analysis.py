
import pandas as pd
import numpy as np
import pymannkendall as mk

from scipy.stats import kendalltau, theilslopes

from config import (
    PROCESSED_DIR,
    OUTPUT_DIR,
    CITIES,
    START_YEAR,
    END_YEAR
)


# ==========================================
# SETTINGS
# ==========================================

MIN_VALID_MONTHS = 9
MIN_VALID_YEARS = 10
CONFIDENCE_LEVEL = 0.95
SIGNIFICANCE_LEVEL = 0.05

MIN_AVERAGE_FOR_PERCENTAGE = 1e-8
P_VALUE_TOLERANCE = 0.01

VARIABLES = [
    "precipitation",
    "soil_moisture"
]


# ==========================================
# ANNUAL AVERAGES
# ==========================================

def calculate_annual_averages(city):
    """Calculate annual averages using at least 9 valid months."""

    input_file = PROCESSED_DIR / f"{city.lower()}_cleaned.csv"

    if not input_file.exists():
        raise FileNotFoundError(
            f"Cleaned file not found: {input_file}"
        )

    df = pd.read_csv(input_file)

    df["date"] = pd.to_datetime(
        df["date"],
        errors="coerce"
    )

    df = df.dropna(subset=["date"]).copy()
    df["year"] = df["date"].dt.year

    df = df[
        (df["year"] >= START_YEAR)
        & (df["year"] <= END_YEAR)
    ].copy()

    annual_records = []

    for year in range(START_YEAR, END_YEAR + 1):

        year_df = df[df["year"] == year]

        record = {
            "city": city,
            "year": year
        }

        for variable in VARIABLES:

            valid_values = year_df[variable].dropna()
            valid_months = len(valid_values)

            if valid_months >= MIN_VALID_MONTHS:
                annual_average = round(
                    valid_values.mean(),
                    6
                )
            else:
                annual_average = np.nan

            record[variable] = annual_average
            record[f"{variable}_valid_months"] = valid_months

        annual_records.append(record)

    return pd.DataFrame(annual_records)


# ==========================================
# PERCENTAGE CHANGE PER DECADE
# ==========================================

def calculate_percentage_per_decade(sen_slope, city_average):
    """Calculate relative percentage change per decade."""

    if pd.isna(sen_slope) or pd.isna(city_average):
        return np.nan

    if abs(city_average) <= MIN_AVERAGE_FOR_PERCENTAGE:
        return np.nan

    return (sen_slope * 10 / city_average) * 100


# ==========================================
# MANN-KENDALL AND SEN'S SLOPE
# ==========================================

def analyze_trend(city, annual_df, variable):
    """Calculate trend statistics for one city and variable."""

    data = annual_df[
        ["year", variable]
    ].dropna().copy()

    city_average = data[variable].mean()

    result = {
        "city": city,
        "variable": variable,
        "valid_years": len(data),
        "city_average": city_average,
        "trend": "insufficient_data",
        "significant": False,
        "mk_tau": np.nan,
        "mk_p_value": np.nan,
        "sen_slope": np.nan,
        "sen_slope_lower_95": np.nan,
        "sen_slope_upper_95": np.nan,
        "pct_per_decade": np.nan,
        "pct_per_decade_lower_95": np.nan,
        "pct_per_decade_upper_95": np.nan,
        "sen_intercept": np.nan,
        "scipy_kendall_tau": np.nan,
        "scipy_kendall_p_value": np.nan,
        "p_value_difference": np.nan
    }

    if len(data) < MIN_VALID_YEARS:
        return result

    years = data["year"].to_numpy(dtype=float)
    values = data[variable].to_numpy(dtype=float)

    # Mann-Kendall test
    mk_result = mk.original_test(values)

    result["trend"] = mk_result.trend
    result["mk_tau"] = mk_result.Tau
    result["mk_p_value"] = mk_result.p

    result["significant"] = (
        mk_result.p < SIGNIFICANCE_LEVEL
    )

    # Sen's slope and 95% confidence interval
    sen_result = theilslopes(
        values,
        years,
        alpha=CONFIDENCE_LEVEL
    )

    result["sen_slope"] = sen_result.slope
    result["sen_slope_lower_95"] = sen_result.low_slope
    result["sen_slope_upper_95"] = sen_result.high_slope
    result["sen_intercept"] = sen_result.intercept

    # Percentage change per decade
    result["pct_per_decade"] = calculate_percentage_per_decade(
        sen_result.slope,
        city_average
    )

    result["pct_per_decade_lower_95"] = calculate_percentage_per_decade(
        sen_result.low_slope,
        city_average
    )

    result["pct_per_decade_upper_95"] = calculate_percentage_per_decade(
        sen_result.high_slope,
        city_average
    )

    # Independent comparison using SciPy
    scipy_result = kendalltau(
        years,
        values,
        nan_policy="omit"
    )

    result["scipy_kendall_tau"] = scipy_result.statistic
    result["scipy_kendall_p_value"] = scipy_result.pvalue

    result["p_value_difference"] = abs(
        mk_result.p - scipy_result.pvalue
    )

    return result


# ==========================================
# THREE-CITY LIBRARY VALIDATION
# ==========================================

def validate_three_cities(trends_df):
    """
    Compare Mann-Kendall p-values against SciPy p-values.

    Tau-a and tau-b are different definitions, so tau
    equality is not used as a validation requirement.
    """

    validation_cities = [
        "Islamabad",
        "London",
        "Cairo"
    ]

    validation_records = []

    for city in validation_cities:

        for variable in VARIABLES:

            row = trends_df[
                (trends_df["city"] == city)
                & (trends_df["variable"] == variable)
            ]

            if row.empty:
                continue

            row = row.iloc[0]

            mk_tau = row["mk_tau"]
            scipy_tau = row["scipy_kendall_tau"]

            mk_p = row["mk_p_value"]
            scipy_p = row["scipy_kendall_p_value"]

            p_match = (
                pd.notna(mk_p)
                and pd.notna(scipy_p)
                and np.isclose(
                    mk_p,
                    scipy_p,
                    atol=P_VALUE_TOLERANCE
                )
            )

            validation_records.append({
                "city": city,
                "variable": variable,
                "mk_tau_a": mk_tau,
                "scipy_tau_b": scipy_tau,
                "mk_p_value": mk_p,
                "scipy_p_value": scipy_p,
                "p_value_difference": (
                    abs(mk_p - scipy_p)
                    if pd.notna(mk_p) and pd.notna(scipy_p)
                    else np.nan
                ),
                "p_value_match_within_0.01": p_match,
                "validation_passed": p_match
            })

    validation_df = pd.DataFrame(validation_records)

    validation_file = (
        OUTPUT_DIR / "statistics_library_validation_report.csv"
    )

    validation_df.to_csv(
        validation_file,
        index=False
    )

    print("\n======================================")
    print("THREE-CITY LIBRARY VALIDATION")
    print("======================================")

    if not validation_df.empty:
        print(validation_df.to_string(index=False))

        passed = validation_df["validation_passed"].sum()
        total = len(validation_df)

        print(f"\nValidation passed: {passed}/{total}")

    print("\nLibrary validation report saved:")
    print(validation_file)

    return validation_df


# ==========================================
# MAIN ANALYSIS
# ==========================================

def run_statistical_analysis():

    print("\n======================================")
    print("GLOBAL STATISTICAL TREND ANALYSIS")
    print("======================================")

    all_annual_data = []
    all_trends = []

    for index, location in enumerate(CITIES, start=1):

        city = location["city"]

        print(f"\nCity {index}/{len(CITIES)}: {city}")

        try:
            annual_df = calculate_annual_averages(city)

            all_annual_data.append(annual_df)

            for variable in VARIABLES:

                trend_result = analyze_trend(
                    city,
                    annual_df,
                    variable
                )

                all_trends.append(trend_result)

                if pd.notna(trend_result["mk_p_value"]):

                    if pd.notna(trend_result["pct_per_decade"]):
                        percentage_text = (
                            f"{trend_result['pct_per_decade']:.4f}"
                        )
                    else:
                        percentage_text = "Not available"

                    print(
                        f"{variable}: "
                        f"{trend_result['trend']} | "
                        f"p={trend_result['mk_p_value']:.6f} | "
                        f"%/decade={percentage_text}"
                    )

                else:
                    print(f"{variable}: insufficient data")

        except Exception as error:
            print(f"ERROR for {city}: {error}")
            raise

    # ======================================
    # SAVE ANNUAL AVERAGES
    # ======================================

    if not all_annual_data:
        raise RuntimeError("No annual data was generated.")

    annual_results = pd.concat(
        all_annual_data,
        ignore_index=True
    )

    annual_file = (
        OUTPUT_DIR / "all_cities_annual_averages.csv"
    )

    annual_results.to_csv(
        annual_file,
        index=False
    )

    # ======================================
    # SAVE TREND RESULTS
    # ======================================

    trends_df = pd.DataFrame(all_trends)

    trends_file = (
        OUTPUT_DIR / "all_cities_trend_results.csv"
    )

    trends_df.to_csv(
        trends_file,
        index=False
    )

    # Independent library comparison
    validation_df = validate_three_cities(trends_df)

    # ======================================
    # SUMMARY
    # ======================================

    print("\n======================================")
    print("STATISTICAL ANALYSIS SUMMARY")
    print("======================================")

    print("Cities configured:", len(CITIES))
    print("Cities with annual data:", annual_results["city"].nunique())
    print("Annual records generated:", len(annual_results))
    print("Trend results generated:", len(trends_df))

    print("\nTrend categories:")

    print(
        trends_df.groupby(
            ["variable", "trend"]
        ).size()
    )

    print("\nSignificant trends:")

    print(
        trends_df.groupby("variable")["significant"].sum()
    )

    print("\nAverage percentage change per decade:")

    print(
        trends_df.groupby("variable")["pct_per_decade"].mean()
    )

    print("\nSaved files:")
    print(annual_file)
    print(trends_file)

    print("\nStatistical analysis completed!")


if __name__ == "__main__":

    run_statistical_analysis()

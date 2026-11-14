
import pandas as pd
from itertools import product
from config import OUTPUT_DIR


def get_possible_explanation(variable):
    """
    Return cautious scientific explanations.
    These are possible factors to investigate, not confirmed causes.
    """
    variable_name = str(variable).lower()

    if "precipitation" in variable_name or "precip" in variable_name:
        return (
            "Possible differences in regional rainfall patterns, "
            "monsoon influence, atmospheric circulation, or topography. "
            "These factors require independent investigation."
        )

    if "soil_moisture" in variable_name or "soil" in variable_name:
        return (
            "Possible differences in rainfall, evaporation, temperature, "
            "soil properties, vegetation, irrigation, or land use. "
            "These factors require independent investigation."
        )

    return (
        "Possible differences in regional climate and local environmental "
        "conditions. Independent evidence is needed to identify the cause."
    )


def find_opposite_trends(top_n=5):

    input_file = OUTPUT_DIR / "all_cities_trend_results.csv"

    if not input_file.exists():
        raise FileNotFoundError(f"File not found: {input_file}")

    if top_n < 1:
        raise ValueError("top_n must be at least 1.")

    df = pd.read_csv(input_file)

    required_columns = [
        "city",
        "variable",
        "mk_p_value",
        "sen_slope",
        "pct_per_decade",
        "significant"
    ]

    missing = [col for col in required_columns if col not in df.columns]

    if missing:
        raise ValueError(f"Missing columns: {missing}")

    # Convert numeric columns safely.
    numeric_columns = [
        "mk_p_value",
        "sen_slope",
        "pct_per_decade"
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    # Handle boolean values whether CSV stores them as True/False or text.
    significant_values = (
        df["significant"]
        .astype(str)
        .str.strip()
        .str.lower()
        .isin(["true", "1", "yes"])
    )

    # Keep only statistically significant trends.
    significant = df[
        significant_values
        & (df["mk_p_value"] < 0.05)
        & df["pct_per_decade"].notna()
        & df["city"].notna()
        & df["variable"].notna()
    ].copy()

    results = []

    # Compare increasing and decreasing cities for the same variable.
    for variable in significant["variable"].unique():

        variable_data = significant[
            significant["variable"] == variable
        ]

        increasing = variable_data[
            variable_data["pct_per_decade"] > 0
        ]

        decreasing = variable_data[
            variable_data["pct_per_decade"] < 0
        ]

        for (_, inc), (_, dec) in product(
            increasing.iterrows(),
            decreasing.iterrows()
        ):

            inc_city = str(inc["city"]).strip()
            dec_city = str(dec["city"]).strip()

            if inc_city.casefold() == dec_city.casefold():
                continue

            trend_gap = (
                inc["pct_per_decade"] - dec["pct_per_decade"]
            )

            results.append({
                "variable": variable,
                "city_increasing": inc_city,
                "city_decreasing": dec_city,
                "increasing_pct_per_decade": inc["pct_per_decade"],
                "decreasing_pct_per_decade": dec["pct_per_decade"],
                "increasing_p_value": inc["mk_p_value"],
                "decreasing_p_value": dec["mk_p_value"],
                "increasing_sen_slope": inc["sen_slope"],
                "decreasing_sen_slope": dec["sen_slope"],
                "trend_gap_pct_points": trend_gap,
                "possible_explanation": get_possible_explanation(variable)
            })

    columns = [
        "rank",
        "variable",
        "city_increasing",
        "city_decreasing",
        "increasing_pct_per_decade",
        "decreasing_pct_per_decade",
        "increasing_p_value",
        "decreasing_p_value",
        "increasing_sen_slope",
        "decreasing_sen_slope",
        "trend_gap_pct_points",
        "possible_explanation"
    ]

    results_df = pd.DataFrame(results)

    if results_df.empty:
        print("\nNo significant opposite-trend city pairs found.")
        results_df = pd.DataFrame(columns=columns)

    else:
        # Rank all candidate pairs by the largest trend gap.
        results_df = results_df.sort_values(
            "trend_gap_pct_points",
            ascending=False
        ).reset_index(drop=True)

        # Greedy selection: each city can appear only once.
        selected_rows = []
        used_cities = set()

        for _, row in results_df.iterrows():

            increasing_city = str(row["city_increasing"]).casefold()
            decreasing_city = str(row["city_decreasing"]).casefold()

            if (
                increasing_city in used_cities
                or decreasing_city in used_cities
            ):
                continue

            selected_rows.append(row)

            used_cities.add(increasing_city)
            used_cities.add(decreasing_city)

            if len(selected_rows) >= top_n:
                break

        results_df = pd.DataFrame(selected_rows)

        if not results_df.empty:
            results_df.insert(
                0,
                "rank",
                range(1, len(results_df) + 1)
            )

            results_df = results_df[columns]

            print("\nTOP UNIQUE OPPOSITE-TREND CITY PAIRS")
            print("=" * 80)
            print(results_df.to_string(index=False))

            print("\nCITY UNIQUENESS CHECK")
            selected_cities = (
                results_df["city_increasing"].tolist()
                + results_df["city_decreasing"].tolist()
            )

            print(f"Total selected pairs: {len(results_df)}")
            print(f"Total cities used: {len(selected_cities)}")
            print(
                "No repeated cities:",
                len(selected_cities) == len(set(
                    city.casefold() for city in selected_cities
                ))
            )

        else:
            results_df = pd.DataFrame(columns=columns)
            print("\nNo non-repeating city pairs could be selected.")

    output_file = OUTPUT_DIR / "opposite_trends.csv"
    results_df.to_csv(output_file, index=False)

    print(f"\nSaved report: {output_file}")

    if 0 < len(results_df) < 3:
        print(
            "\nNote: Fewer than 3 unique pairs were available. "
            "The code did not repeat cities just to fill the report."
        )

    return results_df


if __name__ == "__main__":
    find_opposite_trends(top_n=5)

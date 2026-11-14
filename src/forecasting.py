
"""
NASA Space Apps Challenge 2026
Be An Earth System Trend Detective

Monthly forecasting of:
1. Corrected Precipitation (PRECTOTCORR)
2. Root Zone Soil Moisture (GWETROOT)

Training: 1981-2020
Testing:  2021-2025
Future:   2026-2035

Model:
- Scikit-learn Linear Regression
- Long-term time trend
- Month-of-year seasonal features

Evaluation:
- MAE
- RMSE
- Seasonal Naive Baseline comparison
- Skill score
- 95% model-based prediction intervals

Important:
These are indicative long-term projections,
not operational weather forecasts.
"""

from pathlib import Path
import re
import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from scipy.stats import t

from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error

from config import CITIES

warnings.filterwarnings("ignore")


# ============================================================
# 1. PROJECT PATHS AND SETTINGS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_DIR = PROJECT_ROOT / "outputs"

PLOT_DIR = OUTPUT_DIR / "monthly_forecasts"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
PLOT_DIR.mkdir(parents=True, exist_ok=True)

TRAIN_END = "2020-12-01"
TEST_START = "2021-01-01"
TEST_END = "2025-12-01"

FUTURE_START = "2026-01-01"
FUTURE_END = "2035-12-01"

BASE_YEAR = 1981

PREDICTION_INTERVAL = 0.95

VARIABLES = {
    "precipitation": {
        "label": "Precipitation",
        "unit": "mm/day",
        "minimum": 0.0,
        "maximum": None,
    },
    "soil_moisture": {
        "label": "Root-zone soil (top ~1 m)",
        "unit": "0 to 1",
        "minimum": 0.0,
        "maximum": 1.0,
    },
}


# ============================================================
# 2. CANONICAL CITY NAMES
# ============================================================

CITY_NAME_MAP = {
    location["city"].lower(): location["city"]
    for location in CITIES
}


def get_canonical_city_name(city):
    """
    Convert lowercase filenames into config.CITIES names.

    Example:
    islamabad -> Islamabad
    new_york -> New_York
    sao_paulo -> Sao_Paulo
    """

    city_key = str(city).strip().lower()

    if city_key not in CITY_NAME_MAP:
        raise ValueError(
            f"City '{city}' is not present in config.CITIES."
        )

    return CITY_NAME_MAP[city_key]


# ============================================================
# 3. CREATE TREND + SEASONAL FEATURES
# ============================================================

def create_features(date_values):
    """
    Create:
    - Continuous time index for long-term trend
    - 11 month dummy variables for annual seasonality

    January is the reference month.
    """

    dates = pd.Series(
        pd.to_datetime(date_values)
    ).reset_index(drop=True)

    features = pd.DataFrame()

    features["time_index"] = (
        (dates.dt.year - BASE_YEAR) * 12
        + dates.dt.month - 1
    )

    for month in range(2, 13):
        features[f"month_{month}"] = (
            dates.dt.month == month
        ).astype(int)

    return features


# ============================================================
# 4. APPLY PHYSICAL LIMITS
# ============================================================

def apply_physical_limits(values, variable):
    """
    Keep predictions within physically meaningful limits.
    """

    values = np.asarray(values, dtype=float)

    minimum = VARIABLES[variable]["minimum"]
    maximum = VARIABLES[variable]["maximum"]

    values = np.maximum(values, minimum)

    if maximum is not None:
        values = np.minimum(values, maximum)

    return values


# ============================================================
# 5. CALCULATE MODEL-BASED PREDICTION INTERVAL
# ============================================================

def calculate_prediction_interval(
    model,
    X_train,
    y_train,
    X_future,
    variable,
    confidence_level=PREDICTION_INTERVAL
):
    """
    Calculate classical OLS-style prediction intervals.

    Formula:

    Prediction +/- t_critical * residual_standard_error
                   * sqrt(1 + leverage)

    This is a model-based interval, not a guarantee
    of the actual future climate values.
    """

    X_train_array = np.asarray(
        X_train,
        dtype=float
    )

    X_future_array = np.asarray(
        X_future,
        dtype=float
    )

    y_train_array = np.asarray(
        y_train,
        dtype=float
    )

    # Include intercept in the design matrix.
    train_design = np.column_stack([
        np.ones(len(X_train_array)),
        X_train_array
    ])

    future_design = np.column_stack([
        np.ones(len(X_future_array)),
        X_future_array
    ])

    # Training residuals.
    fitted_values = model.predict(X_train)

    residuals = (
        y_train_array - fitted_values
    )

    # Residual degrees of freedom.
    matrix_rank = np.linalg.matrix_rank(
        train_design
    )

    degrees_of_freedom = (
        len(y_train_array) - matrix_rank
    )

    if degrees_of_freedom <= 0:
        raise ValueError(
            "Not enough degrees of freedom for prediction intervals."
        )

    residual_variance = (
        np.sum(residuals ** 2)
        / degrees_of_freedom
    )

    residual_standard_error = np.sqrt(
        residual_variance
    )

    # Leverage for future observations.
    inverse_matrix = np.linalg.pinv(
        train_design.T @ train_design
    )

    leverage = np.einsum(
        "ij,jk,ik->i",
        future_design,
        inverse_matrix,
        future_design
    )

    leverage = np.maximum(
        leverage,
        0.0
    )

    # Student t critical value.
    alpha = 1 - confidence_level

    critical_value = t.ppf(
        1 - alpha / 2,
        degrees_of_freedom
    )

    future_predictions = model.predict(
        X_future
    )

    margin = (
        critical_value
        * residual_standard_error
        * np.sqrt(1 + leverage)
    )

    lower_bound = future_predictions - margin
    upper_bound = future_predictions + margin

    # Apply physical constraints to interval bounds.
    lower_bound = apply_physical_limits(
        lower_bound,
        variable
    )

    upper_bound = apply_physical_limits(
        upper_bound,
        variable
    )

    # Keep the prediction inside its interval.
    lower_bound = np.minimum(
        lower_bound,
        apply_physical_limits(
            future_predictions,
            variable
        )
    )

    upper_bound = np.maximum(
        upper_bound,
        apply_physical_limits(
            future_predictions,
            variable
        )
    )

    return lower_bound, upper_bound


# ============================================================
# 6. LOAD AND PREPARE CITY DATA
# ============================================================

def load_city_data(file_path):

    df = pd.read_csv(file_path)

    required_columns = [
        "date",
        "precipitation",
        "soil_moisture",
    ]

    missing_columns = [
        col for col in required_columns
        if col not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing columns in {file_path.name}: "
            f"{missing_columns}"
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

    df = df.sort_values("date")

    # Normalize dates to monthly timestamps.
    df["date"] = (
        df["date"]
        .dt.to_period("M")
        .dt.to_timestamp()
    )

    # Remove duplicates after monthly conversion.
    df = df.drop_duplicates(
        subset=["date"],
        keep="first"
    )

    return df.reset_index(drop=True)


# ============================================================
# 7. CALCULATE MODEL AND BASELINE METRICS
# ============================================================

def calculate_metrics(actual, predicted):

    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)

    mae = mean_absolute_error(
        actual,
        predicted
    )

    rmse = np.sqrt(
        mean_squared_error(
            actual,
            predicted
        )
    )

    return mae, rmse


# ============================================================
# 8. SAVE PROFESSIONAL FORECAST GRAPH
# ============================================================

def save_forecast_plot(
    city,
    variable,
    historical,
    test_predictions,
    future_predictions
):

    info = VARIABLES[variable]

    fig, ax = plt.subplots(
        figsize=(14, 6)
    )

    # Historical NASA POWER observations.
    ax.plot(
        historical["date"],
        historical[variable],
        label="NASA POWER (MERRA-2 reanalysis)",
        linewidth=1.3
    )

    # Test-period model predictions.
    ax.plot(
        test_predictions["date"],
        test_predictions["predicted"],
        label="Model Test Predictions (2021-2025)",
        linewidth=1.7,
        linestyle="--"
    )

    # Future projection line.
    ax.plot(
        future_predictions["date"],
        future_predictions["predicted"],
        label="Indicative Projection (2026-2035)",
        linewidth=2.0
    )

    # 95% prediction interval.
    ax.fill_between(
        future_predictions["date"],
        future_predictions["lower_bound"],
        future_predictions["upper_bound"],
        alpha=0.20,
        label="95% Model-Based Prediction Interval"
    )

    # Future projection starting point.
    ax.axvline(
        pd.Timestamp(FUTURE_START),
        linestyle=":",
        linewidth=1.5,
        label="Future Projection Starts"
    )

    ax.set_title(
        f"{city}: {info['label']} Monthly Trend and Projection",
        fontsize=14,
        fontweight="bold"
    )

    ax.set_xlabel("Year")

    ax.set_ylabel(
        f"{info['label']} ({info['unit']})"
    )

    ax.text(
        0.99,
        0.02,
        "Indicative projection, not a weather forecast",
        transform=ax.transAxes,
        horizontalalignment="right",
        fontsize=9,
        alpha=0.8
    )

    ax.grid(
        True,
        alpha=0.25
    )

    ax.legend()
    fig.autofmt_xdate()

    plt.tight_layout()

    safe_city = re.sub(
        r"[^A-Za-z0-9_-]+",
        "_",
        str(city)
    )

    plot_path = (
        PLOT_DIR
        / f"{safe_city}_{variable}_monthly_forecast.png"
    )

    plt.savefig(
        plot_path,
        dpi=300,
        bbox_inches="tight"
    )

    plt.close(fig)


# ============================================================
# 9. FORECAST ONE CITY AND ONE VARIABLE
# ============================================================

def forecast_city_variable(df, city, variable):

    city = get_canonical_city_name(city)

    data = df[
        ["date", variable]
    ].copy()

    data[variable] = pd.to_numeric(
        data[variable],
        errors="coerce"
    )

    data = data.dropna(
        subset=["date", variable]
    )

    data = data.sort_values("date")

    data = data[
        (data["date"] >= pd.Timestamp("1981-01-01"))
        & (data["date"] <= pd.Timestamp("2025-12-01"))
    ].copy()

    train = data[
        data["date"] <= pd.Timestamp(TRAIN_END)
    ].copy()

    test = data[
        (data["date"] >= pd.Timestamp(TEST_START))
        & (data["date"] <= pd.Timestamp(TEST_END))
    ].copy()

    if len(train) < 100:
        raise ValueError(
            f"Not enough training records for {city}, {variable}"
        )

    if len(test) < 48:
        raise ValueError(
            f"Not enough test records for {city}, {variable}"
        )

    # --------------------------------------------------------
    # A. Train using 1981-2020
    # --------------------------------------------------------

    X_train = create_features(
        train["date"]
    )

    y_train = train[variable].values

    model = LinearRegression()

    model.fit(
        X_train,
        y_train
    )

    # --------------------------------------------------------
    # B. Test using 2021-2025
    # --------------------------------------------------------

    X_test = create_features(
        test["date"]
    )

    raw_test_predictions = model.predict(
        X_test
    )

    test_model_predictions = apply_physical_limits(
        raw_test_predictions,
        variable
    )

    actual_values = test[variable].values

    model_mae, model_rmse = calculate_metrics(
        actual_values,
        test_model_predictions
    )

    # --------------------------------------------------------
    # C. Seasonal Naive Baseline
    # Previous year's same-month actual value.
    # --------------------------------------------------------

    baseline_data = data.set_index(
        "date"
    )[variable]

    baseline_predictions = []

    for date in test["date"]:

        previous_year_date = (
            date - pd.DateOffset(years=1)
        )

        baseline_value = baseline_data.get(
            previous_year_date,
            np.nan
        )

        baseline_predictions.append(
            baseline_value
        )

    baseline_predictions = np.asarray(
        baseline_predictions,
        dtype=float
    )

    valid_baseline = np.isfinite(
        baseline_predictions
    )

    if valid_baseline.sum() > 0:

        baseline_mae, baseline_rmse = calculate_metrics(
            actual_values[valid_baseline],
            baseline_predictions[valid_baseline]
        )

        skill_score = (
            1 - model_mae / baseline_mae
            if baseline_mae > 0
            else np.nan
        )

    else:

        baseline_mae = np.nan
        baseline_rmse = np.nan
        skill_score = np.nan

    # --------------------------------------------------------
    # D. Save test predictions
    # --------------------------------------------------------

    test_output = pd.DataFrame({
        "city": city,
        "date": test["date"].values,
        "variable": variable,
        "actual": actual_values,
        "predicted": test_model_predictions,
        "baseline_prediction": baseline_predictions,
    })

    # --------------------------------------------------------
    # E. Refit model on complete 1981-2025 data
    # --------------------------------------------------------

    X_full = create_features(
        data["date"]
    )

    y_full = data[variable].values

    final_model = LinearRegression()

    final_model.fit(
        X_full,
        y_full
    )

    # --------------------------------------------------------
    # F. Forecast January 2026 to December 2035
    # --------------------------------------------------------

    future_dates = pd.date_range(
        start=FUTURE_START,
        end=FUTURE_END,
        freq="MS"
    )

    X_future = create_features(
        future_dates
    )

    raw_future_predictions = final_model.predict(
        X_future
    )

    future_values = apply_physical_limits(
        raw_future_predictions,
        variable
    )

    # Calculate 95% model-based prediction intervals.
    lower_bound, upper_bound = calculate_prediction_interval(
        model=final_model,
        X_train=X_full,
        y_train=y_full,
        X_future=X_future,
        variable=variable
    )

    future_output = pd.DataFrame({
        "city": city,
        "date": future_dates,
        "variable": variable,
        "predicted": future_values,
        "lower_bound": lower_bound,
        "upper_bound": upper_bound,
        "prediction_interval": "95%",
        "unit": VARIABLES[variable]["unit"],
        "projection_type": (
            "Indicative long-term projection, not a weather forecast"
        ),
    })

    # --------------------------------------------------------
    # G. Save graph
    # --------------------------------------------------------

    save_forecast_plot(
        city=city,
        variable=variable,
        historical=data,
        test_predictions=test_output,
        future_predictions=future_output
    )

    # --------------------------------------------------------
    # H. Evaluation report
    # --------------------------------------------------------

    evaluation = {
        "city": city,
        "variable": variable,
        "training_months": len(train),
        "testing_months": len(test),
        "model": "Linear Regression with Monthly Seasonality",
        "model_mae": model_mae,
        "model_rmse": model_rmse,
        "baseline_mae": baseline_mae,
        "baseline_rmse": baseline_rmse,
        "skill_score": skill_score,
        "model_better_than_baseline": (
            model_mae < baseline_mae
            if np.isfinite(baseline_mae)
            else False
        ),
    }

    return future_output, test_output, evaluation


# ============================================================
# 10. MAIN EXECUTION
# ============================================================

def main():

    print("\n" + "=" * 65)
    print("NASA SPACE APPS 2026")
    print("EARTH SYSTEM TREND DETECTIVE")
    print("MONTHLY FORECASTING MODULE")
    print("=" * 65)

    print("\nReading cleaned NASA data...")

    files = sorted(
        DATA_DIR.glob("*_cleaned.csv")
    )

    if not files:
        raise FileNotFoundError(
            f"No cleaned CSV files found in: {DATA_DIR}"
        )

    print(f"Found {len(files)} city files.")

    all_future_forecasts = []
    all_test_predictions = []
    all_evaluations = []

    successful_cities = 0
    failed_cities = []

    for file_path in files:

        raw_city = file_path.stem.replace(
            "_cleaned",
            ""
        )

        try:
            city = get_canonical_city_name(
                raw_city
            )

            print("\n" + "-" * 55)
            print(f"Processing: {city}")

            df = load_city_data(
                file_path
            )

            for variable in VARIABLES:

                future, test, evaluation = (
                    forecast_city_variable(
                        df=df,
                        city=city,
                        variable=variable
                    )
                )

                all_future_forecasts.append(future)
                all_test_predictions.append(test)
                all_evaluations.append(evaluation)

                print(
                    f"  {variable}: "
                    f"MAE={evaluation['model_mae']:.5f}, "
                    f"RMSE={evaluation['model_rmse']:.5f}"
                )

                if np.isfinite(evaluation["skill_score"]):

                    print(
                        f"  Baseline MAE="
                        f"{evaluation['baseline_mae']:.5f}, "
                        f"Skill="
                        f"{evaluation['skill_score']:.3f}"
                    )

            successful_cities += 1

        except Exception as error:

            failed_cities.append({
                "city": raw_city,
                "error": str(error)
            })

            print(
                f"  ERROR for {raw_city}: {error}"
            )

    # ========================================================
    # 11. COMBINE AND SAVE OUTPUTS
    # ========================================================

    if not all_future_forecasts:

        raise RuntimeError(
            "No forecasts were generated. Check the error messages."
        )

    future_df = pd.concat(
        all_future_forecasts,
        ignore_index=True
    )

    test_df = pd.concat(
        all_test_predictions,
        ignore_index=True
    )

    evaluation_df = pd.DataFrame(
        all_evaluations
    )

    future_path = (
        OUTPUT_DIR / "monthly_10_year_forecasts.csv"
    )

    test_path = (
        OUTPUT_DIR / "monthly_forecast_test_predictions.csv"
    )

    evaluation_path = (
        OUTPUT_DIR / "monthly_forecast_evaluation_report.csv"
    )

    failures_path = (
        OUTPUT_DIR / "monthly_forecast_failures.csv"
    )

    future_df.to_csv(
        future_path,
        index=False
    )

    test_df.to_csv(
        test_path,
        index=False
    )

    evaluation_df.to_csv(
        evaluation_path,
        index=False
    )

    pd.DataFrame(failed_cities).to_csv(
        failures_path,
        index=False
    )

    # ========================================================
    # 12. PROJECT PERFORMANCE SUMMARY
    # ========================================================

    print("\n" + "=" * 65)
    print("FORECASTING SUMMARY")
    print("=" * 65)

    print(f"Total city files found: {len(files)}")
    print(f"Successful cities: {successful_cities}")
    print(f"Failed cities: {len(failed_cities)}")

    print(
        f"Future forecast records: {len(future_df)}"
    )

    print(
        f"Test prediction records: {len(test_df)}"
    )

    print(
        f"Models evaluated: {len(evaluation_df)}"
    )

    if not evaluation_df.empty:

        print("\nAverage model performance:")

        print(
            "Mean MAE:",
            round(evaluation_df["model_mae"].mean(), 5)
        )

        print(
            "Mean RMSE:",
            round(evaluation_df["model_rmse"].mean(), 5)
        )

        valid_skill = evaluation_df[
            evaluation_df["skill_score"].notna()
        ]

        if not valid_skill.empty:

            better_count = int(
                valid_skill["model_better_than_baseline"].sum()
            )

            print(
                "\nModels better than seasonal baseline:",
                f"{better_count}/{len(valid_skill)}"
            )

            print(
                "Average skill score:",
                round(valid_skill["skill_score"].mean(), 4)
            )

    print("\nSaved files:")

    print(f"1. {future_path}")
    print(f"2. {test_path}")
    print(f"3. {evaluation_path}")
    print(f"4. {failures_path}")
    print(f"5. Forecast graphs: {PLOT_DIR}")

    print("\nImportant scientific note:")
    print(
        "These projections describe indicative long-term patterns "
        "based on historical NASA POWER (MERRA-2 reanalysis) data. "
        "They are not operational weather forecasts."
    )

    print("\nForecasting module completed.")
    print("=" * 65)


if __name__ == "__main__":
    main()


import pandas as pd

from backend.config import (
    TREND_RESULTS_FILE,
    ANNUAL_AVERAGES_FILE,
    FORECAST_FILE,
    CLUSTERS_FILE,
    CLUSTER_CENTERS_FILE,
    OPPOSITE_TRENDS_FILE,
    VALIDATION_FILE,
)


def load_csv(file_path):
    """Load an existing CSV file without modifying it."""

    if not file_path.exists():
        raise FileNotFoundError(
            f"Required data file not found: {file_path}"
        )

    return pd.read_csv(file_path)


def load_trend_results():
    return load_csv(TREND_RESULTS_FILE)


def load_annual_averages():
    return load_csv(ANNUAL_AVERAGES_FILE)


def load_forecasts():
    return load_csv(FORECAST_FILE)


def load_city_clusters():
    return load_csv(CLUSTERS_FILE)


def load_cluster_centers():
    return load_csv(CLUSTER_CENTERS_FILE)


def load_opposite_trends():
    return load_csv(OPPOSITE_TRENDS_FILE)


def load_validation_report():
    return load_csv(VALIDATION_FILE)


def get_available_cities():
    """Return unique city names from trend results."""

    df = load_trend_results()

    if "city" not in df.columns:
        raise ValueError("City column is missing from trend results.")

    return sorted(df["city"].dropna().unique().tolist())


import numpy as np
import pandas as pd
import pytest

from src.statistics_analysis import (
    analyze_trend,
    calculate_annual_averages,
    calculate_percentage_per_decade,
)


def test_annual_averages_with_valid_months(tmp_path, monkeypatch):

    monkeypatch.setattr(
        "src.statistics_analysis.PROCESSED_DIR",
        tmp_path
    )

    dates = pd.date_range(
        start="2020-01-01",
        periods=12,
        freq="MS"
    )

    df = pd.DataFrame({
        "date": dates,
        "precipitation": [10.0] * 12,
        "soil_moisture": [0.5] * 12,
    })

    df.to_csv(
        tmp_path / "testcity_cleaned.csv",
        index=False
    )

    result = calculate_annual_averages("TestCity")

    row = result[result["year"] == 2020].iloc[0]

    assert row["precipitation"] == 10.0
    assert row["soil_moisture"] == 0.5
    assert row["precipitation_valid_months"] == 12
    assert row["soil_moisture_valid_months"] == 12


def test_annual_average_requires_nine_valid_months(tmp_path, monkeypatch):

    monkeypatch.setattr(
        "src.statistics_analysis.PROCESSED_DIR",
        tmp_path
    )

    dates = pd.date_range(
        start="2020-01-01",
        periods=12,
        freq="MS"
    )

    df = pd.DataFrame({
        "date": dates,
        "precipitation": [10.0] * 8 + [np.nan] * 4,
        "soil_moisture": [0.5] * 12,
    })

    df.to_csv(
        tmp_path / "testcity_cleaned.csv",
        index=False
    )

    result = calculate_annual_averages("TestCity")

    row = result[result["year"] == 2020].iloc[0]

    assert pd.isna(row["precipitation"])
    assert row["precipitation_valid_months"] == 8
    assert row["soil_moisture"] == 0.5


def test_analyze_increasing_trend():

    annual_df = pd.DataFrame({
        "year": np.arange(2000, 2020),
        "precipitation": np.arange(20, dtype=float) + 10,
    })

    result = analyze_trend(
        "TestCity",
        annual_df,
        "precipitation"
    )

    assert result["trend"] == "increasing"
    assert bool(result["significant"]) is True
    assert result["mk_p_value"] < 0.05
    assert result["sen_slope"] > 0


def test_analyze_decreasing_trend():

    annual_df = pd.DataFrame({
        "year": np.arange(2000, 2020),
        "precipitation": np.arange(20, 0, -1, dtype=float),
    })

    result = analyze_trend(
        "TestCity",
        annual_df,
        "precipitation"
    )

    assert result["trend"] == "decreasing"
    assert bool(result["significant"]) is True
    assert result["mk_p_value"] < 0.05
    assert result["sen_slope"] < 0


def test_analyze_insufficient_data():

    annual_df = pd.DataFrame({
        "year": np.arange(2000, 2008),
        "precipitation": np.arange(8, dtype=float),
    })

    result = analyze_trend(
        "TestCity",
        annual_df,
        "precipitation"
    )

    assert result["trend"] == "insufficient_data"
    assert result["significant"] is False
    assert pd.isna(result["mk_p_value"])


def test_percentage_per_decade():

    result = calculate_percentage_per_decade(
        sen_slope=0.1,
        city_average=10
    )

    assert np.isclose(result, 10.0)


def test_percentage_per_decade_zero_average():

    result = calculate_percentage_per_decade(
        sen_slope=0.1,
        city_average=0
    )

    assert np.isnan(result)


def test_percentage_per_decade_missing_value():

    result = calculate_percentage_per_decade(
        sen_slope=np.nan,
        city_average=10
    )

    assert np.isnan(result)

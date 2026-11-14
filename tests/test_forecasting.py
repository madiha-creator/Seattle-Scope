
import numpy as np
import pandas as pd
import pytest

from sklearn.linear_model import LinearRegression

from src.forecasting import (
    get_canonical_city_name,
    create_features,
    apply_physical_limits,
    calculate_prediction_interval,
    load_city_data,
    calculate_metrics,
    forecast_city_variable,
)


def test_get_canonical_city_name():
    assert get_canonical_city_name("islamabad") == "Islamabad"
    assert get_canonical_city_name("ISLAMABAD") == "Islamabad"


def test_get_canonical_city_name_invalid():
    with pytest.raises(ValueError):
        get_canonical_city_name("UnknownCity")


def test_create_features():
    dates = pd.to_datetime([
        "2020-01-01",
        "2020-02-01",
        "2020-12-01",
    ])

    features = create_features(dates)

    assert len(features) == 3
    assert "time_index" in features.columns
    assert "month_2" in features.columns
    assert "month_12" in features.columns

    assert features.iloc[0]["time_index"] == 468
    assert features.iloc[0]["month_2"] == 0
    assert features.iloc[1]["month_2"] == 1
    assert features.iloc[2]["month_12"] == 1


def test_apply_physical_limits():
    precipitation = apply_physical_limits(
        [-2.0, 5.0, 10.0],
        "precipitation"
    )

    assert np.all(precipitation >= 0)
    assert np.allclose(precipitation, [0.0, 5.0, 10.0])

    soil_moisture = apply_physical_limits(
        [-0.2, 0.5, 1.5],
        "soil_moisture"
    )

    assert np.all(soil_moisture >= 0)
    assert np.all(soil_moisture <= 1)
    assert np.allclose(soil_moisture, [0.0, 0.5, 1.0])


def test_calculate_prediction_interval():
    dates = pd.date_range(
        "2000-01-01",
        periods=60,
        freq="MS"
    )

    X_train = create_features(dates)

    y_train = (
        10
        + 0.01 * np.arange(60)
        + np.sin(np.arange(60) * 2 * np.pi / 12)
    )

    model = LinearRegression()
    model.fit(X_train, y_train)

    future_dates = pd.date_range(
        "2005-01-01",
        periods=12,
        freq="MS"
    )

    X_future = create_features(future_dates)

    lower, upper = calculate_prediction_interval(
        model=model,
        X_train=X_train,
        y_train=y_train,
        X_future=X_future,
        variable="precipitation"
    )

    predictions = model.predict(X_future)

    assert len(lower) == 12
    assert len(upper) == 12
    assert np.all(lower <= predictions)
    assert np.all(upper >= predictions)
    assert np.all(lower >= 0)


def test_calculate_prediction_interval_insufficient_degrees():
    X_train = pd.DataFrame({
        "time_index": [1, 2]
    })

    y_train = np.array([1.0, 2.0])

    model = LinearRegression()
    model.fit(X_train, y_train)

    with pytest.raises(ValueError):
        calculate_prediction_interval(
            model=model,
            X_train=X_train,
            y_train=y_train,
            X_future=pd.DataFrame({"time_index": [3]}),
            variable="precipitation"
        )


def test_load_city_data(tmp_path):
    df = pd.DataFrame({
        "date": [
            "2020-02-15",
            "invalid-date",
            "2020-01-15",
            "2020-02-20",
        ],
        "precipitation": ["5.0", "3.0", "4.0", "8.0"],
        "soil_moisture": ["0.5", "0.4", "0.6", "0.7"],
    })

    file_path = tmp_path / "test_city.csv"
    df.to_csv(file_path, index=False)

    result = load_city_data(file_path)

    assert len(result) == 2
    assert result["date"].is_monotonic_increasing
    assert result["date"].is_unique
    assert result.iloc[0]["date"] == pd.Timestamp("2020-01-01")
    assert result.iloc[1]["date"] == pd.Timestamp("2020-02-01")


def test_load_city_data_missing_columns(tmp_path):
    df = pd.DataFrame({
        "date": ["2020-01-01"],
        "precipitation": [5.0],
    })

    file_path = tmp_path / "incomplete.csv"
    df.to_csv(file_path, index=False)

    with pytest.raises(ValueError):
        load_city_data(file_path)


def test_calculate_metrics():
    actual = np.array([10, 20, 30], dtype=float)
    predicted = np.array([12, 18, 30], dtype=float)

    mae, rmse = calculate_metrics(actual, predicted)

    assert np.isclose(mae, 4 / 3)
    assert np.isclose(rmse, np.sqrt(8 / 3))


def test_forecast_city_variable(
    monkeypatch
):
    import src.forecasting as forecasting

    # Avoid generating actual graphs during unit tests.
    monkeypatch.setattr(
        forecasting,
        "save_forecast_plot",
        lambda **kwargs: None
    )

    dates = pd.date_range(
        "1981-01-01",
        "2025-12-01",
        freq="MS"
    )

    month_effect = np.sin(
        (dates.month - 1) * 2 * np.pi / 12
    )

    df = pd.DataFrame({
        "date": dates,
        "precipitation": (
            5 + 0.002 * np.arange(len(dates)) + month_effect
        ),
        "soil_moisture": (
            0.4 + 0.00001 * np.arange(len(dates))
            + 0.05 * month_effect
        ),
    })

    future, test, evaluation = forecast_city_variable(
        df=df,
        city="islamabad",
        variable="precipitation"
    )

    assert len(test) == 60
    assert len(future) == 120

    assert future["date"].min() == pd.Timestamp("2026-01-01")
    assert future["date"].max() == pd.Timestamp("2035-12-01")

    assert test["date"].min() == pd.Timestamp("2021-01-01")
    assert test["date"].max() == pd.Timestamp("2025-12-01")

    assert future["city"].nunique() == 1
    assert future["city"].iloc[0] == "Islamabad"

    assert future["lower_bound"].notna().all()
    assert future["upper_bound"].notna().all()

    assert (
        future["lower_bound"] <= future["predicted"]
    ).all()

    assert (
        future["upper_bound"] >= future["predicted"]
    ).all()

    assert (future["predicted"] >= 0).all()

    assert evaluation["training_months"] == 480
    assert evaluation["testing_months"] == 60
    assert np.isfinite(evaluation["model_mae"])
    assert np.isfinite(evaluation["model_rmse"])

import pandas as pd
import pytest

import src.opposite_trends as opposite


def make_trend_data():
    return pd.DataFrame([
        {
            "city": "CityA",
            "variable": "precipitation",
            "mk_p_value": 0.01,
            "sen_slope": 0.5,
            "pct_per_decade": 10.0,
            "significant": True,
        },
        {
            "city": "CityB",
            "variable": "precipitation",
            "mk_p_value": 0.02,
            "sen_slope": -0.3,
            "pct_per_decade": -8.0,
            "significant": True,
        },
        {
            "city": "CityC",
            "variable": "precipitation",
            "mk_p_value": 0.01,
            "sen_slope": 0.4,
            "pct_per_decade": 7.0,
            "significant": True,
        },
        {
            "city": "CityD",
            "variable": "precipitation",
            "mk_p_value": 0.03,
            "sen_slope": -0.2,
            "pct_per_decade": -5.0,
            "significant": True,
        },
        {
            "city": "CityE",
            "variable": "soil_moisture",
            "mk_p_value": 0.01,
            "sen_slope": 0.02,
            "pct_per_decade": 6.0,
            "significant": True,
        },
        {
            "city": "CityF",
            "variable": "soil_moisture",
            "mk_p_value": 0.02,
            "sen_slope": -0.01,
            "pct_per_decade": -4.0,
            "significant": True,
        },
        {
            "city": "CityG",
            "variable": "precipitation",
            "mk_p_value": 0.20,
            "sen_slope": 0.8,
            "pct_per_decade": 20.0,
            "significant": True,
        },
    ])


def setup_input(tmp_path, monkeypatch, df):
    monkeypatch.setattr(opposite, "OUTPUT_DIR", tmp_path)
    df.to_csv(
        tmp_path / "all_cities_trend_results.csv",
        index=False
    )


def test_precipitation_explanation():
    result = opposite.get_possible_explanation("precipitation")

    assert "rainfall" in result.lower()
    assert "independent investigation" in result.lower()


def test_soil_moisture_explanation():
    result = opposite.get_possible_explanation("soil_moisture")

    assert "evaporation" in result.lower()
    assert "land use" in result.lower()


def test_general_explanation():
    result = opposite.get_possible_explanation("temperature")

    assert "regional climate" in result.lower()
    assert "independent evidence" in result.lower()


def test_missing_input_file(tmp_path, monkeypatch):
    monkeypatch.setattr(opposite, "OUTPUT_DIR", tmp_path)

    with pytest.raises(FileNotFoundError):
        opposite.find_opposite_trends()


def test_invalid_top_n(tmp_path, monkeypatch):
    setup_input(tmp_path, monkeypatch, make_trend_data())

    with pytest.raises(ValueError, match="top_n must be at least 1"):
        opposite.find_opposite_trends(top_n=0)


def test_missing_required_columns(tmp_path, monkeypatch):
    incomplete = pd.DataFrame({
        "city": ["CityA"],
        "variable": ["precipitation"],
    })

    setup_input(tmp_path, monkeypatch, incomplete)

    with pytest.raises(ValueError, match="Missing columns"):
        opposite.find_opposite_trends()


def test_opposite_trends_and_unique_cities(tmp_path, monkeypatch):
    setup_input(tmp_path, monkeypatch, make_trend_data())

    result = opposite.find_opposite_trends(top_n=5)

    assert not result.empty

    assert len(result) == 3

    assert result["rank"].tolist() == [1, 2, 3]

    selected_cities = (
        result["city_increasing"].tolist()
        + result["city_decreasing"].tolist()
    )

    normalized_cities = [
        city.casefold() for city in selected_cities
    ]

    assert len(normalized_cities) == len(set(normalized_cities))

    assert (
        result["increasing_pct_per_decade"] > 0
    ).all()

    assert (
        result["decreasing_pct_per_decade"] < 0
    ).all()

    assert (
        result["trend_gap_pct_points"] > 0
    ).all()

    assert result["rank"].tolist() == list(
        range(1, len(result) + 1)
    )


def test_only_significant_trends_are_selected(tmp_path, monkeypatch):
    df = make_trend_data()

    df.loc[df["city"] == "CityA", "mk_p_value"] = 0.20

    setup_input(tmp_path, monkeypatch, df)

    result = opposite.find_opposite_trends(top_n=5)

    selected_cities = (
        result["city_increasing"].tolist()
        + result["city_decreasing"].tolist()
    )

    assert "CityA" not in selected_cities
    assert "CityG" not in selected_cities


def test_no_opposite_trends(tmp_path, monkeypatch):
    df = make_trend_data()

    df["pct_per_decade"] = abs(df["pct_per_decade"])

    setup_input(tmp_path, monkeypatch, df)

    result = opposite.find_opposite_trends(top_n=5)

    assert result.empty

    assert "rank" in result.columns
    assert (tmp_path / "opposite_trends.csv").exists()

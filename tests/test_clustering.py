import numpy as np
import pandas as pd
import pytest

import src.clustering as clustering


def make_trend_data():
    return pd.DataFrame({
        "city": [
            "CityA", "CityA",
            "CityB", "CityB",
            "CityC", "CityC",
            "CityD", "CityD",
            "CityE", "CityE",
            "CityF", "CityF",
        ],
        "variable": [
            "precipitation", "soil_moisture",
            "precipitation", "soil_moisture",
            "precipitation", "soil_moisture",
            "precipitation", "soil_moisture",
            "precipitation", "soil_moisture",
            "precipitation", "soil_moisture",
        ],
        "pct_per_decade": [
            10, 5, 11, 6, 9, 4,
            -5, -3, -6, -4, -4, -2,
        ],
    })


def test_prepare_clustering_data(tmp_path, monkeypatch):
    input_file = tmp_path / "trends.csv"
    make_trend_data().to_csv(input_file, index=False)

    monkeypatch.setattr(clustering, "INPUT_FILE", input_file)

    result = clustering.prepare_clustering_data()

    assert len(result) == 6
    assert result["city"].nunique() == 6
    assert "precipitation" in result.columns
    assert "soil_moisture" in result.columns
    assert result[clustering.FEATURES].notna().all().all()


def test_prepare_clustering_data_missing_file(tmp_path, monkeypatch):
    missing_file = tmp_path / "missing.csv"

    monkeypatch.setattr(clustering, "INPUT_FILE", missing_file)

    with pytest.raises(FileNotFoundError):
        clustering.prepare_clustering_data()


def test_prepare_clustering_data_missing_columns(tmp_path, monkeypatch):
    input_file = tmp_path / "incomplete.csv"

    pd.DataFrame({
        "city": ["CityA"],
        "variable": ["precipitation"],
    }).to_csv(input_file, index=False)

    monkeypatch.setattr(clustering, "INPUT_FILE", input_file)

    with pytest.raises(ValueError, match="Missing required columns"):
        clustering.prepare_clustering_data()


def test_prepare_clustering_data_insufficient_cities(tmp_path, monkeypatch):
    input_file = tmp_path / "small.csv"

    pd.DataFrame({
        "city": ["CityA", "CityA", "CityB", "CityB"],
        "variable": [
            "precipitation", "soil_moisture",
            "precipitation", "soil_moisture",
        ],
        "pct_per_decade": [1, 2, 3, 4],
    }).to_csv(input_file, index=False)

    monkeypatch.setattr(clustering, "INPUT_FILE", input_file)

    with pytest.raises(ValueError, match="At least 3 cities"):
        clustering.prepare_clustering_data()


def test_evaluate_cluster_numbers():
    X = np.array([
        [1.0, 1.0],
        [1.1, 1.2],
        [0.9, 0.8],
        [8.0, 8.0],
        [8.1, 8.2],
        [7.9, 7.8],
    ])

    result = clustering.evaluate_cluster_numbers(X)

    assert not result.empty
    assert {"k", "inertia", "silhouette_score"}.issubset(result.columns)
    assert result["k"].min() >= 2
    assert result["k"].max() <= 5
    assert result["inertia"].notna().all()
    assert result["silhouette_score"].between(-1, 1).all()


def test_perform_clustering():
    pivot_df = pd.DataFrame({
        "city": ["A", "B", "C", "D", "E", "F"],
        "precipitation": [10, 11, 9, -5, -6, -4],
        "soil_moisture": [5, 6, 4, -3, -4, -2],
    })

    metrics_df = pd.DataFrame({
        "k": [2, 3],
        "inertia": [5.0, 2.0],
        "silhouette_score": [0.80, 0.60],
    })

    clustered, centers, best_k = clustering.perform_clustering(
        pivot_df,
        metrics_df
    )

    assert best_k == 2
    assert "cluster" in clustered.columns
    assert clustered["cluster"].nunique() == 2
    assert len(centers) == 2

    assert {
        "precipitation_pct_per_decade",
        "soil_moisture_pct_per_decade",
    }.issubset(centers.columns)

    assert set(clustered["city"]) == set(pivot_df["city"])


def test_save_results(tmp_path, monkeypatch):
    monkeypatch.setattr(
        clustering,
        "CLUSTER_OUTPUT",
        tmp_path / "clusters.csv"
    )
    monkeypatch.setattr(
        clustering,
        "CENTERS_OUTPUT",
        tmp_path / "centers.csv"
    )
    monkeypatch.setattr(
        clustering,
        "METRICS_OUTPUT",
        tmp_path / "metrics.csv"
    )

    clustered = pd.DataFrame({
        "city": ["A", "B"],
        "precipitation": [5.0, -2.0],
        "soil_moisture": [2.0, -1.0],
        "cluster": [1, 2],
    })

    centers = pd.DataFrame({
        "cluster": [1, 2],
        "precipitation_pct_per_decade": [5.0, -2.0],
        "soil_moisture_pct_per_decade": [2.0, -1.0],
    })

    metrics = pd.DataFrame({
        "k": [2],
        "inertia": [1.0],
        "silhouette_score": [0.8],
    })

    clustering.save_results(clustered, centers, metrics)

    assert (tmp_path / "clusters.csv").exists()
    assert (tmp_path / "centers.csv").exists()
    assert (tmp_path / "metrics.csv").exists()

    saved = pd.read_csv(tmp_path / "clusters.csv")

    assert "precipitation_pct_per_decade" in saved.columns
    assert "soil_moisture_pct_per_decade" in saved.columns


def test_save_evaluation_plot(tmp_path, monkeypatch):
    monkeypatch.setattr(
        clustering,
        "PLOT_OUTPUT",
        tmp_path / "evaluation.png"
    )

    metrics = pd.DataFrame({
        "k": [2, 3, 4],
        "inertia": [10.0, 5.0, 2.0],
        "silhouette_score": [0.5, 0.7, 0.6],
    })

    clustering.save_evaluation_plot(metrics)

    assert (tmp_path / "evaluation.png").exists()
    assert (tmp_path / "evaluation.png").stat().st_size > 0

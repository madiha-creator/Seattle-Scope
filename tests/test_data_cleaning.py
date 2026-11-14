import pandas as pd
import pytest

import src.data_cleaning as cleaning


def create_monthly_data(year=2020):
    dates = pd.date_range(
        start=f"{year}-01-01",
        periods=12,
        freq="MS"
    )

    return pd.DataFrame({
        "date": dates,
        "precipitation": [2.5] * 12,
        "soil_moisture": [0.45] * 12
    })


def setup_directories(tmp_path, monkeypatch):
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    cache_dir = tmp_path / "cache"

    monkeypatch.setattr(cleaning, "RAW_DIR", raw_dir)
    monkeypatch.setattr(cleaning, "PROCESSED_DIR", processed_dir)
    monkeypatch.setattr(cleaning, "CACHE_DIR", cache_dir)

    monkeypatch.setattr(cleaning, "START_YEAR", 2020)
    monkeypatch.setattr(cleaning, "END_YEAR", 2020)

    raw_dir.mkdir(parents=True)
    processed_dir.mkdir(parents=True)
    cache_dir.mkdir(parents=True)

    return raw_dir, processed_dir, cache_dir


def test_create_required_directories(tmp_path, monkeypatch):
    raw_dir, processed_dir, cache_dir = setup_directories(
        tmp_path, monkeypatch
    )

    cleaning.create_required_directories()

    assert raw_dir.exists()
    assert processed_dir.exists()
    assert cache_dir.exists()


def test_missing_raw_file(tmp_path, monkeypatch):
    setup_directories(tmp_path, monkeypatch)

    with pytest.raises(FileNotFoundError):
        cleaning.clean_city_data("Islamabad")


def test_missing_required_columns(tmp_path, monkeypatch):
    raw_dir, _, _ = setup_directories(tmp_path, monkeypatch)

    pd.DataFrame({
        "date": ["2020-01-01"],
        "precipitation": [2.5]
    }).to_csv(
        raw_dir / "islamabad_monthly.csv",
        index=False
    )

    with pytest.raises(ValueError, match="Required columns missing"):
        cleaning.clean_city_data("Islamabad")


def test_successful_monthly_cleaning(tmp_path, monkeypatch):
    raw_dir, processed_dir, _ = setup_directories(
        tmp_path, monkeypatch
    )

    create_monthly_data().to_csv(
        raw_dir / "islamabad_monthly.csv",
        index=False
    )

    result = cleaning.clean_city_data("Islamabad")

    assert result["city"] == "Islamabad"
    assert result["expected_months"] == 12
    assert result["actual_records"] == 12
    assert result["unique_months"] == 12
    assert result["monthly_status"] == "PASS"

    output_file = processed_dir / "islamabad_cleaned.csv"

    assert output_file.exists()

    cleaned = pd.read_csv(output_file)

    assert len(cleaned) == 12
    assert cleaned["precipitation"].notna().all()
    assert cleaned["soil_moisture"].notna().all()


def test_invalid_dates_are_removed(tmp_path, monkeypatch):
    raw_dir, _, _ = setup_directories(tmp_path, monkeypatch)

    df = create_monthly_data()
    df["date"] = df["date"].astype("object")
    df.loc[0, "date"] = "invalid-date"

    df.to_csv(
        raw_dir / "islamabad_monthly.csv",
        index=False
    )

    result = cleaning.clean_city_data("Islamabad")

    assert result["invalid_dates_removed"] == 1
    assert result["actual_records"] == 11
    assert result["monthly_status"] == "CHECK REQUIRED"


def test_duplicate_records_are_removed(tmp_path, monkeypatch):
    raw_dir, _, _ = setup_directories(tmp_path, monkeypatch)

    df = create_monthly_data()

    duplicate = df.iloc[[0]]
    df = pd.concat([df, duplicate], ignore_index=True)

    df.to_csv(
        raw_dir / "islamabad_monthly.csv",
        index=False
    )

    result = cleaning.clean_city_data("Islamabad")

    assert result["duplicate_records_removed"] == 1
    assert result["actual_records"] == 12
    assert result["duplicate_months"] == 0
    assert result["monthly_status"] == "PASS"


def test_invalid_values_are_converted_to_missing(tmp_path, monkeypatch):
    raw_dir, processed_dir, _ = setup_directories(
        tmp_path, monkeypatch
    )

    df = create_monthly_data()
    df["precipitation"] = df["precipitation"].astype("object")
    df["soil_moisture"] = df["soil_moisture"].astype("object")

    df.loc[0, "precipitation"] = -5
    df.loc[1, "soil_moisture"] = 1.5

    df.loc[2, "precipitation"] = -999
    df.loc[3, "soil_moisture"] = -999

    df.to_csv(
        raw_dir / "islamabad_monthly.csv",
        index=False
    )

    result = cleaning.clean_city_data("Islamabad")

    assert result["invalid_precipitation"] == 1
    assert result["invalid_soil_moisture"] == 1

    assert result["missing_precipitation"] == 2
    assert result["missing_soil_moisture"] == 2

    cleaned = pd.read_csv(
        processed_dir / "islamabad_cleaned.csv"
    )

    assert pd.isna(cleaned.loc[0, "precipitation"])
    assert pd.isna(cleaned.loc[1, "soil_moisture"])
    assert pd.isna(cleaned.loc[2, "precipitation"])
    assert pd.isna(cleaned.loc[3, "soil_moisture"])


def test_invalid_numeric_values_are_handled(tmp_path, monkeypatch):
    raw_dir, processed_dir, _ = setup_directories(
        tmp_path, monkeypatch
    )

    df = create_monthly_data()
    df["precipitation"] = df["precipitation"].astype("object")
    df["soil_moisture"] = df["soil_moisture"].astype("object")

    df.loc[0, "precipitation"] = "invalid"
    df.loc[1, "soil_moisture"] = "invalid"

    df.to_csv(
        raw_dir / "islamabad_monthly.csv",
        index=False
    )

    result = cleaning.clean_city_data("Islamabad")

    assert result["missing_precipitation"] == 1
    assert result["missing_soil_moisture"] == 1

    cleaned = pd.read_csv(
        processed_dir / "islamabad_cleaned.csv"
    )

    assert pd.isna(cleaned.loc[0, "precipitation"])
    assert pd.isna(cleaned.loc[1, "soil_moisture"])


def test_missing_month_is_detected(tmp_path, monkeypatch):
    raw_dir, _, _ = setup_directories(tmp_path, monkeypatch)

    df = create_monthly_data().iloc[:-1]

    df.to_csv(
        raw_dir / "islamabad_monthly.csv",
        index=False
    )

    result = cleaning.clean_city_data("Islamabad")

    assert result["missing_months"] == 1
    assert result["actual_records"] == 11
    assert result["monthly_status"] == "CHECK REQUIRED"


def test_clean_all_cities_creates_validation_report(
    tmp_path, monkeypatch
):
    raw_dir, _, cache_dir = setup_directories(
        tmp_path, monkeypatch
    )

    pd.DataFrame([
        {
            "city": "TestCity",
            "continent": "Asia"
        },
        {
            "city": "MissingCity",
            "continent": "Europe"
        }
    ])

    create_monthly_data().to_csv(
        raw_dir / "testcity_monthly.csv",
        index=False
    )

    monkeypatch.setattr(
        cleaning,
        "CITIES",
        [
            {"city": "TestCity", "continent": "Asia"},
            {"city": "MissingCity", "continent": "Europe"}
        ]
    )

    cleaning.clean_all_cities()

    report_file = cache_dir / "data_validation_report.csv"

    assert report_file.exists()

    report = pd.read_csv(report_file)

    assert len(report) == 2

    assert (
        report.loc[
            report["city"] == "TestCity",
            "processing_status"
        ].iloc[0] == "SUCCESS"
    )

    assert (
        report.loc[
            report["city"] == "MissingCity",
            "processing_status"
        ].iloc[0] == "FAILED"
    )

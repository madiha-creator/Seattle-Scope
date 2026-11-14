
import pandas as pd

from config import (
    RAW_DIR,
    PROCESSED_DIR,
    CACHE_DIR,
    CITIES,
    START_YEAR,
    END_YEAR
)


# ==========================================
# DIRECTORY SETUP
# ==========================================

def create_required_directories():
    """Create folders required for data cleaning."""

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


# ==========================================
# CLEAN ONE CITY
# ==========================================

def clean_city_data(city):
    """Clean monthly NASA data for one city."""

    print(f"\nCleaning: {city}")

    input_file = RAW_DIR / f"{city.lower()}_monthly.csv"

    if not input_file.exists():
        raise FileNotFoundError(
            f"Raw CSV not found: {input_file}"
        )

    df = pd.read_csv(input_file)

    original_rows = len(df)

    # Check required columns
    required_columns = [
        "date",
        "precipitation",
        "soil_moisture"
    ]

    missing_columns = [
        column for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Required columns missing: {missing_columns}"
        )

    # Convert columns
    df["date"] = pd.to_datetime(
        df["date"],
        errors="coerce"
    )

    for column in ["precipitation", "soil_moisture"]:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    # Remove invalid dates
    invalid_dates = int(df["date"].isna().sum())
    df = df.dropna(subset=["date"]).copy()

    # Remove duplicate date records
    duplicate_records = int(
        df.duplicated(subset=["date"]).sum()
    )

    df = df.drop_duplicates(
        subset=["date"],
        keep="first"
    ).copy()

    # Convert NASA missing-value sentinel to missing data
    for column in ["precipitation", "soil_moisture"]:
        df.loc[df[column] <= -900, column] = pd.NA

    # Check invalid precipitation values
    invalid_precipitation = (
        df["precipitation"].notna()
        & (df["precipitation"] < 0)
    )

    invalid_precipitation_count = int(
        invalid_precipitation.sum()
    )

    df.loc[
        invalid_precipitation,
        "precipitation"
    ] = pd.NA

    # Check invalid soil moisture values
    invalid_soil = (
        df["soil_moisture"].notna()
        & (
            (df["soil_moisture"] < 0)
            | (df["soil_moisture"] > 1)
        )
    )

    invalid_soil_count = int(invalid_soil.sum())

    df.loc[
        invalid_soil,
        "soil_moisture"
    ] = pd.NA

    # Sort data
    df = df.sort_values("date").reset_index(drop=True)

    # Expected monthly dates
    expected_months = pd.period_range(
        start=f"{START_YEAR}-01",
        end=f"{END_YEAR}-12",
        freq="M"
    )

    # Actual monthly dates
    actual_months = df["date"].dt.to_period("M")

    expected_set = set(expected_months)
    actual_set = set(actual_months)

    missing_months = sorted(
        expected_set - actual_set
    )

    unexpected_months = sorted(
        actual_set - expected_set
    )

    duplicate_months = int(
        actual_months.duplicated().sum()
    )

    # Missing variable values
    missing_precipitation = int(
        df["precipitation"].isna().sum()
    )

    missing_soil = int(
        df["soil_moisture"].isna().sum()
    )

    # Valid observations
    valid_precipitation = int(
        df["precipitation"].notna().sum()
    )

    valid_soil = int(
        df["soil_moisture"].notna().sum()
    )

    # Save cleaned CSV
    output_file = (
        PROCESSED_DIR / f"{city.lower()}_cleaned.csv"
    )

    df.to_csv(output_file, index=False)

    # Determine completeness
    monthly_pass = (
        len(df) == len(expected_months)
        and len(actual_set) == len(expected_months)
        and len(missing_months) == 0
        and len(unexpected_months) == 0
        and duplicate_months == 0
    )

    print("Original records:", original_rows)
    print("Cleaned records:", len(df))
    print("Invalid dates removed:", invalid_dates)
    print("Duplicate records removed:", duplicate_records)
    print("Missing months:", len(missing_months))
    print("Duplicate months:", duplicate_months)
    print("Missing precipitation values:", missing_precipitation)
    print("Missing soil moisture values:", missing_soil)
    print("Invalid precipitation values:", invalid_precipitation_count)
    print("Invalid soil moisture values:", invalid_soil_count)

    print(
        "Monthly completeness:",
        "PASS" if monthly_pass else "CHECK REQUIRED"
    )

    return {
        "city": city,
        "expected_months": len(expected_months),
        "actual_records": len(df),
        "unique_months": len(actual_set),
        "invalid_dates_removed": invalid_dates,
        "duplicate_records_removed": duplicate_records,
        "missing_months": len(missing_months),
        "unexpected_months": len(unexpected_months),
        "duplicate_months": duplicate_months,
        "valid_precipitation": valid_precipitation,
        "missing_precipitation": missing_precipitation,
        "valid_soil_moisture": valid_soil,
        "missing_soil_moisture": missing_soil,
        "invalid_precipitation": invalid_precipitation_count,
        "invalid_soil_moisture": invalid_soil_count,
        "monthly_status": "PASS" if monthly_pass else "CHECK REQUIRED",
        "cleaned_file": f"data/processed/{city.lower()}_cleaned.csv"
    }


# ==========================================
# CLEAN ALL CITIES
# ==========================================

def clean_all_cities():
    """Clean and validate all configured cities."""

    create_required_directories()

    print("\n======================================")
    print("GLOBAL DATA CLEANING AND VALIDATION")
    print("======================================")

    reports = []

    for index, location in enumerate(CITIES, start=1):

        city = location["city"]

        print(f"\nCity {index}/{len(CITIES)}")

        try:
            result = clean_city_data(city)

            result["continent"] = location["continent"]
            result["processing_status"] = "SUCCESS"

            reports.append(result)

        except Exception as error:

            print(f"ERROR processing {city}: {error}")

            reports.append({
                "city": city,
                "continent": location["continent"],
                "processing_status": "FAILED",
                "error": str(error)
            })

    # Create validation report
    report_df = pd.DataFrame(reports)

    report_file = (
        CACHE_DIR / "data_validation_report.csv"
    )

    report_df.to_csv(report_file, index=False)

    # Final summary
    print("\n======================================")
    print("GLOBAL VALIDATION SUMMARY")
    print("======================================")

    print("Total cities:", len(CITIES))

    if "processing_status" in report_df.columns:
        print("\nProcessing status:")
        print(report_df["processing_status"].value_counts())

    if "monthly_status" in report_df.columns:
        print("\nMonthly completeness:")
        print(report_df["monthly_status"].value_counts())

    print("\nCity-wise validation:")

    display_columns = [
        "city",
        "monthly_status",
        "actual_records",
        "missing_months",
        "duplicate_months",
        "missing_precipitation",
        "missing_soil_moisture"
    ]

    available_columns = [
        column for column in display_columns
        if column in report_df.columns
    ]

    print(
        report_df[available_columns].to_string(index=False)
    )

    print("\nValidation report saved:")
    print("data/cache/data_validation_report.csv")


# ==========================================
# MAIN EXECUTION
# ==========================================

if __name__ == "__main__":

    try:
        clean_all_cities()

    except Exception as error:
        print("\nGLOBAL CLEANING ERROR:", error)

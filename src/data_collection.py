
import requests
import json
import pandas as pd
import time

from config import (
    NASA_API_URL,
    PARAMETERS,
    START_YEAR,
    END_YEAR,
    CITIES,
    RAW_DIR,
    CACHE_DIR
)


# ==========================================
# DIRECTORY SETUP
# ==========================================

def create_required_directories():
    """Create folders required for data collection."""

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


# ==========================================
# EXPECTED MONTHLY RECORDS
# ==========================================

def get_expected_months():
    """Generate all expected monthly dates."""

    return pd.date_range(
        start=f"{START_YEAR}-01-01",
        end=f"{END_YEAR}-12-01",
        freq="MS"
    )


# ==========================================
# CACHE VALIDATION
# ==========================================

def validate_cached_data(cache_file, city):
    """
    Check whether cached CSV contains complete,
    valid monthly data for the configured period.
    """

    if not cache_file.exists():
        return False, "Cache file missing"

    try:
        df = pd.read_csv(cache_file)

        required_columns = [
            "date",
            "precipitation",
            "soil_moisture",
            "city"
        ]

        for column in required_columns:
            if column not in df.columns:
                return False, f"Missing column: {column}"

        if df.empty:
            return False, "Cache file is empty"

        df["date"] = pd.to_datetime(
            df["date"],
            errors="coerce"
        )

        if df["date"].isna().any():
            return False, "Invalid dates found"

        if df["date"].duplicated().any():
            return False, "Duplicate monthly dates found"

        df["precipitation"] = pd.to_numeric(
            df["precipitation"],
            errors="coerce"
        )

        df["soil_moisture"] = pd.to_numeric(
            df["soil_moisture"],
            errors="coerce"
        )

        if df["precipitation"].isna().any():
            return False, "Missing or invalid precipitation values"

        if df["soil_moisture"].isna().any():
            return False, "Missing or invalid soil moisture values"

        if (df["precipitation"] < 0).any():
            return False, "Negative precipitation values found"

        if not df["soil_moisture"].between(0, 1).all():
            return False, "Soil moisture outside 0–1 range"

        expected_months = get_expected_months()

        actual_months = pd.DatetimeIndex(
            df["date"].dt.to_period("M").dt.to_timestamp()
        ).sort_values()

        if len(df) != len(expected_months):
            return False, (
                f"Expected {len(expected_months)} records, "
                f"found {len(df)}"
            )

        if not actual_months.equals(expected_months):
            return False, "Missing or unexpected months found"

        if not df["city"].astype(str).str.lower().eq(
            city.lower()
        ).all():
            return False, "City name mismatch"

        return True, "Cache is valid"

    except Exception as error:
        return False, f"Cache validation error: {error}"


# ==========================================
# NASA DATA DOWNLOAD WITH RETRIES
# ==========================================

def download_nasa_data(city, latitude, longitude, max_retries=3):
    """Download monthly data from NASA POWER API."""

    params = {
        "parameters": ",".join(PARAMETERS),
        "community": "RE",
        "longitude": longitude,
        "latitude": latitude,
        "start": START_YEAR,
        "end": END_YEAR,
        "format": "JSON"
    }

    for attempt in range(1, max_retries + 1):

        try:
            print(
                f"NASA API request for {city} "
                f"(attempt {attempt}/{max_retries})..."
            )

            response = requests.get(
                NASA_API_URL,
                params=params,
                timeout=120
            )

            response.raise_for_status()

            data = response.json()

            if "properties" not in data:
                raise ValueError("Invalid NASA API response.")

            if "parameter" not in data["properties"]:
                raise ValueError("NASA parameters not found.")

            return data

        except Exception as error:

            print(f"Download attempt failed: {error}")

            if attempt == max_retries:
                raise

            time.sleep(3 * attempt)


# ==========================================
# SAVE ORIGINAL NASA JSON
# ==========================================

def save_raw_json(data, city):

    raw_file = RAW_DIR / f"{city.lower()}_raw.json"

    with open(raw_file, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)

    print(f"Raw JSON saved: {raw_file}")


# ==========================================
# CONVERT JSON TO DATAFRAME
# ==========================================

def convert_to_dataframe(data, city):

    parameters = data["properties"]["parameter"]

    if "PRECTOTCORR" not in parameters:
        raise ValueError("PRECTOTCORR parameter missing.")

    if "GWETROOT" not in parameters:
        raise ValueError("GWETROOT parameter missing.")

    rainfall = parameters["PRECTOTCORR"]
    soil = parameters["GWETROOT"]

    records = []
    invalid_dates = []

    for date_key in sorted(rainfall.keys()):

        date_text = str(date_key)

        if len(date_text) != 6 or not date_text.isdigit():
            invalid_dates.append(date_key)
            continue

        year = int(date_text[:4])
        month = int(date_text[4:6])

        if not (START_YEAR <= year <= END_YEAR):
            invalid_dates.append(date_key)
            continue

        if month < 1 or month > 12:
            invalid_dates.append(date_key)
            continue

        if date_key not in soil:
            raise ValueError(
                f"Soil moisture missing for month {date_key}"
            )

        date = pd.to_datetime(
            date_text,
            format="%Y%m"
        )

        precipitation = pd.to_numeric(
            rainfall[date_key],
            errors="coerce"
        )

        soil_moisture = pd.to_numeric(
            soil[date_key],
            errors="coerce"
        )

        if pd.isna(precipitation) or pd.isna(soil_moisture):
            raise ValueError(
                f"Invalid NASA measurement for {date_key}"
            )

        if precipitation < 0:
            raise ValueError(
                f"Negative precipitation for {date_key}"
            )

        if not 0 <= soil_moisture <= 1:
            raise ValueError(
                f"Invalid soil moisture for {date_key}"
            )

        records.append({
            "date": date,
            "precipitation": precipitation,
            "soil_moisture": soil_moisture,
            "city": city
        })

    df = pd.DataFrame(records)

    if df.empty:
        raise ValueError("No valid monthly records received.")

    expected_months = get_expected_months()

    actual_months = pd.DatetimeIndex(df["date"])

    if len(df) != len(expected_months):
        raise ValueError(
            f"Incomplete NASA data: expected "
            f"{len(expected_months)}, received {len(df)}"
        )

    if not actual_months.equals(expected_months):
        raise ValueError("NASA response has missing or unexpected months.")

    print("Valid monthly records:", len(df))
    print("Invalid date keys excluded:", len(invalid_dates))

    return df


# ==========================================
# SAVE MONTHLY CSV FILES
# ==========================================

def save_monthly_csv(df, city):

    raw_csv = RAW_DIR / f"{city.lower()}_monthly.csv"
    cache_csv = CACHE_DIR / f"{city.lower()}_monthly.csv"

    df.to_csv(raw_csv, index=False)
    df.to_csv(cache_csv, index=False)

    print(f"Monthly CSV saved: {raw_csv}")
    print(f"Cache CSV saved: {cache_csv}")


# ==========================================
# COLLECT ONE CITY
# ==========================================

def collect_city_data(location):

    create_required_directories()

    city = location["city"]

    raw_json = RAW_DIR / f"{city.lower()}_raw.json"
    raw_csv = RAW_DIR / f"{city.lower()}_monthly.csv"
    cache_csv = CACHE_DIR / f"{city.lower()}_monthly.csv"

    # First priority: reuse valid cache
    is_valid, message = validate_cached_data(
        cache_csv,
        city
    )

    if is_valid:

        print(f"\nSKIPPING {city}")
        print("Reason:", message)
        print("Using existing cached data.")

        return "SKIPPED"

    print(f"\nCache unavailable for {city}: {message}")

    # Cache invalid or missing: download from NASA
    try:

        data = download_nasa_data(
            city,
            location["latitude"],
            location["longitude"]
        )

        df = convert_to_dataframe(data, city)

        # Save files only after successful validation
        save_raw_json(data, city)
        save_monthly_csv(df, city)

        print(f"{city} completed successfully!")

        return "SUCCESS"

    except Exception as error:

        print(f"\nERROR downloading {city}: {error}")

        return "FAILED"


# ==========================================
# COLLECT ALL CITIES
# ==========================================

def collect_all_cities():

    create_required_directories()

    print("\n===================================")
    print("NASA POWER GLOBAL DATA COLLECTION")
    print("===================================")

    print("Total configured cities:", len(CITIES))
    print("Expected records per city:", len(get_expected_months()))

    results = []

    for index, location in enumerate(CITIES, start=1):

        city = location["city"]

        print(f"\nCity {index}/{len(CITIES)}: {city}")
        print("Continent:", location["continent"])

        status = collect_city_data(location)

        results.append({
            "city": city,
            "continent": location["continent"],
            "status": status
        })

        if index < len(CITIES):
            time.sleep(1)

    # Collection report
    report = pd.DataFrame(results)

    report_file = CACHE_DIR / "collection_report.csv"

    report.to_csv(report_file, index=False)

    print("\n===================================")
    print("DATA COLLECTION SUMMARY")
    print("===================================")

    print("\nTotal cities:", len(report))
    print("\nStatus counts:")
    print(report["status"].value_counts())

    print("\nCity-wise report:")
    print(report.to_string(index=False))

    print("\nCollection report saved:", report_file)

    failed = report[report["status"] == "FAILED"]

    if not failed.empty:
        print("\nWARNING: Some cities failed collection.")
        print(failed["city"].tolist())
    else:
        print("\nAll cities have valid data.")


# ==========================================
# MAIN EXECUTION
# ==========================================

if __name__ == "__main__":

    try:
        collect_all_cities()

    except Exception as error:
        print("\nCOLLECTION ERROR:", error)

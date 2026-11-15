
from fastapi import APIRouter, HTTPException, Query
import pandas as pd

from backend.config import CACHE_DIR

from backend.utils.data_loader import (
    load_trend_results,
    load_annual_averages,
    load_forecasts,
    load_city_clusters,
    load_cluster_centers,
    load_opposite_trends,
    load_validation_report,
    get_available_cities,
)

from backend.api.schemas import (
    CitiesResponse,
    DataResponse,
    CityTrendResponse,
)

router = APIRouter()


def dataframe_to_records(df):
    """Convert DataFrame into JSON-safe records."""
    clean_df = df.astype(object).where(df.notna(), None)
    return clean_df.to_dict(orient="records")


def create_response(df):
    records = dataframe_to_records(df)

    return {
        "success": True,
        "total_records": len(records),
        "data": records,
    }


@router.get("/cities", response_model=CitiesResponse)
def get_cities():
    cities = get_available_cities()

    return {
        "total_cities": len(cities),
        "cities": [{"n": city} for city in cities],
    }


@router.get("/series", response_model=DataResponse)
def get_series(city: str | None = Query(default=None)):
    """Load monthly city data from existing cache CSV files."""

    files = sorted(CACHE_DIR.glob("*_monthly.csv"))

    if city:
        filename = f"{city.strip().lower()}_monthly.csv"
        files = [
            file for file in files
            if file.name.lower() == filename
        ]

    if not files:
        raise HTTPException(
            status_code=404,
            detail="No monthly data found.",
        )

    frames = []

    for file in files:
        try:
            df = pd.read_csv(file)

            required_columns = {
                "date",
                "precipitation",
                "soil_moisture",
                "city",
            }

            missing_columns = required_columns - set(df.columns)

            if missing_columns:
                raise HTTPException(
                    status_code=500,
                    detail=(
                        f"Invalid columns in {file.name}: "
                        f"{sorted(missing_columns)}"
                    ),
                )

            frames.append(df)

        except pd.errors.ParserError as error:
            raise HTTPException(
                status_code=500,
                detail=f"Could not read {file.name}: {error}",
            )

    result = pd.concat(frames, ignore_index=True)

    return create_response(result)


@router.get("/trends", response_model=DataResponse)
def get_trends(
    variable: str | None = Query(default=None),
):
    df = load_trend_results()

    if variable:
        if "variable" not in df.columns:
            raise HTTPException(
                status_code=500,
                detail="Variable column not found.",
            )

        df = df[
            df["variable"].astype(str).str.lower()
            == variable.lower()
        ]

    return create_response(df)


@router.get("/trends/city/{city}", response_model=CityTrendResponse)
def get_city_trends(city: str):
    df = load_trend_results()

    if "city" not in df.columns:
        raise HTTPException(
            status_code=500,
            detail="City column not found.",
        )

    result = df[
        df["city"].astype(str).str.lower() == city.lower()
    ]

    if result.empty:
        raise HTTPException(
            status_code=404,
            detail=f"No trend data found for {city}.",
        )

    return {
        "success": True,
        "city": city,
        "total_records": len(result),
        "data": dataframe_to_records(result),
    }


@router.get("/annual-averages", response_model=DataResponse)
def get_annual_averages():
    return create_response(load_annual_averages())


@router.get("/forecasts", response_model=DataResponse)
def get_forecasts(
    city: str | None = Query(default=None),
    variable: str | None = Query(default=None),
):
    df = load_forecasts()

    if city and "city" in df.columns:
        df = df[
            df["city"].astype(str).str.lower()
            == city.lower()
        ]

    if variable and "variable" in df.columns:
        df = df[
            df["variable"].astype(str).str.lower()
            == variable.lower()
        ]

    return create_response(df)


@router.get("/clusters", response_model=DataResponse)
def get_clusters():
    return create_response(load_city_clusters())


@router.get("/cluster-centers", response_model=DataResponse)
def get_cluster_centers():
    return create_response(load_cluster_centers())


@router.get("/opposite-trends", response_model=DataResponse)
def get_opposite_trends():
    return create_response(load_opposite_trends())


@router.get("/validation", response_model=DataResponse)
def get_validation_report():
    return create_response(load_validation_report())

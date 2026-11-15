
from pydantic import BaseModel
from typing import Any, Optional


class HealthResponse(BaseModel):
    status: str
    message: str
    version: str


class CitiesResponse(BaseModel):
    total_cities: int
    cities: list[dict[str, Any]]


class DataResponse(BaseModel):
    success: bool
    total_records: int
    data: list[dict[str, Any]]


class CityTrendResponse(BaseModel):
    success: bool
    city: str
    total_records: int
    data: list[dict[str, Any]]


class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    detail: Optional[str] = None

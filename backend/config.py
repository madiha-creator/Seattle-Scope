
from pathlib import Path

# Main project directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Existing project directories
SRC_DIR = BASE_DIR / "src"
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
CACHE_DIR = DATA_DIR / "cache"

# Existing generated results
OUTPUT_DIR = BASE_DIR / "outputs"

# API configuration
APP_NAME = "NASA Earth System Trend Detective API"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = (
    "Backend API for climate trend analysis, "
    "forecasting, clustering and opposite trend detection."
)

# API settings
API_PREFIX = "/api"

# CORS settings
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
]

# Existing output CSV files
TREND_RESULTS_FILE = OUTPUT_DIR / "all_cities_trend_results.csv"
ANNUAL_AVERAGES_FILE = OUTPUT_DIR / "all_cities_annual_averages.csv"
FORECAST_FILE = OUTPUT_DIR / "monthly_10_year_forecasts.csv"
CLUSTERS_FILE = OUTPUT_DIR / "city_clusters.csv"
CLUSTER_CENTERS_FILE = OUTPUT_DIR / "cluster_centers.csv"
OPPOSITE_TRENDS_FILE = OUTPUT_DIR / "opposite_trends.csv"
VALIDATION_FILE = OUTPUT_DIR / "manual_validation_report.csv"


from pathlib import Path

# ==========================================
# PROJECT DIRECTORIES
# ==========================================

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
CACHE_DIR = DATA_DIR / "cache"
OUTPUT_DIR = BASE_DIR / "outputs"


# ==========================================
# NASA POWER API SETTINGS
# ==========================================

NASA_API_URL = (
    "https://power.larc.nasa.gov/"
    "api/temporal/monthly/point"
)

PARAMETERS = [
    "PRECTOTCORR",
    "GWETROOT"
]

START_YEAR = 1981
END_YEAR = 2025


# ==========================================
# 39 GLOBAL CITIES
# ==========================================

CITIES = [

    # ASIA - 8 CITIES
    {
        "city": "Islamabad",
        "continent": "Asia",
        "latitude": 33.6844,
        "longitude": 73.0479
    },
    {
        "city": "Delhi",
        "continent": "Asia",
        "latitude": 28.6139,
        "longitude": 77.2090
    },
    {
        "city": "Beijing",
        "continent": "Asia",
        "latitude": 39.9042,
        "longitude": 116.4074
    },
    {
        "city": "Tokyo",
        "continent": "Asia",
        "latitude": 35.6762,
        "longitude": 139.6503
    },
    {
        "city": "Bangkok",
        "continent": "Asia",
        "latitude": 13.7563,
        "longitude": 100.5018
    },
    {
        "city": "Riyadh",
        "continent": "Asia",
        "latitude": 24.7136,
        "longitude": 46.6753
    },
    {
        "city": "Dhaka",
        "continent": "Asia",
        "latitude": 23.8103,
        "longitude": 90.4125
    },
    {
        "city": "Jakarta",
        "continent": "Asia",
        "latitude": -6.2088,
        "longitude": 106.8456
    },

    # AFRICA - 7 CITIES
    {
        "city": "Cairo",
        "continent": "Africa",
        "latitude": 30.0444,
        "longitude": 31.2357
    },
    {
        "city": "Lagos",
        "continent": "Africa",
        "latitude": 6.5244,
        "longitude": 3.3792
    },
    {
        "city": "Nairobi",
        "continent": "Africa",
        "latitude": -1.2921,
        "longitude": 36.8219
    },
    {
        "city": "Cape_Town",
        "continent": "Africa",
        "latitude": -33.9249,
        "longitude": 18.4241
    },
    {
        "city": "Addis_Ababa",
        "continent": "Africa",
        "latitude": 8.9806,
        "longitude": 38.7578
    },
    {
        "city": "Accra",
        "continent": "Africa",
        "latitude": 5.6037,
        "longitude": -0.1870
    },
    {
        "city": "Casablanca",
        "continent": "Africa",
        "latitude": 33.5731,
        "longitude": -7.5898
    },

    # EUROPE - 7 CITIES
    {
        "city": "London",
        "continent": "Europe",
        "latitude": 51.5072,
        "longitude": -0.1276
    },
    {
        "city": "Paris",
        "continent": "Europe",
        "latitude": 48.8566,
        "longitude": 2.3522
    },
    {
        "city": "Berlin",
        "continent": "Europe",
        "latitude": 52.5200,
        "longitude": 13.4050
    },
    {
        "city": "Rome",
        "continent": "Europe",
        "latitude": 41.9028,
        "longitude": 12.4964
    },
    {
        "city": "Madrid",
        "continent": "Europe",
        "latitude": 40.4168,
        "longitude": -3.7038
    },
    {
        "city": "Moscow",
        "continent": "Europe",
        "latitude": 55.7558,
        "longitude": 37.6173
    },
    {
        "city": "Stockholm",
        "continent": "Europe",
        "latitude": 59.3293,
        "longitude": 18.0686
    },

    # NORTH AMERICA - 7 CITIES
    {
        "city": "New_York",
        "continent": "North America",
        "latitude": 40.7128,
        "longitude": -74.0060
    },
    {
        "city": "Los_Angeles",
        "continent": "North America",
        "latitude": 34.0522,
        "longitude": -118.2437
    },
    {
        "city": "Mexico_City",
        "continent": "North America",
        "latitude": 19.4326,
        "longitude": -99.1332
    },
    {
        "city": "Toronto",
        "continent": "North America",
        "latitude": 43.6532,
        "longitude": -79.3832
    },
    {
        "city": "Miami",
        "continent": "North America",
        "latitude": 25.7617,
        "longitude": -80.1918
    },
    {
        "city": "Chicago",
        "continent": "North America",
        "latitude": 41.8781,
        "longitude": -87.6298
    },
    {
        "city": "Vancouver",
        "continent": "North America",
        "latitude": 49.2827,
        "longitude": -123.1207
    },

    # SOUTH AMERICA - 7 CITIES
    {
        "city": "Sao_Paulo",
        "continent": "South America",
        "latitude": -23.5505,
        "longitude": -46.6333
    },
    {
        "city": "Buenos_Aires",
        "continent": "South America",
        "latitude": -34.6037,
        "longitude": -58.3816
    },
    {
        "city": "Lima",
        "continent": "South America",
        "latitude": -12.0464,
        "longitude": -77.0428
    },
    {
        "city": "Bogota",
        "continent": "South America",
        "latitude": 4.7110,
        "longitude": -74.0721
    },
    {
        "city": "Santiago",
        "continent": "South America",
        "latitude": -33.4489,
        "longitude": -70.6693
    },
    {
        "city": "Quito",
        "continent": "South America",
        "latitude": -0.1807,
        "longitude": -78.4678
    },
    {
        "city": "Manaus",
        "continent": "South America",
        "latitude": -3.1190,
        "longitude": -60.0217
    },

    # OCEANIA - 3 CITIES
    {
        "city": "Sydney",
        "continent": "Oceania",
        "latitude": -33.8688,
        "longitude": 151.2093
    },
    {
        "city": "Melbourne",
        "continent": "Oceania",
        "latitude": -37.8136,
        "longitude": 144.9631
    },
    {
        "city": "Auckland",
        "continent": "Oceania",
        "latitude": -36.8509,
        "longitude": 174.7645
    }
]


# ==========================================
# TEMPORARY TEST LOCATION
# ==========================================

TEST_CITY = "Islamabad"
TEST_LATITUDE = 33.6844
TEST_LONGITUDE = 73.0479


# ==========================================
# LOCATION VALIDATION
# ==========================================

CITY_COUNT = len(CITIES)

city_names = [
    location["city"]
    for location in CITIES
]

if len(city_names) != len(set(city_names)):
    raise ValueError("Duplicate city names found!")

for location in CITIES:

    if not -90 <= location["latitude"] <= 90:
        raise ValueError(
            f"Invalid latitude: {location['city']}"
        )

    if not -180 <= location["longitude"] <= 180:
        raise ValueError(
            f"Invalid longitude: {location['city']}"
        )

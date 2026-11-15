
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from backend.config import (
    APP_NAME,
    APP_VERSION,
    APP_DESCRIPTION,
    API_PREFIX,
    CORS_ORIGINS,
)

from backend.api.routes import router


app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description=APP_DESCRIPTION,
)

# Allow frontend applications to access the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes
app.include_router(
    router,
    prefix=API_PREFIX,
    tags=["NASA Data Science"],
)

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "dist"


@app.get("/")
def home():
    index_file = FRONTEND_DIR / "index.html"
    if index_file.is_file():
        return FileResponse(index_file)

    return {
        "success": True,
        "message": "NASA Earth System Trend Detective API is running!",
        "version": APP_VERSION,
        "documentation": "/docs",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "message": "Backend is running successfully.",
        "version": APP_VERSION,
    }


if FRONTEND_DIR.is_dir():
    app.frontend("/", directory=str(FRONTEND_DIR))

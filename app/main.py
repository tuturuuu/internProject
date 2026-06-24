import logging
import sys
import time
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import router as api_router

import os
print("REDIS_URL =", os.getenv("REDIS_URL", "NOT SET"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)

APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR.parent / "dist"

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

app = FastAPI(
    title="Sentinel Service",
    version="1.0.0",
    description="Application settings for Behavioral RAG system",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(api_router)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "Behavioral RAG",
        "timestamp": time.time(),
    }


if STATIC_DIR.exists():
    # Serve JS/CSS/assets
    app.mount(
        "/assets",
        StaticFiles(directory=STATIC_DIR / "assets"),
        name="assets",
    )

    # Serve SPA for all non-API routes
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        return FileResponse(STATIC_DIR / "index.html")

else:
    @app.get("/")
    async def root():
        return {
            "service": "Behavioral RAG",
            "version": "1.0.0",
            "message": "Frontend build not found",
            "docs_url": "/docs",
        }
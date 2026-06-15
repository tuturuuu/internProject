import logging
import sys
import time
from pathlib import Path

from fastapi import FastAPI

from app.api.router import router as api_router


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))


logger = logging.getLogger(__name__)



app = FastAPI(
    title="Sentinel Service",
    version="1.0.0",
    description="Application settings for Behavioral RAG system",
)

from fastapi.middleware.cors import CORSMiddleware

# Allow the frontend dev server and localhost to access the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

# Merge CORS configurations from both services

@app.get("/")
async def root():
    """Service information endpoint"""
    return {
        "service": "Behavorial RAG",
        "version": "1.0.0",
        "message": "Application settings for Behavioral RAG system",
        "docs_url": "/docs",

    }


@app.get("/health")
async def health():
    """Combined health check endpoint"""
    return {
        "status": "ok",
        "service": "Behavorial RAG",
        "timestamp": time.time(),
    }



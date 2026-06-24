from typing import List
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/frontend", tags=["frontend"])

# Frontend data built from data/business.json (keeps mocked images)
import json
import random
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[3] / "data" / "business.json"
try:
    with open(DATA_FILE, "r", encoding="utf-8") as fh:
        _businesses = json.load(fh)
except Exception:
    _businesses = []

# simple price mapper
def _price_label(price_range: str):
    if not price_range:
        return "$"
    pr = price_range.lower()
    if "0-100" in pr or pr.startswith("0"):
        return "$"
    if "100-250" in pr or "100-250k" in pr:
        return "$$"
    if "250-500" in pr or "500" in pr:
        return "$$$"
    return "$$"

# mocked images to keep visual fidelity
_TREND_IMG = [
    "https://images.unsplash.com/photo-1553621042-f6e147245754?w=400&h=220&fit=crop",
    "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=400&h=220&fit=crop",
    "https://images.unsplash.com/photo-1544025162-d76694265947?w=400&h=220&fit=crop",
    "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=400&h=220&fit=crop",
]

_RECO_IMG = [
    "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=800&h=400&fit=crop",
    "https://images.unsplash.com/photo-1424847651672-bf20a4b0982b?w=800&h=400&fit=crop",
]

# Build trending and recommended lists from the JSON data. Fall back to empty lists if file missing.
trending = []
recommended = []

for i, b in enumerate(_businesses[:8]):
    trending.append(
        {
            "id": b.get("id", i + 1),
            "name": b.get("name", f"Business {i+1}"),
            "type": b.get("cuisine", "Various"),
            "distance": f"{round(0.5 + i * 0.7, 1)} miles",
            "rating": b.get("rating", 4.5),
            "price": _price_label(b.get("price_range", "")),
            "tags": b.get("tags", [])[:3],
            "image": _TREND_IMG[i % len(_TREND_IMG)],
        }
    )

# take some businesses further down for recommended
for i, b in enumerate(_businesses[8:12]):
    recommended.append(
        {
            "id": b.get("id", f"rec-{i+1}"),
            "name": b.get("name", f"Recommended {i+1}"),
            "reviews": random.randint(20, 300),
            "rating": b.get("rating", 4),
            "description": f"{b.get('name','')} — {b.get('cuisine','Great food')} with local favorites and seasonal menus.",
            "metrics": [
                {"label": "Flavor", "value": random.randint(80, 99)},
                {"label": "Service", "value": random.randint(75, 95)},
            ],
            "image": _RECO_IMG[i % len(_RECO_IMG)],
        }
    )

# If file was empty, keep the previous hard-coded fallback minimal list
if not trending:
    trending = [
        {
            "id": 1,
            "name": "Orizuru Sushi",
            "type": "Modern Japanese",
            "distance": "0.8 miles",
            "rating": 4.9,
            "price": "$$$",
            "tags": ["Chef's Table", "Omakase"],
            "image": _TREND_IMG[0],
        }
    ]

if not recommended:
    recommended = [
        {
            "id": "r1",
            "name": "The Azure Terrace",
            "reviews": 124,
            "rating": 4,
            "description": "Experience authentic coastal cuisine with ingredients sourced daily from local harbors.",
            "metrics": [{"label": "Flavor", "value": 98}, {"label": "Service", "value": 92}],
            "image": _RECO_IMG[0],
        }
    ]


@router.get("/trending")
async def get_trending():
    """Return mocked trending restaurants"""
    return trending


@router.get("/recommended")
async def get_recommended():
    """Return mocked recommended restaurants"""
    return recommended


@router.get("/home")
async def get_home():
    """Return combined frontend data"""
    return {"trending": trending, "recommended": recommended}


@router.get("/businesses")
async def get_businesses():
    """Return all businesses from the dataset"""
    return _businesses


class UserHistoryRequest(BaseModel):
    user_id: str
    history: List[str]


@router.post("/history")
async def save_history(request: UserHistoryRequest):
    """Save user history to Redis"""
    from app.services.redis_service import save_user_history
    success = save_user_history(request.user_id, request.history)
    if not success:
        return {"status": "error", "message": "Failed to save history to Redis"}
    return {"status": "success", "user_id": request.user_id}


@router.get("/history")
async def get_history(user_id: str):
    """Load user history from Redis"""
    from app.services.redis_service import get_user_history
    history = get_user_history(user_id)
    return {"user_id": user_id, "history": history}

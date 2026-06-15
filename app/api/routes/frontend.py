from fastapi import APIRouter

router = APIRouter(prefix="/frontend", tags=["frontend"])

# Mocked frontend data to be consumed by the React app
trending = [
    {
        "id": 1,
        "name": "Orizuru Sushi",
        "type": "Modern Japanese",
        "distance": "0.8 miles",
        "rating": 4.9,
        "price": "$$$",
        "tags": ["Chef's Table", "Omakase"],
        "image": "https://images.unsplash.com/photo-1553621042-f6e147245754?w=400&h=220&fit=crop",
    },
    {
        "id": 2,
        "name": "La Lanterna",
        "type": "Authentic Italian",
        "distance": "1.2 miles",
        "rating": 4.7,
        "price": "$$",
        "tags": ["Handmade Pasta"],
        "image": "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=400&h=220&fit=crop",
    },
    {
        "id": 3,
        "name": "Iron & Oak",
        "type": "Modern Grill",
        "distance": "2.5 miles",
        "rating": 4.8,
        "price": "$$$$",
        "tags": ["Dry Aged", "Cocktails"],
        "image": "https://images.unsplash.com/photo-1544025162-d76694265947?w=400&h=220&fit=crop",
    },
    {
        "id": 4,
        "name": "Verdant Kitchen",
        "type": "Plant-Based",
        "distance": "3.1 miles",
        "rating": 4.6,
        "price": "$$",
        "tags": ["Sustainable"],
        "image": "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=400&h=220&fit=crop",
    },
]

recommended = [
    {
        "id": 1,
        "name": "The Azure Terrace",
        "reviews": 124,
        "rating": 4,
        "description": "Experience authentic coastal cuisine with ingredients sourced daily from local harbors. Chef Maria's signature…",
        "metrics": [
            {"label": "Flavor", "value": 98},
            {"label": "Service", "value": 92},
        ],
        "image": "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=800&h=400&fit=crop",
    },
    {
        "id": 2,
        "name": "Heritage Bistro",
        "reviews": 89,
        "rating": 4,
        "description": "A refined take on classic French bistro fare. From the perfect onion soup to delicate soufflés, Heritage brings the soul of…",
        "metrics": [
            {"label": "Flavor", "value": 95},
            {"label": "Value", "value": 88},
        ],
        "image": "https://images.unsplash.com/photo-1424847651672-bf20a4b0982b?w=800&h=400&fit=crop",
    },
]


@router.get("/trending")
async def get_trending():
    """Return mocked trending restaurants"""
    return trending


@router.get("/recommended")
async def get_recommended():
    """Return mocked recommended restaurants"""
    return recommended

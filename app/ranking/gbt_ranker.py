import json
import random
from collections import Counter
from functools import lru_cache
from pathlib import Path

from fastapi import HTTPException


ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
MODELS_DIR = ROOT_DIR / "models"
MODEL_PATH = MODELS_DIR / "ordered_xgboost.json"
METADATA_PATH = MODELS_DIR / "ordered_xgboost_metadata.json"


def parse_prep_time(value):
    if not value:
        return 0.0
    text = str(value).strip().lower()
    if text.endswith("min"):
        text = text[:-3].strip()
    try:
        return float(text)
    except ValueError:
        return 0.0


@lru_cache(maxsize=1)
def load_business_by_id():
    with open(DATA_DIR / "business.json", "r", encoding="utf-8") as file_handle:
        businesses = json.load(file_handle)
    return {business["id"]: business for business in businesses}


@lru_cache(maxsize=1)
def load_model_assets():
    try:
        import xgboost as xgb
    except ImportError as error:
        raise RuntimeError("xgboost is not installed") from error

    with open(METADATA_PATH, "r", encoding="utf-8") as file_handle:
        metadata = json.load(file_handle)

    booster = xgb.Booster()
    booster.load_model(str(MODEL_PATH))
    return booster, metadata


def build_feature_schema(business_by_id):
    cuisines = sorted({business["cuisine"] for business in business_by_id.values()})
    price_ranges = sorted({business["price_range"] for business in business_by_id.values()})

    tag_counter = Counter()
    for business in business_by_id.values():
        tag_counter.update(business["tags"])
    top_tags = [tag for tag, _ in tag_counter.most_common(50)]

    return {
        "cuisines": cuisines,
        "price_ranges": price_ranges,
        "top_tags": top_tags,
    }


def build_user_profile(history_ids, business_by_id):
    valid_restaurants = [
        business_by_id[restaurant_id]
        for restaurant_id in history_ids
        if restaurant_id in business_by_id
    ]

    if not valid_restaurants:
        raise HTTPException(status_code=400, detail="history must contain at least one valid restaurant id")

    cuisine_counts = Counter(restaurant["cuisine"] for restaurant in valid_restaurants)
    price_counts = Counter(restaurant["price_range"] for restaurant in valid_restaurants)
    tag_counts = Counter(tag for restaurant in valid_restaurants for tag in restaurant["tags"])
    ratings = [float(restaurant["rating"]) for restaurant in valid_restaurants]

    dominant_cuisine = cuisine_counts.most_common(1)[0][0]
    dominant_price = price_counts.most_common(1)[0][0]
    cuisine_diversity = len(cuisine_counts) / len(valid_restaurants)

    return {
        "history_length": len(valid_restaurants),
        "average_rating": sum(ratings) / len(ratings),
        "dominant_cuisine": dominant_cuisine,
        "dominant_price": dominant_price,
        "tag_counts": tag_counts,
        "user_tags": set(tag_counts),
        "user_cuisine_diversity": cuisine_diversity,
        "user_reorder_rate": max(0.1, min(0.95, 1.0 - (cuisine_diversity * 0.75))),
        "user_avg_basket_size": float(max(1.0, min(8.0, len(valid_restaurants) / 2.0))),
        "user_order_frequency_per_week": float(max(0.5, min(7.0, len(valid_restaurants) / 2.0))),
    }


def encode_row(user_profile, business, schema):
    business_tags = set(business["tags"])

    features = [
        user_profile["user_reorder_rate"],
        user_profile["user_avg_basket_size"],
        user_profile["user_order_frequency_per_week"],
        user_profile["user_cuisine_diversity"],
        float(user_profile["history_length"]),
        float(user_profile["average_rating"]),
        float(business["rating"]),
        1.0 if business["open"] else 0.0,
        parse_prep_time(business.get("prep_time")),
        1.0 if business["cuisine"] == user_profile["dominant_cuisine"] else 0.0,
        1.0 if business["price_range"] == user_profile["dominant_price"] else 0.0,
        float(business["rating"]) - float(user_profile["average_rating"]),
    ]

    features.extend(
        1.0 if cuisine == user_profile["dominant_cuisine"] else 0.0
        for cuisine in schema["cuisines"]
    )
    features.extend(
        1.0 if price_range == user_profile["dominant_price"] else 0.0
        for price_range in schema["price_ranges"]
    )
    features.extend(
        1.0 if cuisine == business["cuisine"] else 0.0
        for cuisine in schema["cuisines"]
    )
    features.extend(
        1.0 if price_range == business["price_range"] else 0.0
        for price_range in schema["price_ranges"]
    )
    features.extend(
        1.0 if tag in user_profile["user_tags"] else 0.0
        for tag in schema["top_tags"]
    )
    features.extend(
        1.0 if tag in business_tags else 0.0
        for tag in schema["top_tags"]
    )

    return features


def sample_businesses(history_ids, sample_size):
    business_by_id = load_business_by_id()
    unseen_businesses = [
        business
        for business_id, business in business_by_id.items()
        if business_id not in history_ids
    ]
    pool = unseen_businesses if len(unseen_businesses) >= sample_size else list(business_by_id.values())
    sample_size = min(sample_size, len(pool))
    return random.sample(pool, sample_size)


def score_businesses_with_xgb(history, candidate_businesses):
    business_by_id = load_business_by_id()
    booster, metadata = load_model_assets()
    schema = build_feature_schema(business_by_id)
    user_profile = build_user_profile(history, business_by_id)

    try:
        import xgboost as xgb
    except ImportError as error:
        raise HTTPException(status_code=500, detail="xgboost is not installed") from error

    features = [
        encode_row(user_profile, business, schema)
        for business in candidate_businesses
    ]
    matrix = xgb.DMatrix(features, feature_names=metadata["feature_names"])
    probabilities = booster.predict(matrix)

    scored = []
    for business, probability in zip(candidate_businesses, probabilities):
        score = float(probability)
        scored.append(
            {
                "restaurant_id": business["id"],
                "name": business["name"],
                "score": score,
                "label": 1 if score >= 0.0 else 0,
            }
        )

    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored


def recommend_businesses(history, sample_size, top_k=3):
    candidate_businesses = sample_businesses(set(history), sample_size)
    scored = score_businesses_with_xgb(history, candidate_businesses)

    return {
        "candidates_sampled": len(candidate_businesses),
        "recommendations": scored[:top_k],
    }

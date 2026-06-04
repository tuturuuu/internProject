import json
import random
from collections import Counter
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"


def load_business_by_id():
    with open(DATA_DIR / "business.json", "r", encoding="utf-8") as file_handle:
        business_rows = json.load(file_handle)
    return {row["id"]: row for row in business_rows}


def load_users():
    with open(DATA_DIR / "user_history.json", "r", encoding="utf-8") as file_handle:
        return json.load(file_handle)


def load_all_businesses():
    with open(DATA_DIR / "business.json", "r", encoding="utf-8") as file_handle:
        return json.load(file_handle)


def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def build_profile(user_row, business_by_id):
    cuisine_counts = Counter()
    tag_counts = Counter()
    price_counts = Counter()
    ratings = []

    for restaurant_id in user_row["history"]:
        restaurant = business_by_id[restaurant_id]
        cuisine_counts[restaurant["cuisine"]] += 1
        price_counts[restaurant["price_range"]] += 1
        ratings.append(float(restaurant["rating"]))
        tag_counts.update(restaurant["tags"])

    return {
        "cuisine_counts": cuisine_counts,
        "tag_counts": tag_counts,
        "price_counts": price_counts,
        "average_rating": round(sum(ratings) / len(ratings), 2) if ratings else 0.0,
        "dominant_cuisine": cuisine_counts.most_common(1)[0][0] if cuisine_counts else None,
        "dominant_price": price_counts.most_common(1)[0][0] if price_counts else None,
    }


def score_restaurant(restaurant, profile, rng=None):
    score = 0.0
    rng = rng or random

    if restaurant["cuisine"] == profile["dominant_cuisine"]:
        score += 3.0

    tag_overlap = sum(
        profile["tag_counts"].get(tag, 0)
        for tag in restaurant["tags"]
    )
    score += min(3.0, tag_overlap / 5)

    rating = float(restaurant["rating"])
    if rating >= 4.8:
        score += 1.0
    elif rating >= 4.5:
        score += 0.5

    if restaurant["price_range"] == profile["dominant_price"]:
        score += 0.5

    score += rng.uniform(-0.2, 0.2)

    return max(0.0, score)


def recommendation_fraction(user_row, rng=None):
    behavior_profile = user_row["behavior_profile"]
    reorder_rate = float(behavior_profile["reorder_rate"])
    cuisine_diversity = float(behavior_profile["cuisine_diversity"])
    rng = rng or random

    fraction = 0.12 + (0.18 * reorder_rate) - (0.06 * cuisine_diversity)
    fraction += rng.uniform(-0.03, 0.03)
    return clamp(fraction, 0.08, 0.30)


def rank_candidates(user_row, business_by_id, candidate_ids=None, rng=None):
    rng = rng or random
    profile = build_profile(user_row, business_by_id)
    ranked = []
    history_ids = set(user_row["history"])

    if candidate_ids is None:
        candidate_ids = [
            restaurant_id
            for restaurant_id in business_by_id
            if restaurant_id not in history_ids
        ]

    for restaurant_id in candidate_ids:
        restaurant = business_by_id[restaurant_id]
        ranked.append(
            {
                "restaurant_id": restaurant_id,
                "restaurant": restaurant,
                "score": score_restaurant(restaurant, profile, rng=rng),
            }
        )

    ranked.sort(
        key=lambda item: (
            item["score"],
            float(item["restaurant"]["rating"]),
            item["restaurant"]["name"],
        ),
        reverse=True,
    )

    positive_count = max(
        1,
        round(len(ranked) * recommendation_fraction(user_row, rng=rng)),
    )

    positive_ids = {
        item["restaurant_id"]
        for item in ranked[:positive_count]
    }

    return {
        "profile": profile,
        "ranked": ranked,
        "positive_count": positive_count,
        "positive_ids": positive_ids,
    }

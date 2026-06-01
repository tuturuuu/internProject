import json
import random
from collections import Counter

# -----------------------------
# Load restaurant cards
# -----------------------------
with open("processed_file.json", "r", encoding="utf-8") as f:
    restaurant_cards = json.load(f)

# -----------------------------
# Group restaurants by cuisine
# -----------------------------
restaurants_by_cuisine = {}

for restaurant in restaurant_cards:
    cuisine = restaurant["cuisine"]

    if cuisine not in restaurants_by_cuisine:
        restaurants_by_cuisine[cuisine] = []

    restaurants_by_cuisine[cuisine].append(restaurant)

available_cuisines = list(restaurants_by_cuisine.keys())

# -----------------------------
# Generate users
# -----------------------------
NUM_USERS = 20

users = []

for user_idx in range(1, NUM_USERS + 1):

    # User likes 1-3 cuisines
    num_preferences = random.randint(1, 3)

    preferred_cuisines = random.sample(
        available_cuisines,
        min(num_preferences, len(available_cuisines))
    )

    # Candidate restaurants from preferred cuisines
    candidate_restaurants = []

    for cuisine in preferred_cuisines:
        candidate_restaurants.extend(
            restaurants_by_cuisine[cuisine]
        )

    # Remove duplicates
    unique_restaurants = {
        restaurant["id"]: restaurant
        for restaurant in candidate_restaurants
    }

    candidate_restaurants = list(
        unique_restaurants.values()
    )

    # History size
    history_size = min(
        random.randint(5, 10),
        len(candidate_restaurants)
    )

    history_restaurants = random.sample(
        candidate_restaurants,
        history_size
    )

    # -----------------------------
    # Behavioral features
    # -----------------------------

    history_cuisines = [
        restaurant["cuisine"]
        for restaurant in history_restaurants
    ]

    cuisine_counter = Counter(history_cuisines)

    cuisine_diversity = round(
        len(set(history_cuisines))
        / len(history_cuisines),
        2
    )

    # Loyal users tend to have lower diversity
    reorder_rate = round(
        random.uniform(
            max(0.3, 1 - cuisine_diversity),
            0.95
        ),
        2
    )

    avg_basket_size = random.randint(1, 8)

    order_frequency_per_week = round(
        random.uniform(0.5, 7.0),
        1
    )

    users.append({
        "user_id": f"u{user_idx}",

        "history": [
            restaurant["id"]
            for restaurant in history_restaurants
        ],

        "behavior_profile": {
            "reorder_rate": reorder_rate,
            "avg_basket_size": avg_basket_size,
            "order_frequency_per_week": order_frequency_per_week,
            "cuisine_diversity": cuisine_diversity
        }
    })

# -----------------------------
# Export
# -----------------------------
with open(
    "user_history.json",
    "w",
    encoding="utf-8"
) as f:
    json.dump(
        users,
        f,
        indent=2,
        ensure_ascii=False
    )

print(f"Generated {len(users)} users")
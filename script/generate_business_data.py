import pandas as pd
import random

# -----------------------------
# Load business data
# -----------------------------
df_bus = pd.read_json(
    "./yelp_academic_dataset_business.json",
    lines=True
)

df_bus = df_bus[
    (df_bus["city"] == "Nashville") &
    (df_bus["stars"] > 4.0) &
    (df_bus["is_open"] == 1)
]

# -----------------------------
# Config
# -----------------------------
CUISINES = [
    "Vietnamese",
    "Chinese",
    "Japanese",
    "Thai",
    "Korean",
    "Indian",
    "Mexican",
    "Italian",
    "American",
    "Mediterranean",
    "Greek",
    "French"
]

PRICE_MAPPING = {
    "1": "0-100k",
    "2": "100-250k",
    "3": "250-500k",
    "4": "500k+"
}

ATTRIBUTE_TAGS = {
    "RestaurantsTakeOut": "takeout",
    "RestaurantsDelivery": "delivery",
    "OutdoorSeating": "outdoor-seating",
    "GoodForKids": "family-friendly",
    "BikeParking": "bike-parking",
    "WheelchairAccessible": "accessible",
    "RestaurantsReservations": "reservations",
    "GoodForGroups": "group-friendly",
    "HasTV": "has-tv",
    "DogsAllowed": "dog-friendly"
}

PREP_TIME_MAPPING = {
    "Vietnamese": "15 min",
    "Chinese": "20 min",
    "Japanese": "20 min",
    "Thai": "20 min",
    "Korean": "25 min",
    "Indian": "25 min",
    "Mexican": "15 min",
    "Italian": "25 min",
    "American": "15 min",
    "Mediterranean": "20 min",
    "Greek": "20 min",
    "French": "30 min"
}

def extract_cuisine(categories):
    if pd.isna(categories):
        return "American"

    categories = str(categories)

    for cuisine in CUISINES:
        if cuisine.lower() in categories.lower():
            return cuisine

    return "American"


def extract_price_range(attributes):
    if not isinstance(attributes, dict):
        return "100-250k"

    price = attributes.get("RestaurantsPriceRange2")

    if price is None:
        return "100-250k"

    return PRICE_MAPPING.get(str(price), "100-250k")

def extract_tags(categories, attributes):
    tags = []

    # Categories -> tags
    if pd.notna(categories):

        category_tags = [
            c.strip().lower()
            for c in str(categories).split(",")
        ]

        tags.extend(category_tags)

    # Yelp attributes -> tags
    if isinstance(attributes, dict):

        for attr_name, tag_name in ATTRIBUTE_TAGS.items():

            value = attributes.get(attr_name)

            if str(value).lower() == "true":
                tags.append(tag_name)

    # cleanup
    tags = [
        t for t in tags
        if t not in ["restaurants", "food"]
    ]

    # unique while preserving order
    tags = list(dict.fromkeys(tags))

    return tags[:10]

restaurant_cards = []

sample_df = df_bus.sample(
    min(100, len(df_bus)),
    random_state=42
)

for idx, (_, row) in enumerate(sample_df.iterrows(), start=1):

    cuisine = extract_cuisine(row["categories"])

    restaurant_cards.append({
        "id": row["business_id"],
        "name": row["name"],
        "cuisine": cuisine,
        "tags": extract_tags(
            row["categories"],
            row["attributes"]
        ),
        "price_range": extract_price_range(
            row["attributes"]
        ),
        "rating": round(float(row["stars"]), 1),
        "open": True,
        "prep_time": PREP_TIME_MAPPING.get(
            cuisine,
            "20 min"
        )
    })

pd.DataFrame(restaurant_cards).to_json('processed_file.json', orient="records", indent=1)
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.ranking.reranker import build_feature_schema, build_user_profile, encode_row, load_business_by_id


DATA_DIR = ROOT_DIR / "data"


def load_users():
    with open(DATA_DIR / "user_history.json", "r", encoding="utf-8") as file_handle:
        return json.load(file_handle)


def load_labels():
    with open(DATA_DIR / "user_labels.json", "r", encoding="utf-8") as file_handle:
        return json.load(file_handle)


def build_feature_names(business_by_id):
    schema = build_feature_schema(business_by_id)
    feature_names = [
        "user_reorder_rate",
        "user_avg_basket_size",
        "user_order_frequency_per_week",
        "user_cuisine_diversity",
        "user_history_length",
        "user_average_rating",
        "business_rating",
        "business_open",
        "business_prep_time_minutes",
        "cuisine_match",
        "price_match",
        "rating_gap_to_user_average",
    ]
    feature_names.extend(f"user_dominant_cuisine__{cuisine}" for cuisine in schema["cuisines"])
    feature_names.extend(f"user_dominant_price__{price}" for price in schema["price_ranges"])
    feature_names.extend(f"business_cuisine__{cuisine}" for cuisine in schema["cuisines"])
    feature_names.extend(f"business_price__{price}" for price in schema["price_ranges"])
    feature_names.extend(f"user_tag_presence__{tag}" for tag in schema["top_tags"])
    feature_names.extend(f"business_tag_presence__{tag}" for tag in schema["top_tags"])
    return feature_names, schema


def build_dataset():
    business_by_id = load_business_by_id()
    users = {user_row["user_id"]: user_row for user_row in load_users()}
    labels = load_labels()
    feature_names, schema = build_feature_names(business_by_id)

    rows = []
    for label_row in labels:
        user_row = users[label_row["user_id"]]
        user_profile = build_user_profile(user_row["history"], business_by_id)
        business = business_by_id[label_row["restaurant_id"]]
        rows.append(
            {
                "user_id": label_row["user_id"],
                "restaurant_id": label_row["restaurant_id"],
                "label": int(label_row["ordered"]),
                "features": encode_row(user_profile, business, schema),
            }
        )

    return rows, feature_names


def split_by_user(rows, seed, validation_fraction):
    user_ids = sorted({row["user_id"] for row in rows})
    import random

    random.Random(seed).shuffle(user_ids)

    validation_user_count = max(1, round(len(user_ids) * validation_fraction))
    validation_users = set(user_ids[:validation_user_count])

    train_rows = [row for row in rows if row["user_id"] not in validation_users]
    validation_rows = [row for row in rows if row["user_id"] in validation_users]

    print("Train rows:", len(train_rows))
    print("Validation rows:", len(validation_rows))


    return train_rows, validation_rows, validation_users


def group_rows_by_user(rows):
    grouped_rows = []
    group_sizes = []

    for user_id in sorted({row["user_id"] for row in rows}):
        user_rows = [row for row in rows if row["user_id"] == user_id]
        grouped_rows.extend(user_rows)
        group_sizes.append(len(user_rows))


    
    return grouped_rows, group_sizes


def discounted_cumulative_gain(relevances, k):
    import math

    gain = 0.0
    for index, relevance in enumerate(relevances[:k]):
        gain += (2**relevance - 1) / math.log2(index + 2)
    return gain


def ndcg_at_k(y_true, y_score, k=3):
    ordered_pairs = sorted(zip(y_score, y_true), reverse=True)
    ranked_relevances = [label for _, label in ordered_pairs]
    ideal_relevances = sorted(y_true, reverse=True)

    actual_dcg = discounted_cumulative_gain(ranked_relevances, k)
    ideal_dcg = discounted_cumulative_gain(ideal_relevances, k)
    if ideal_dcg == 0:
        return 0.0
    return actual_dcg / ideal_dcg


def mean_group_ndcg_at_k(y_true, y_score, group_sizes, k=3):
    scores = []
    offset = 0
    for group_size in group_sizes:
        group_true = y_true[offset : offset + group_size]
        group_score = y_score[offset : offset + group_size]
        scores.append(ndcg_at_k(group_true, group_score, k=k))
        offset += group_size

    return sum(scores) / max(1, len(scores))


def predict_rows(model, rows, feature_names):
    feature_rows = np.asarray([row["features"] for row in rows], dtype=float)
    try:
        scores = model.predict(feature_rows)
    except TypeError:
        try:
            from catboost import Pool
        except ImportError:
            raise

        scores = model.predict(Pool(feature_rows, feature_names=feature_names))
    return [
        {
            "user_id": row["user_id"],
            "restaurant_id": row["restaurant_id"],
            "ordered": row["label"],
            "score": float(score),
        }
        for row, score in zip(rows, scores)
    ]

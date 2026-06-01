import argparse
import json
import math
import random
from collections import Counter
from pathlib import Path

from user_labeling_utils import DATA_DIR, ROOT_DIR, build_profile, load_business_by_id, load_users


MODELS_DIR = ROOT_DIR / "models"
DEFAULT_MODEL_PATH = MODELS_DIR / "ordered_xgboost.json"
DEFAULT_METADATA_PATH = MODELS_DIR / "ordered_xgboost_metadata.json"
DEFAULT_PREDICTIONS_PATH = MODELS_DIR / "ordered_xgboost_predictions.json"


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


def build_feature_schema(business_by_id):
    cuisines = sorted({business["cuisine"] for business in business_by_id.values()})
    price_ranges = sorted({business["price_range"] for business in business_by_id.values()})

    tag_counter = Counter()
    for business in business_by_id.values():
        tag_counter.update(business["tags"])
    top_tags = [tag for tag, _ in tag_counter.most_common(50)]

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
    feature_names.extend(f"user_dominant_cuisine__{cuisine}" for cuisine in cuisines)
    feature_names.extend(f"user_dominant_price__{price}" for price in price_ranges)
    feature_names.extend(f"business_cuisine__{cuisine}" for cuisine in cuisines)
    feature_names.extend(f"business_price__{price}" for price in price_ranges)
    feature_names.extend(f"user_tag_presence__{tag}" for tag in top_tags)
    feature_names.extend(f"business_tag_presence__{tag}" for tag in top_tags)

    return {
        "cuisines": cuisines,
        "price_ranges": price_ranges,
        "top_tags": top_tags,
        "feature_names": feature_names,
    }


def encode_row(user_row, business, schema, user_profile):
    features = []

    behavior_profile = user_row["behavior_profile"]
    tag_counts = user_profile["tag_counts"]
    user_tags = set(tag_counts)
    business_tags = set(business["tags"])

    features.extend(
        [
            float(behavior_profile["reorder_rate"]),
            float(behavior_profile["avg_basket_size"]),
            float(behavior_profile["order_frequency_per_week"]),
            float(behavior_profile["cuisine_diversity"]),
            float(len(user_row["history"])),
            float(user_profile["average_rating"]),
            float(business["rating"]),
            1.0 if business["open"] else 0.0,
            parse_prep_time(business.get("prep_time")),
            1.0 if business["cuisine"] == user_profile["dominant_cuisine"] else 0.0,
            1.0 if business["price_range"] == user_profile["dominant_price"] else 0.0,
            float(business["rating"]) - float(user_profile["average_rating"]),
        ]
    )

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
        1.0 if tag in user_tags else 0.0
        for tag in schema["top_tags"]
    )
    features.extend(
        1.0 if tag in business_tags else 0.0
        for tag in schema["top_tags"]
    )

    return features


def build_dataset():
    business_by_id = load_business_by_id()
    users = {user_row["user_id"]: user_row for user_row in load_users()}
    labels = json.loads((DATA_DIR / "user_labels.json").read_text(encoding="utf-8"))
    schema = build_feature_schema(business_by_id)

    rows = []
    for label_row in labels:
        user_row = users[label_row["user_id"]]
        user_profile = build_profile(user_row, business_by_id)
        business = business_by_id[label_row["restaurant_id"]]
        rows.append(
            {
                "user_id": label_row["user_id"],
                "restaurant_id": label_row["restaurant_id"],
                "label": int(label_row["ordered"]),
                "features": encode_row(user_row, business, schema, user_profile),
            }
        )

    return rows, schema


def split_by_user(rows, seed, validation_fraction):
    user_ids = sorted({row["user_id"] for row in rows})
    random.Random(seed).shuffle(user_ids)

    validation_user_count = max(1, round(len(user_ids) * validation_fraction))
    validation_users = set(user_ids[:validation_user_count])

    train_rows = [row for row in rows if row["user_id"] not in validation_users]
    validation_rows = [row for row in rows if row["user_id"] in validation_users]
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


def train_model(train_rows, validation_rows, feature_names, args):
    try:
        import xgboost as xgb
    except ImportError as error:
        raise SystemExit(
            "xgboost is not installed. Install it first, then rerun: `pip install xgboost`"
        ) from error

    train_rows, train_group_sizes = group_rows_by_user(train_rows)
    validation_rows, validation_group_sizes = group_rows_by_user(validation_rows)

    train_features = [row["features"] for row in train_rows]
    train_labels = [row["label"] for row in train_rows]

    validation_features = [row["features"] for row in validation_rows]
    validation_labels = [row["label"] for row in validation_rows]

    dtrain = xgb.DMatrix(train_features, label=train_labels, feature_names=feature_names)
    dtrain.set_group(train_group_sizes)
    dvalidation = xgb.DMatrix(
        validation_features,
        label=validation_labels,
        feature_names=feature_names,
    )
    dvalidation.set_group(validation_group_sizes)

    params = {
        "objective": "rank:pairwise",
        "eval_metric": ["ndcg@3", "map"],
        "max_depth": args.max_depth,
        "eta": args.learning_rate,
        "subsample": args.subsample,
        "colsample_bytree": args.colsample_bytree,
        "min_child_weight": args.min_child_weight,
        "lambda": args.l2_regularization,
        "alpha": args.l1_regularization,
        "seed": args.seed,
    }

    booster = xgb.train(
        params=params,
        dtrain=dtrain,
        num_boost_round=args.num_boost_round,
        evals=[(dtrain, "train"), (dvalidation, "validation")],
        early_stopping_rounds=args.early_stopping_rounds,
        verbose_eval=args.verbose_eval,
    )

    validation_scores = booster.predict(dvalidation)
    metrics = {
        "ndcg@3": mean_group_ndcg_at_k(validation_labels, validation_scores, validation_group_sizes, k=3),
        "ndcg@10": mean_group_ndcg_at_k(validation_labels, validation_scores, validation_group_sizes, k=10),
    }
    metrics["best_iteration"] = int(getattr(booster, "best_iteration", -1))
    metrics["best_score"] = float(getattr(booster, "best_score", float("nan")))

    return booster, metrics


def predict_probabilities(booster, rows, feature_names):
    import xgboost as xgb

    matrix = xgb.DMatrix(
        [row["features"] for row in rows],
        feature_names=feature_names,
    )
    scores = booster.predict(matrix)
    return [
        {
            "user_id": row["user_id"],
            "restaurant_id": row["restaurant_id"],
            "ordered": row["label"],
            "score": float(score),
        }
        for row, score in zip(rows, scores)
    ]


def build_feature_importance(booster, feature_names):
    # Get the score mapping (returns {'feature_name_1': gain, 'feature_name_2': gain})
    # booster.get_score() usually returns the feature names if they were passed to DMatrix
    score_map = booster.get_score(importance_type="gain")
    
    importance = []
    
    # If the score_map keys are 'f0', 'f1', we map them to our list
    # If they are the actual feature names, we use them directly
    for i, name in enumerate(feature_names):
        # Check both the 'f{i}' format and the actual name just in case
        gain = score_map.get(f"f{i}", score_map.get(name, 0.0))
        importance.append({"feature": name, "gain": float(gain)})
        
    importance.sort(key=lambda item: item["gain"], reverse=True)
    return importance

def main():
    parser = argparse.ArgumentParser(description="Train an XGBoost model for ordered label prediction.")
    parser.add_argument("--model-path", default=str(DEFAULT_MODEL_PATH))
    parser.add_argument("--metadata-path", default=str(DEFAULT_METADATA_PATH))
    parser.add_argument("--predictions-path", default=str(DEFAULT_PREDICTIONS_PATH))
    parser.add_argument("--validation-fraction", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--num-boost-round", type=int, default=300)
    parser.add_argument("--early-stopping-rounds", type=int, default=20)
    parser.add_argument("--max-depth", type=int, default=2)
    parser.add_argument("--learning-rate", type=float, default=0.05)
    parser.add_argument("--subsample", type=float, default=0.85)
    parser.add_argument("--colsample-bytree", type=float, default=0.85)
    parser.add_argument("--min-child-weight", type=float, default=5.0)
    parser.add_argument("--l2-regularization", type=float, default=10.0)
    parser.add_argument("--l1-regularization", type=float, default=0.0)
    parser.add_argument("--verbose-eval", type=int, default=25)
    args = parser.parse_args()

    rows, schema = build_dataset()
    train_rows, validation_rows, validation_users = split_by_user(
        rows,
        seed=args.seed,
        validation_fraction=args.validation_fraction,
    )

    booster, metrics = train_model(train_rows, validation_rows, schema["feature_names"], args)
    predictions = predict_probabilities(booster, rows, schema["feature_names"])

    model_path = Path(args.model_path)
    metadata_path = Path(args.metadata_path)
    predictions_path = Path(args.predictions_path)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    predictions_path.parent.mkdir(parents=True, exist_ok=True)

    booster.save_model(str(model_path))
    metadata = {
        "model_path": str(model_path),
        "metadata_path": str(metadata_path),
        "feature_names": schema["feature_names"],
        "validation_users": sorted(validation_users),
        "train_rows": len(train_rows),
        "validation_rows": len(validation_rows),
        "metrics": metrics,
        "feature_importance": build_feature_importance(booster, schema["feature_names"]),
    }
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    predictions_path.write_text(json.dumps(predictions, indent=2), encoding="utf-8")

    print(f"Saved model to {model_path}")
    print(f"Saved metadata to {metadata_path}")
    print(f"Saved probability predictions to {predictions_path}")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()

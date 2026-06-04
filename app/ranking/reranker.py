import json
import os
import random
from abc import ABC, abstractmethod
from collections import Counter
from functools import lru_cache
from pathlib import Path

from fastapi import HTTPException


ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
MODELS_DIR = ROOT_DIR / "models"
DEFAULT_METADATA_PATH = MODELS_DIR / "ordered_xgboost_metadata.json"


def resolve_model_path(env_name, default_path):
    return Path(os.environ.get(env_name, str(default_path)))


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


class BaseRankerStrategy(ABC):
    strategy_name = "base"
    label_threshold = 0.5
    model_path = None
    feature_metadata_path = DEFAULT_METADATA_PATH

    def __init__(self):
        self.business_by_id = load_business_by_id()
        self.schema = build_feature_schema(self.business_by_id)
        self.feature_metadata = self._load_feature_metadata()
        self.model = self._load_model()

    def _load_feature_metadata(self):
        with open(self.feature_metadata_path, "r", encoding="utf-8") as file_handle:
            return json.load(file_handle)

    @abstractmethod
    def _load_model(self):
        raise NotImplementedError

    @abstractmethod
    def _predict_scores(self, features):
        raise NotImplementedError

    def score_businesses(self, history, candidate_businesses):
        user_profile = build_user_profile(history, self.business_by_id)
        features = [
            encode_row(user_profile, business, self.schema)
            for business in candidate_businesses
        ]
        scores = self._predict_scores(features)

        scored = []
        for business, score in zip(candidate_businesses, scores):
            numeric_score = float(score)
            scored.append(
                {
                    "restaurant_id": business["id"],
                    "name": business["name"],
                    "score": numeric_score,
                    "label": 1 if numeric_score >= self.label_threshold else 0,
                }
            )

        scored.sort(key=lambda item: item["score"], reverse=True)
        return scored

    def recommend_businesses(self, history, sample_size, top_k=3):
        candidate_businesses = sample_businesses(set(history), sample_size)
        scored = self.score_businesses(history, candidate_businesses)
        return {
            "candidates_sampled": len(candidate_businesses),
            "recommendations": scored[:top_k],
        }


class XGBoostRankerStrategy(BaseRankerStrategy):
    strategy_name = "xgboost"
    model_path = resolve_model_path("ORDERED_XGBOOST_MODEL_PATH", MODELS_DIR / "ordered_xgboost.json")

    def _load_model(self):
        try:
            import xgboost as xgb
        except ImportError as error:
            raise RuntimeError("xgboost is not installed") from error

        if not self.model_path.exists():
            raise FileNotFoundError(f"XGBoost model not found at {self.model_path}")

        booster = xgb.Booster()
        booster.load_model(str(self.model_path))
        return booster

    def _predict_scores(self, features):
        try:
            import xgboost as xgb
        except ImportError as error:
            raise RuntimeError("xgboost is not installed") from error

        matrix = xgb.DMatrix(features, feature_names=self.feature_metadata["feature_names"])
        return self.model.predict(matrix)


class LightGBMRankerStrategy(BaseRankerStrategy):
    strategy_name = "lightgbm"
    model_path = resolve_model_path("ORDERED_LIGHTGBM_MODEL_PATH", MODELS_DIR / "ordered_lightgbm.txt")

    def _load_model(self):
        try:
            import lightgbm as lgb
        except ImportError as error:
            raise RuntimeError("lightgbm is not installed") from error

        if not self.model_path.exists():
            raise FileNotFoundError(f"LightGBM model not found at {self.model_path}")

        return lgb.Booster(model_file=str(self.model_path))

    def _predict_scores(self, features):
        return self.model.predict(features)


class CatBoostRankerStrategy(BaseRankerStrategy):
    strategy_name = "catboost"
    model_path = resolve_model_path("ORDERED_CATBOOST_MODEL_PATH", MODELS_DIR / "ordered_catboost.cbm")

    def _load_model(self):
        try:
            from catboost import CatBoostRanker
        except ImportError as error:
            raise RuntimeError("catboost is not installed") from error

        if not self.model_path.exists():
            raise FileNotFoundError(f"CatBoost model not found at {self.model_path}")

        model = CatBoostRanker()
        model.load_model(str(self.model_path))
        return model

    def _predict_scores(self, features):
        return self.model.predict(features)


@lru_cache(maxsize=8)
def get_ranker(strategy="xgboost"):
    strategy_key = strategy.lower().strip()
    if strategy_key == "xgboost":
        return XGBoostRankerStrategy()
    if strategy_key == "lightgbm":
        return LightGBMRankerStrategy()
    if strategy_key == "catboost":
        return CatBoostRankerStrategy()
    raise ValueError(f"Unsupported ranker strategy: {strategy}")


def score_businesses_with_strategy(history, candidate_businesses, strategy="xgboost"):
    ranker = get_ranker(strategy)
    return ranker.score_businesses(history, candidate_businesses)


def recommend_businesses_with_strategy(history, sample_size, strategy="xgboost", top_k=3):
    ranker = get_ranker(strategy)
    return ranker.recommend_businesses(history, sample_size, top_k=top_k)


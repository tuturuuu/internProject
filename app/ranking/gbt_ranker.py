from app.ranking.reranker import (
    load_business_by_id,
    recommend_businesses_with_strategy,
    score_businesses_with_strategy,
)


def score_businesses_with_xgb(history, candidate_businesses):
    return score_businesses_with_strategy(history, candidate_businesses, strategy="xgboost")


def recommend_businesses(history, sample_size, top_k=3):
    return recommend_businesses_with_strategy(history, sample_size, strategy="xgboost", top_k=top_k)


def score_businesses_with_lightgbm(history, candidate_businesses):
    return score_businesses_with_strategy(history, candidate_businesses, strategy="lightgbm")


def recommend_businesses_with_lightgbm(history, sample_size, top_k=3):
    return recommend_businesses_with_strategy(history, sample_size, strategy="lightgbm", top_k=top_k)


def score_businesses_with_catboost(history, candidate_businesses):
    return score_businesses_with_strategy(history, candidate_businesses, strategy="catboost")


def recommend_businesses_with_catboost(history, sample_size, top_k=3):
    return recommend_businesses_with_strategy(history, sample_size, strategy="catboost", top_k=top_k)

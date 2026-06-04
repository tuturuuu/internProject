import argparse
import json
from pathlib import Path

from ranker_training_common import (
    build_dataset,
    group_rows_by_user,
    mean_group_ndcg_at_k,
    predict_rows,
    split_by_user,
)


ROOT_DIR = Path(__file__).resolve().parents[1]
MODELS_DIR = ROOT_DIR / "models"
DEFAULT_MODEL_PATH = MODELS_DIR / "ordered_catboost.cbm"
DEFAULT_METADATA_PATH = MODELS_DIR / "ordered_catboost_metadata.json"
DEFAULT_PREDICTIONS_PATH = MODELS_DIR / "ordered_catboost_predictions.json"


def extract_best_score(model, fallback_score):
    try:
        best_score = model.get_best_score()
    except Exception:
        best_score = getattr(model, "best_score_", None)

    if isinstance(best_score, dict):
        validation_scores = best_score.get("validation", {})
        for key in ("NDCG:top=10", "NDCG:top=5", "NDCG:top=3", "NDCG"):
            value = validation_scores.get(key)
            if value is not None:
                return float(value)

    if best_score is not None:
        try:
            return float(best_score)
        except (TypeError, ValueError):
            pass

    return float(fallback_score)


def build_group_ids(group_sizes):
    group_ids = []
    for index, group_size in enumerate(group_sizes):
        group_ids.extend([index] * group_size)
    return group_ids


def train_model(train_rows, validation_rows, feature_names, args):
    try:
        from catboost import CatBoostRanker, Pool
    except ImportError as error:
        raise SystemExit(
            "catboost is not installed. Install it first, then rerun: `pip install catboost`"
        ) from error

    train_rows, train_group_sizes = group_rows_by_user(train_rows)
    validation_rows, validation_group_sizes = group_rows_by_user(validation_rows)

    train_features = [row["features"] for row in train_rows]
    train_labels = [row["label"] for row in train_rows]
    validation_features = [row["features"] for row in validation_rows]
    validation_labels = [row["label"] for row in validation_rows]

    train_pool = Pool(
        train_features,
        label=train_labels,
        group_id=build_group_ids(train_group_sizes),
        feature_names=feature_names,
    )
    validation_pool = Pool(
        validation_features,
        label=validation_labels,
        group_id=build_group_ids(validation_group_sizes),
        feature_names=feature_names,
    )

    model = CatBoostRanker(
        loss_function="YetiRankPairwise",
        eval_metric="NDCG:top=10",
        custom_metric=["NDCG:top=3", "NDCG:top=5"],
        iterations=args.iterations,
        depth=args.depth,
        learning_rate=args.learning_rate,
        l2_leaf_reg=args.l2_leaf_reg,
        subsample=args.subsample,
        random_seed=args.seed,
        od_type="Iter",
        od_wait=args.early_stopping_rounds,
        verbose=args.verbose_eval,
        allow_writing_files=False,
    )

    model.fit(
        train_pool,
        eval_set=validation_pool,
        use_best_model=True,
        verbose=args.verbose_eval,
    )

    validation_scores = model.predict(validation_pool)
    metrics = {
        "ndcg@3": mean_group_ndcg_at_k(validation_labels, validation_scores, validation_group_sizes, k=3),
        "ndcg@5": mean_group_ndcg_at_k(validation_labels, validation_scores, validation_group_sizes, k=5),
        "ndcg@10": mean_group_ndcg_at_k(validation_labels, validation_scores, validation_group_sizes, k=10),
        "best_iteration": int(getattr(model, "best_iteration_", -1)),
        "best_score": extract_best_score(
            model,
            fallback_score=mean_group_ndcg_at_k(validation_labels, validation_scores, validation_group_sizes, k=10),
        ),
    }

    return model, metrics, train_pool


def build_feature_importance(model, train_pool, feature_names):
    try:
        importance = model.get_feature_importance(train_pool, type="PredictionValuesChange")
    except Exception:
        try:
            importance = model.get_feature_importance(train_pool)
        except Exception:
            importance = [0.0 for _ in feature_names]

    feature_importance = [
        {"feature": name, "gain": float(gain)}
        for name, gain in zip(feature_names, importance)
    ]
    feature_importance.sort(key=lambda item: item["gain"], reverse=True)
    return feature_importance


def main():
    parser = argparse.ArgumentParser(description="Train a CatBoost ranker for ordered label prediction.")
    parser.add_argument("--model-path", default=str(DEFAULT_MODEL_PATH))
    parser.add_argument("--metadata-path", default=str(DEFAULT_METADATA_PATH))
    parser.add_argument("--predictions-path", default=str(DEFAULT_PREDICTIONS_PATH))
    parser.add_argument("--validation-fraction", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--iterations", type=int, default=500)
    parser.add_argument("--early-stopping-rounds", type=int, default=30)
    parser.add_argument("--depth", type=int, default=6)
    parser.add_argument("--learning-rate", type=float, default=0.05)
    parser.add_argument("--subsample", type=float, default=0.85)
    parser.add_argument("--l2-leaf-reg", type=float, default=10.0)
    parser.add_argument("--verbose-eval", type=int, default=25)
    args = parser.parse_args()

    rows, feature_names = build_dataset()
    train_rows, validation_rows, validation_users = split_by_user(
        rows,
        seed=args.seed,
        validation_fraction=args.validation_fraction,
    )

    model, metrics, train_pool = train_model(train_rows, validation_rows, feature_names, args)
    predictions = predict_rows(model, rows, feature_names)

    model_path = Path(args.model_path)
    metadata_path = Path(args.metadata_path)
    predictions_path = Path(args.predictions_path)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    predictions_path.parent.mkdir(parents=True, exist_ok=True)

    model.save_model(str(model_path))
    metadata = {
        "model_path": str(model_path),
        "metadata_path": str(metadata_path),
        "feature_names": feature_names,
        "validation_users": sorted(validation_users),
        "train_rows": len(train_rows),
        "validation_rows": len(validation_rows),
        "metrics": metrics,
        "feature_importance": build_feature_importance(model, train_pool, feature_names),
    }
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    predictions_path.write_text(json.dumps(predictions, indent=2), encoding="utf-8")

    print(f"Saved model to {model_path}")
    print(f"Saved metadata to {metadata_path}")
    print(f"Saved predictions to {predictions_path}")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()

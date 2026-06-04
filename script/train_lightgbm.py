import argparse
import json
from pathlib import Path

import numpy as np

from ranker_training_common import (
    build_dataset,
    group_rows_by_user,
    mean_group_ndcg_at_k,
    predict_rows,
    split_by_user,
)


ROOT_DIR = Path(__file__).resolve().parents[1]
MODELS_DIR = ROOT_DIR / "models"
DEFAULT_MODEL_PATH = MODELS_DIR / "ordered_lightgbm.txt"
DEFAULT_METADATA_PATH = MODELS_DIR / "ordered_lightgbm_metadata.json"
DEFAULT_PREDICTIONS_PATH = MODELS_DIR / "ordered_lightgbm_predictions.json"


def extract_best_score(booster, fallback_score):
    best_score = getattr(booster, "best_score", None)
    if isinstance(best_score, dict):
        validation_scores = best_score.get("validation", {})
        for key in ("ndcg@10", "ndcg@3", "ndcg"):
            value = validation_scores.get(key)
            if value is not None:
                return float(value)
    if best_score is not None:
        try:
            return float(best_score)
        except (TypeError, ValueError):
            pass
    return float(fallback_score)


def extract_validation_metric(booster, metric_name, fallback_score):
    best_score = getattr(booster, "best_score", None)
    if isinstance(best_score, dict):
        validation_scores = best_score.get("validation", {})
        value = validation_scores.get(metric_name)
        if value is not None:
            return float(value)
    return float(fallback_score)


def debug_validation_ranking(validation_rows, validation_scores, validation_group_sizes, user_index=0, top_k=5):
    if not validation_rows or not validation_group_sizes:
        print("No validation rows available for debug.")
        return

    user_index = max(0, min(user_index, len(validation_group_sizes) - 1))
    start_offset = sum(validation_group_sizes[:user_index])
    group_size = validation_group_sizes[user_index]
    group_rows = validation_rows[start_offset : start_offset + group_size]
    group_true = [row["label"] for row in group_rows]
    group_scores = list(validation_scores[start_offset : start_offset + group_size])

    ranked = sorted(
        zip(group_scores, group_true, group_rows),
        key=lambda item: item[0],
        reverse=True,
    )

    print(f"\n[LightGBM debug] validation user index: {user_index}")
    print(f"[LightGBM debug] y_true: {group_true}")
    print(f"[LightGBM debug] y_score: {[round(score, 6) for score in group_scores]}")
    print("[LightGBM debug] top ranked items:")
    for rank, (score, label, row) in enumerate(ranked[:top_k], start=1):
        print(
            f"  {rank}. user_id={row['user_id']} restaurant_id={row['restaurant_id']} "
            f"label={label} score={score:.6f}"
        )


def train_model(train_rows, validation_rows, feature_names, args):
    try:
        import lightgbm as lgb
    except ImportError as error:
        raise SystemExit(
            "lightgbm is not installed. Install it first, then rerun: `pip install lightgbm`"
        ) from error

    train_rows, train_group_sizes = group_rows_by_user(train_rows)
    validation_rows, validation_group_sizes = group_rows_by_user(validation_rows)

    train_features = np.asarray([row["features"] for row in train_rows], dtype=float)
    train_labels = [row["label"] for row in train_rows]
    validation_features = np.asarray([row["features"] for row in validation_rows], dtype=float)
    validation_labels = [row["label"] for row in validation_rows]

    train_dataset = lgb.Dataset(
        train_features,
        label=train_labels,
        group=train_group_sizes,
        feature_name=feature_names,
        free_raw_data=False,
    )
    validation_dataset = lgb.Dataset(
        validation_features,
        label=validation_labels,
        group=validation_group_sizes,
        feature_name=feature_names,
        reference=train_dataset,
        free_raw_data=False,
    )

    params = {
        "objective": "lambdarank",
        "metric": ["ndcg"],
        "ndcg_eval_at": [3, 10],
        "learning_rate": args.learning_rate,
        "num_leaves": args.num_leaves,
        "max_depth": args.max_depth,
        "feature_fraction": args.feature_fraction,
        "bagging_fraction": args.bagging_fraction,
        "bagging_freq": args.bagging_freq,
        "min_data_in_leaf": args.min_data_in_leaf,
        "lambda_l1": args.l1_regularization,
        "lambda_l2": args.l2_regularization,
        "seed": args.seed,
        "verbosity": -1,
    }

    callbacks = [
        lgb.early_stopping(args.early_stopping_rounds, verbose=bool(args.verbose_eval)),
    ]
    if args.verbose_eval > 0:
        callbacks.append(lgb.log_evaluation(args.verbose_eval))

    booster = lgb.train(
        params=params,
        train_set=train_dataset,
        num_boost_round=args.num_boost_round,
        valid_sets=[train_dataset, validation_dataset],
        valid_names=["train", "validation"],
        callbacks=callbacks,
    )

    best_iteration = booster.best_iteration if booster.best_iteration and booster.best_iteration > 0 else None
    validation_scores = booster.predict(validation_features, num_iteration=best_iteration)
    manual_ndcg3 = mean_group_ndcg_at_k(validation_labels, validation_scores, validation_group_sizes, k=3)
    manual_ndcg5 = mean_group_ndcg_at_k(validation_labels, validation_scores, validation_group_sizes, k=5)
    manual_ndcg10 = mean_group_ndcg_at_k(validation_labels, validation_scores, validation_group_sizes, k=10)
    metrics = {
        "ndcg@3": extract_validation_metric(booster, "ndcg@3", manual_ndcg3),
        "ndcg@5": manual_ndcg5,
        "ndcg@10": extract_validation_metric(booster, "ndcg@10", manual_ndcg10),
        "best_iteration": int(booster.best_iteration or -1),
        "best_score": extract_best_score(
            booster,
            fallback_score=manual_ndcg10,
        ),
    }

    return booster, metrics


def build_feature_importance(booster, feature_names):
    importance = booster.feature_importance(importance_type="gain")
    feature_importance = [
        {"feature": name, "gain": float(gain)}
        for name, gain in zip(feature_names, importance)
    ]
    feature_importance.sort(key=lambda item: item["gain"], reverse=True)
    return feature_importance


def main():
    parser = argparse.ArgumentParser(description="Train a LightGBM ranker for ordered label prediction.")
    parser.add_argument("--model-path", default=str(DEFAULT_MODEL_PATH))
    parser.add_argument("--metadata-path", default=str(DEFAULT_METADATA_PATH))
    parser.add_argument("--predictions-path", default=str(DEFAULT_PREDICTIONS_PATH))
    parser.add_argument("--validation-fraction", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--num-boost-round", type=int, default=300)
    parser.add_argument("--early-stopping-rounds", type=int, default=20)
    parser.add_argument("--learning-rate", type=float, default=0.01)
    parser.add_argument("--num-leaves", type=int, default=31)
    parser.add_argument("--max-depth", type=int, default=-1)
    parser.add_argument("--feature-fraction", type=float, default=0.85)
    parser.add_argument("--bagging-fraction", type=float, default=0.85)
    parser.add_argument("--bagging-freq", type=int, default=1)
    parser.add_argument("--min-data-in-leaf", type=int, default=20)
    parser.add_argument("--l2-regularization", type=float, default=10.0)
    parser.add_argument("--l1-regularization", type=float, default=1.0)
    parser.add_argument("--verbose-eval", type=int, default=25)
    parser.add_argument("--debug-validation-user-index", type=int, default=None)
    args = parser.parse_args()

    rows, feature_names = build_dataset()
    train_rows, validation_rows, validation_users = split_by_user(
        rows,
        seed=args.seed,
        validation_fraction=args.validation_fraction,
    )

    booster, metrics = train_model(train_rows, validation_rows, feature_names, args)
    predictions = predict_rows(booster, rows, feature_names)

    if args.debug_validation_user_index is not None:
        validation_rows_grouped, validation_group_sizes = group_rows_by_user(validation_rows)
        best_iteration = booster.best_iteration if booster.best_iteration and booster.best_iteration > 0 else None
        validation_features = np.asarray([row["features"] for row in validation_rows_grouped], dtype=float)
        validation_scores = booster.predict(validation_features, num_iteration=best_iteration)
        debug_validation_ranking(
            validation_rows=validation_rows_grouped,
            validation_scores=validation_scores,
            validation_group_sizes=validation_group_sizes,
            user_index=args.debug_validation_user_index,
            top_k=5,
        )

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
        "feature_names": feature_names,
        "validation_users": sorted(validation_users),
        "train_rows": len(train_rows),
        "validation_rows": len(validation_rows),
        "metrics": metrics,
        "feature_importance": build_feature_importance(booster, feature_names),
    }
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    predictions_path.write_text(json.dumps(predictions, indent=2), encoding="utf-8")

    print(f"Saved model to {model_path}")
    print(f"Saved metadata to {metadata_path}")
    print(f"Saved predictions to {predictions_path}")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()

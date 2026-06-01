import argparse
import json
import math
import random
import time
from pathlib import Path
import sys

# Ensure package imports work when running this script directly
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.ranking.gbt_ranker import load_business_by_id, score_businesses_with_xgb
from app.ranking.llm_ranker import score_businesses_with_llm


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
REPORTS_DIR = ROOT_DIR / "reports"
OUTPUT_PATH = REPORTS_DIR / "ranker_evaluation.md"


def load_users():
    with open(DATA_DIR / "user_history.json", "r", encoding="utf-8") as file_handle:
        return json.load(file_handle)


def load_labels():
    with open(DATA_DIR / "user_labels.json", "r", encoding="utf-8") as file_handle:
        labels = json.load(file_handle)
    return {
        (label["user_id"], label["restaurant_id"]): int(label["ordered"])
        for label in labels
    }


def sample_unseen_businesses(business_by_id, history_ids, sample_size, seed):
    unseen_businesses = [
        business
        for business_id, business in business_by_id.items()
        if business_id not in history_ids
    ]
    pool_size = min(sample_size, len(unseen_businesses))
    rng = random.Random(seed)
    return rng.sample(unseen_businesses, pool_size)


def discounted_cumulative_gain(relevances, k):
    gain = 0.0
    for index, relevance in enumerate(relevances[:k]):
        gain += (2**relevance - 1) / math.log2(index + 2)
    return gain


def ndcg_at_k(y_true, y_score, k):
    ranked_pairs = sorted(zip(y_score, y_true), reverse=True)
    ranked_relevances = [label for _, label in ranked_pairs]
    ideal_relevances = sorted(y_true, reverse=True)

    actual_dcg = discounted_cumulative_gain(ranked_relevances, k)
    ideal_dcg = discounted_cumulative_gain(ideal_relevances, k)
    if ideal_dcg == 0:
        return 0.0
    return actual_dcg / ideal_dcg


def evaluate_ranker(users, business_by_id, labels_by_pair, scorer, sample_size, seed):
    ndcg3_scores = []
    ndcg5_scores = []
    ndcg10_scores = []
    latency_scores = []
    openai_latency_scores = []
    per_user_rows = []

    for index, user_row in enumerate(users):
        history_ids = set(user_row["history"])
        candidates = sample_unseen_businesses(
            business_by_id=business_by_id,
            history_ids=history_ids,
            sample_size=sample_size,
            seed=seed + index,
        )

        start_time = time.perf_counter()
        scored_result = scorer(user_row["history"], candidates)
        latency_seconds = time.perf_counter() - start_time

        if isinstance(scored_result, dict):
            scored_candidates = scored_result["recommendations"]
            openai_latency_seconds = scored_result.get("openai_latency_seconds")
        else:
            scored_candidates = scored_result
            openai_latency_seconds = None

        score_by_restaurant_id = {
            item["restaurant_id"]: float(item["score"])
            for item in scored_candidates
        }

        y_true = [
            labels_by_pair[(user_row["user_id"], candidate["id"])]
            for candidate in candidates
        ]
        y_score = [
            score_by_restaurant_id[candidate["id"]]
            for candidate in candidates
        ]

        ndcg3 = ndcg_at_k(y_true, y_score, k=3)
        ndcg5 = ndcg_at_k(y_true, y_score, k=5)
        ndcg10 = ndcg_at_k(y_true, y_score, k=min(10, len(y_true)))

        ndcg3_scores.append(ndcg3)
        ndcg5_scores.append(ndcg5)
        ndcg10_scores.append(ndcg10)
        latency_scores.append(latency_seconds)
        if openai_latency_seconds is not None:
            openai_latency_scores.append(openai_latency_seconds)
        per_user_rows.append(
            {
                "user_id": user_row["user_id"],
                "ndcg@3": ndcg3,
                "ndcg@5": ndcg5,
                "ndcg@10": ndcg10,
                "sampled": len(candidates),
                "latency_seconds": latency_seconds,
                "openai_latency_seconds": openai_latency_seconds,
            }
        )

    return {
        "ndcg@3": sum(ndcg3_scores) / max(1, len(ndcg3_scores)),
        "ndcg@5": sum(ndcg5_scores) / max(1, len(ndcg5_scores)),
        "ndcg@10": sum(ndcg10_scores) / max(1, len(ndcg10_scores)),
        "avg_latency_seconds": sum(latency_scores) / max(1, len(latency_scores)),
        "avg_openai_latency_seconds": (
            sum(openai_latency_scores) / max(1, len(openai_latency_scores))
            if openai_latency_scores
            else 0.0
        ),
        "users": len(users),
        "per_user_rows": per_user_rows,
    }


def render_table(rows, headers):
    widths = []
    for header in headers:
        width = len(header)
        for row in rows:
            width = max(width, len(str(row.get(header, ""))))
        widths.append(width)

    def render_row(values):
        return "| " + " | ".join(
            str(value).ljust(widths[index])
            for index, value in enumerate(values)
        ) + " |"

    separator = "|-" + "-|-".join("-" * width for width in widths) + "-|"
    lines = [render_row(headers), separator]
    for row in rows:
        lines.append(render_row([row.get(header, "") for header in headers]))
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Evaluate the XGBoost and LLM rankers with NDCG.")
    parser.add_argument("--sample-size", type=int, default=20)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    business_by_id = load_business_by_id()
    users = load_users()
    labels_by_pair = load_labels()

    xgb_result = evaluate_ranker(
        users=users,
        business_by_id=business_by_id,
        labels_by_pair=labels_by_pair,
        scorer=score_businesses_with_xgb,
        sample_size=args.sample_size,
        seed=args.seed,
    )
    llm_result = evaluate_ranker(
        users=users,
        business_by_id=business_by_id,
        labels_by_pair=labels_by_pair,
        scorer=lambda history, candidates: score_businesses_with_llm(
            history,
            candidates,
            return_metrics=True,
        ),
        sample_size=args.sample_size,
        seed=args.seed,
    )

    summary_rows = [
        {
            "ranker": "xgboost",
            "ndcg@3": f"{xgb_result['ndcg@3']:.4f}",
            "ndcg@5": f"{xgb_result['ndcg@5']:.4f}",
            "ndcg@10": f"{xgb_result['ndcg@10']:.4f}",
            "users": xgb_result["users"],
            "sample_size": args.sample_size,
            "latency_ms": f"{xgb_result['avg_latency_seconds'] * 1000:.2f}",
        },
        {
            "ranker": "llm",
            "ndcg@3": f"{llm_result['ndcg@3']:.4f}",
            "ndcg@5": f"{llm_result['ndcg@5']:.4f}",
            "ndcg@10": f"{llm_result['ndcg@10']:.4f}",
            "users": llm_result["users"],
            "sample_size": args.sample_size,
            "latency_ms": f"{llm_result['avg_latency_seconds'] * 1000:.2f}",
            "openai_latency_ms": f"{llm_result['avg_openai_latency_seconds'] * 1000:.2f}",
        },
    ]

    per_user_rows = []
    for row in xgb_result["per_user_rows"]:
        llm_row = next(item for item in llm_result["per_user_rows"] if item["user_id"] == row["user_id"])
        per_user_rows.append(
            {
                "user_id": row["user_id"],
                "xgb_ndcg@3": f"{row['ndcg@3']:.4f}",
                "llm_ndcg@3": f"{llm_row['ndcg@3']:.4f}",
                "xgb_ndcg@5": f"{row['ndcg@5']:.4f}",
                "llm_ndcg@5": f"{llm_row['ndcg@5']:.4f}",
                "xgb_ndcg@10": f"{row['ndcg@10']:.4f}",
                "llm_ndcg@10": f"{llm_row['ndcg@10']:.4f}",
                "xgb_latency_ms": f"{row['latency_seconds'] * 1000:.2f}",
                "llm_latency_ms": f"{llm_row['latency_seconds'] * 1000:.2f}",
                "llm_openai_latency_ms": (
                    f"{llm_row['openai_latency_seconds'] * 1000:.2f}"
                    if llm_row["openai_latency_seconds"] is not None
                    else "-"
                ),
            }
        )

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report = [
        "# Ranker Evaluation",
        "",
        f"Sample size per user: {args.sample_size}",
        f"Users evaluated: {len(users)}",
        "",
        "## Summary",
        render_table(
            summary_rows,
            [
                "ranker",
                "ndcg@3",
                "ndcg@5",
                "ndcg@10",
                "users",
                "sample_size",
                "latency_ms",
                "openai_latency_ms",
            ],
        ),
        "",
        "## Per User",
        render_table(
            per_user_rows,
            [
                "user_id",
                "xgb_ndcg@3",
                "llm_ndcg@3",
                "xgb_ndcg@5",
                "llm_ndcg@5",
                "xgb_ndcg@10",
                "llm_ndcg@10",
                "xgb_latency_ms",
                "llm_latency_ms",
                "llm_openai_latency_ms",
            ],
        ),
        "",
    ]
    OUTPUT_PATH.write_text("\n".join(report), encoding="utf-8")

    print(
        render_table(
            summary_rows,
            [
                "ranker",
                "ndcg@3",
                "ndcg@5",
                "ndcg@10",
                "users",
                "sample_size",
                "latency_ms",
                "openai_latency_ms",
            ],
        )
    )
    print(f"\nWrote report to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

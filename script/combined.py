import argparse
import concurrent.futures
import json
import math
import random
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.ranking.gbt_ranker import load_business_by_id, score_businesses_with_xgb
from app.ranking.llm_ranker import score_businesses_with_llm


DATA_DIR = ROOT_DIR / "data"
REPORTS_DIR = ROOT_DIR / "reports"
OUTPUT_PATH = REPORTS_DIR / "combined_ranker_evaluation.md"

ALPHA = 0.8
BETA = 0.2


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
    rng = random.Random(seed)
    return rng.sample(unseen_businesses, min(sample_size, len(unseen_businesses)))


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


def build_score_map(scored_items):
    return {
        item["restaurant_id"]: float(item["score"])
        for item in scored_items
    }


def score_user_candidates(user_row, candidates):
    history = user_row["history"]

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        xgb_future = executor.submit(score_businesses_with_xgb, history, candidates)
        llm_future = executor.submit(score_businesses_with_llm, history, candidates)
        xgb_scored = xgb_future.result()
        llm_scored = llm_future.result()

    xgb_map = build_score_map(xgb_scored)
    llm_map = build_score_map(llm_scored)

    blended_scored = []
    for business in candidates:
        xgb_score = xgb_map[business["id"]]
        llm_score = llm_map[business["id"]]
        final_score = (ALPHA * xgb_score) + (BETA * llm_score)
        blended_scored.append(
            {
                "restaurant_id": business["id"],
                "name": business["name"],
                "xgb_score": xgb_score,
                "llm_score": llm_score,
                "final_score": final_score,
            }
        )

    blended_scored.sort(key=lambda item: item["final_score"], reverse=True)
    return blended_scored


def evaluate(users, business_by_id, labels_by_pair, sample_size, seed):
    ndcg3_scores = []
    ndcg5_scores = []
    ndcg10_scores = []
    per_user_rows = []

    for index, user_row in enumerate(users):
        history_ids = set(user_row["history"])
        candidates = sample_unseen_businesses(
            business_by_id=business_by_id,
            history_ids=history_ids,
            sample_size=sample_size,
            seed=seed + index,
        )

        scored_candidates = score_user_candidates(user_row, candidates)
        score_by_restaurant_id = {
            item["restaurant_id"]: float(item["final_score"])
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

        ndcg3 = ndcg_at_k(y_true, y_score, k=min(3, len(y_true)))
        ndcg5 = ndcg_at_k(y_true, y_score, k=min(5, len(y_true)))
        ndcg10 = ndcg_at_k(y_true, y_score, k=min(10, len(y_true)))

        ndcg3_scores.append(ndcg3)
        ndcg5_scores.append(ndcg5)
        ndcg10_scores.append(ndcg10)
        per_user_rows.append(
            {
                "user_id": user_row["user_id"],
                "ndcg@3": ndcg3,
                "ndcg@5": ndcg5,
                "ndcg@10": ndcg10,
                "sampled": len(candidates),
            }
        )

    return {
        "ndcg@3": sum(ndcg3_scores) / max(1, len(ndcg3_scores)),
        "ndcg@5": sum(ndcg5_scores) / max(1, len(ndcg5_scores)),
        "ndcg@10": sum(ndcg10_scores) / max(1, len(ndcg10_scores)),
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
    parser = argparse.ArgumentParser(description="Evaluate the blended XGBoost + LLM ranker.")
    parser.add_argument("--sample-size", type=int, default=20)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    business_by_id = load_business_by_id()
    users = load_users()
    labels_by_pair = load_labels()

    result = evaluate(
        users=users,
        business_by_id=business_by_id,
        labels_by_pair=labels_by_pair,
        sample_size=args.sample_size,
        seed=args.seed,
    )

    summary_rows = [
        {
            "ranker": "combined",
            "alpha": ALPHA,
            "beta": BETA,
            "ndcg@3": f"{result['ndcg@3']:.4f}",
            "ndcg@5": f"{result['ndcg@5']:.4f}",
            "ndcg@10": f"{result['ndcg@10']:.4f}",
            "users": result["users"],
            "sample_size": args.sample_size,
        }
    ]

    per_user_rows = [
        {
            "user_id": row["user_id"],
            "ndcg@3": f"{row['ndcg@3']:.4f}",
            "ndcg@5": f"{row['ndcg@5']:.4f}",
            "ndcg@10": f"{row['ndcg@10']:.4f}",
        }
        for row in result["per_user_rows"]
    ]

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report = [
        "# Combined Ranker Evaluation",
        "",
        f"Blend: final_score = {ALPHA:.1f} * gbt_score + {BETA:.1f} * llm_context_score",
        f"Sample size per user: {args.sample_size}",
        f"Users evaluated: {len(users)}",
        "",
        "## Summary",
        render_table(summary_rows, ["ranker", "alpha", "beta", "ndcg@3", "ndcg@5", "ndcg@10", "users", "sample_size"]),
        "",
        "## Per User",
        render_table(per_user_rows, ["user_id", "ndcg@3", "ndcg@5", "ndcg@10"]),
        "",
    ]
    OUTPUT_PATH.write_text("\n".join(report), encoding="utf-8")

    print(render_table(summary_rows, ["ranker", "alpha", "beta", "ndcg@3", "ndcg@5", "ndcg@10", "users", "sample_size"]))
    print(f"\nWrote report to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

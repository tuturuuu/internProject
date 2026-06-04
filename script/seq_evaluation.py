import argparse
import json
import math
import random
import sys
import time
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.ranking.gbt_ranker import load_business_by_id, score_businesses_with_xgb
from app.ranking.llm_ranker import score_businesses_with_llm


DATA_DIR = ROOT_DIR / "data"
REPORTS_DIR = ROOT_DIR / "reports"
OUTPUT_PATH = REPORTS_DIR / "seq_ranker_evaluation.md"
LLM_SHORTLIST_SIZE = 5


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


def evaluate_sequential_ranker(users, business_by_id, labels_by_pair, sample_size, seed):
    ndcg3_scores = []
    ndcg5_scores = []
    ndcg10_scores = []
    xgb_latency_scores = []
    llm_latency_scores = []
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

        xgb_start_time = time.perf_counter()
        xgb_scored = score_businesses_with_xgb(user_row["history"], candidates)
        xgb_latency_seconds = time.perf_counter() - xgb_start_time

        llm_candidates = xgb_scored[:LLM_SHORTLIST_SIZE]
        llm_start_time = time.perf_counter()
        llm_result = score_businesses_with_llm(
            user_row["history"],
            llm_candidates,
            gbt_context=llm_candidates,
            return_metrics=True,
        )
        llm_latency_seconds = time.perf_counter() - llm_start_time

        scored_candidates = llm_result["recommendations"]
        openai_latency_seconds = llm_result.get("openai_latency_seconds")

        score_by_restaurant_id = {
            item["restaurant_id"]: float(item["score"])
            for item in xgb_scored
        }
        score_by_restaurant_id.update(
            {
                item["restaurant_id"]: float(item["score"])
                for item in scored_candidates
            }
        )

        y_true = [
            labels_by_pair[(user_row["user_id"], candidate["id"])]
            for candidate in candidates
        ]
        y_score = [
            score_by_restaurant_id.get(candidate["id"], 0.0)
            for candidate in candidates
        ]

        ndcg3 = ndcg_at_k(y_true, y_score, k=min(3, len(y_true)))
        ndcg5 = ndcg_at_k(y_true, y_score, k=min(5, len(y_true)))
        ndcg10 = ndcg_at_k(y_true, y_score, k=min(10, len(y_true)))

        ndcg3_scores.append(ndcg3)
        ndcg5_scores.append(ndcg5)
        ndcg10_scores.append(ndcg10)
        xgb_latency_scores.append(xgb_latency_seconds)
        llm_latency_scores.append(llm_latency_seconds)
        if openai_latency_seconds is not None:
            openai_latency_scores.append(openai_latency_seconds)

        per_user_rows.append(
            {
                "user_id": user_row["user_id"],
                "ndcg@3": ndcg3,
                "ndcg@5": ndcg5,
                "ndcg@10": ndcg10,
                "sampled": len(candidates),
                "llm_shortlist": len(llm_candidates),
                "xgb_latency_seconds": xgb_latency_seconds,
                "llm_latency_seconds": llm_latency_seconds,
                "openai_latency_seconds": openai_latency_seconds,
            }
        )

    return {
        "ndcg@3": sum(ndcg3_scores) / max(1, len(ndcg3_scores)),
        "ndcg@5": sum(ndcg5_scores) / max(1, len(ndcg5_scores)),
        "ndcg@10": sum(ndcg10_scores) / max(1, len(ndcg10_scores)),
        "avg_xgb_latency_seconds": sum(xgb_latency_scores) / max(1, len(xgb_latency_scores)),
        "avg_llm_latency_seconds": sum(llm_latency_scores) / max(1, len(llm_latency_scores)),
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
    parser = argparse.ArgumentParser(description="Evaluate the sequential GBT -> LLM ranker with NDCG.")
    parser.add_argument("--sample-size", type=int, default=20)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    business_by_id = load_business_by_id()
    users = load_users()
    labels_by_pair = load_labels()

    result = evaluate_sequential_ranker(
        users=users,
        business_by_id=business_by_id,
        labels_by_pair=labels_by_pair,
        sample_size=args.sample_size,
        seed=args.seed,
    )

    summary_rows = [
        {
            "ranker": "gbt -> llm",
            "ndcg@3": f"{result['ndcg@3']:.4f}",
            "ndcg@5": f"{result['ndcg@5']:.4f}",
            "ndcg@10": f"{result['ndcg@10']:.4f}",
            "users": result["users"],
            "sample_size": args.sample_size,
            "llm_shortlist": LLM_SHORTLIST_SIZE,
            "xgb_latency_ms": f"{result['avg_xgb_latency_seconds'] * 1000:.2f}",
            "llm_latency_ms": f"{result['avg_llm_latency_seconds'] * 1000:.2f}",
            "openai_latency_ms": f"{result['avg_openai_latency_seconds'] * 1000:.2f}",
        }
    ]

    per_user_rows = [
        {
            "user_id": row["user_id"],
            "ndcg@3": f"{row['ndcg@3']:.4f}",
            "ndcg@5": f"{row['ndcg@5']:.4f}",
            "ndcg@10": f"{row['ndcg@10']:.4f}",
            "llm_shortlist": row["llm_shortlist"],
            "xgb_latency_ms": f"{row['xgb_latency_seconds'] * 1000:.2f}",
            "llm_latency_ms": f"{row['llm_latency_seconds'] * 1000:.2f}",
            "openai_latency_ms": (
                f"{row['openai_latency_seconds'] * 1000:.2f}"
                if row["openai_latency_seconds"] is not None
                else "-"
            ),
        }
        for row in result["per_user_rows"]
    ]

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report = [
        "# Sequential Ranker Evaluation",
        "",
        "Pipeline: GBT ranker first, then LLM scorer with GBT context",
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
                "llm_shortlist",
                "xgb_latency_ms",
                "llm_latency_ms",
                "openai_latency_ms",
            ],
        ),
        "",
        "## Per User",
        render_table(
            per_user_rows,
            [
                "user_id",
                "ndcg@3",
                "ndcg@5",
                "ndcg@10",
                "llm_shortlist",
                "xgb_latency_ms",
                "llm_latency_ms",
                "openai_latency_ms",
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
                "xgb_latency_ms",
                "llm_latency_ms",
                "openai_latency_ms",
            ],
        )
    )
    print(f"\nWrote report to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

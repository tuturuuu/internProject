import argparse
import json
import math
import random
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.ranking.gbt_ranker import (
    score_businesses_with_catboost,
    score_businesses_with_lightgbm,
    score_businesses_with_xgb,
)
from app.ranking.llm_ranker import score_businesses_with_llm
from app.ranking.reranker import load_business_by_id


DATA_DIR = ROOT_DIR / "data"
MODELS_DIR = ROOT_DIR / "models"
REPORTS_DIR = ROOT_DIR / "reports"

DEFAULT_USER_ID = "u3"
DEFAULT_SAMPLE_SIZE = 20
DEFAULT_SEED = 42
DEFAULT_ALPHA = 0.8
DEFAULT_BETA = 0.2
DEFAULT_LLM_SHORTLIST_SIZE = 5


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


def load_metadata(model_name):
    metadata_path = MODELS_DIR / f"ordered_{model_name}_metadata.json"
    if not metadata_path.exists():
        return {}
    return json.loads(metadata_path.read_text(encoding="utf-8"))


def sample_unseen_businesses(business_by_id, history_ids, sample_size, seed):
    unseen_businesses = [
        business
        for business_id, business in business_by_id.items()
        if business_id not in history_ids
    ]
    rng = random.Random(seed)
    return rng.sample(unseen_businesses, min(sample_size, len(unseen_businesses)))


def format_item(business_by_id, item):
    business = business_by_id[item["restaurant_id"]]
    return f"{business['name']} (`{float(item['score']):.4f}`)"


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


def build_score_map(scored_items):
    return {item["restaurant_id"]: float(item["score"]) for item in scored_items}


def score_combined(xgb_scored, llm_scored, alpha, beta):
    xgb_map = build_score_map(xgb_scored)
    llm_map = build_score_map(llm_scored)
    combined = []
    for item in xgb_scored:
        restaurant_id = item["restaurant_id"]
        combined_score = (alpha * xgb_map[restaurant_id]) + (beta * llm_map.get(restaurant_id, 0.0))
        combined.append(
            {
                "restaurant_id": restaurant_id,
                "score": combined_score,
            }
        )
    combined.sort(key=lambda item: item["score"], reverse=True)
    return combined


def score_sequential(xgb_scored, llm_scored, shortlist_size):
    final_map = build_score_map(xgb_scored)
    for item in llm_scored[:shortlist_size]:
        final_map[item["restaurant_id"]] = float(item["score"])
    sequenced = [
        {
            "restaurant_id": restaurant_id,
            "score": score,
        }
        for restaurant_id, score in final_map.items()
    ]
    sequenced.sort(key=lambda item: item["score"], reverse=True)
    return sequenced


def get_top10_lines(scored_items, business_by_id):
    return [format_item(business_by_id, item) for item in scored_items[:10]]


def summarize_reasons(model_name, top_features):
    if not top_features:
        return f"- `{model_name}` không có feature importance metadata để giải thích chi tiết."
    feature_list = ", ".join(f"`{item['feature']}`" for item in top_features[:5])
    return f"- `{model_name}` đang nhấn mạnh các tín hiệu như {feature_list}."


def main():
    parser = argparse.ArgumentParser(description="Generate a per-user recommendation case study report.")
    parser.add_argument("--user-id", default=DEFAULT_USER_ID)
    parser.add_argument("--sample-size", type=int, default=DEFAULT_SAMPLE_SIZE)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--alpha", type=float, default=DEFAULT_ALPHA)
    parser.add_argument("--beta", type=float, default=DEFAULT_BETA)
    parser.add_argument("--llm-shortlist", type=int, default=DEFAULT_LLM_SHORTLIST_SIZE)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    business_by_id = load_business_by_id()
    users = {user["user_id"]: user for user in load_users()}
    labels_by_pair = load_labels()
    user_row = users.get(args.user_id)
    if user_row is None:
        raise SystemExit(f"User {args.user_id} not found in data/user_history.json")

    user_index = sorted(users).index(args.user_id)
    candidates = sample_unseen_businesses(
        business_by_id=business_by_id,
        history_ids=set(user_row["history"]),
        sample_size=args.sample_size,
        seed=args.seed + user_index,
    )

    xgb_scored = score_businesses_with_xgb(user_row["history"], candidates)
    lightgbm_scored = score_businesses_with_lightgbm(user_row["history"], candidates)
    catboost_scored = score_businesses_with_catboost(user_row["history"], candidates)
    llm_scored = score_businesses_with_llm(user_row["history"], candidates)
    combined_scored = score_combined(xgb_scored, llm_scored, alpha=args.alpha, beta=args.beta)
    seq_scored = score_sequential(xgb_scored, llm_scored, shortlist_size=args.llm_shortlist)

    output_path = Path(args.output) if args.output else REPORTS_DIR / f"user_case_study_{args.user_id}.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    xgb_meta = load_metadata("xgboost")
    lgbm_meta = load_metadata("lightgbm")
    cat_meta = load_metadata("catboost")

    report = [
        f"# User Case Study: `{args.user_id}`",
        "",
        f"Mình dùng cùng một pool `{len(candidates)}` business unseen cho user `{args.user_id}` để so sánh các kiến trúc khác nhau.",
        "",
        "## User History",
    ]

    for restaurant_id in user_row["history"]:
        business = business_by_id[restaurant_id]
        report.append(
            f"- {business['name']} — {business['cuisine']} — {business['price_range']} — rating `{business['rating']}`"
        )

    report += [
        "",
        "## Top 10 Recommendations",
        "",
    ]

    table_rows = []
    for rank in range(10):
        row = {
            "rank": rank + 1,
            "XGBoost": get_top10_lines(xgb_scored, business_by_id)[rank],
            "LightGBM": get_top10_lines(lightgbm_scored, business_by_id)[rank],
            "CatBoost": get_top10_lines(catboost_scored, business_by_id)[rank],
            "LLM": get_top10_lines(llm_scored, business_by_id)[rank],
            "Combined": get_top10_lines(combined_scored, business_by_id)[rank],
            "GBT -> LLM": get_top10_lines(seq_scored, business_by_id)[rank],
        }
        table_rows.append(row)

    report.append(
        render_table(
            table_rows,
            ["rank", "XGBoost", "LightGBM", "CatBoost", "LLM", "Combined", "GBT -> LLM"],
        )
    )

    report += [
        "",
        "## Why the ranking changes",
        "",
        f"- User `{args.user_id}` có history nghiêng mạnh về cuisine/tags cụ thể, nhưng candidate pool lại chứa nhiều business khác loại, nên các model phải dựa vào tín hiệu phụ để phân biệt.",
        "- `XGBoost` thường giữ một thứ hạng khá cân bằng nhờ các tín hiệu cuisine match, tag presence và rating.",
        "- `LightGBM` có xu hướng nhạy với rating gap và một vài tag phổ biến, nên có thể đẩy một business khác lên trên dù cuisine không khớp nhất.",
        "- `CatBoost` thường xáo trộn nhiều hơn ở top đầu khi nó gán trọng số mạnh vào các tag kiểu lifestyle / general-purpose.",
        "- `LLM` có thể ưu tiên candidate có mô tả/tags “hợp gu” hơn, nên thứ tự đôi khi khác đáng kể so với tree models.",
        "- `Combined` và `GBT -> LLM` dùng LLM để chỉnh lại top candidates, nên thường thay đổi rõ nhất ở nhóm đầu của ranking.",
        "",
        "## Model Notes",
        "",
        summarize_reasons("XGBoost", xgb_meta.get("feature_importance", [])),
        summarize_reasons("LightGBM", lgbm_meta.get("feature_importance", [])),
        summarize_reasons("CatBoost", cat_meta.get("feature_importance", [])),
        "- `LLM` không có feature importance dạng tree model; nó đang dựa trên prompt + user profile + candidate cards + (nếu có) context từ GBT.",
        "",
        "## Sources",
        "",
        f"- `data/user_history.json`",
        f"- `data/business.json`",
        f"- `data/user_labels.json`",
        f"- `models/ordered_xgboost_metadata.json`",
        f"- `models/ordered_lightgbm_metadata.json`",
        f"- `models/ordered_catboost_metadata.json`",
        "",
    ]

    output_path.write_text("\n".join(report), encoding="utf-8")
    print(f"Wrote report to {output_path}")


if __name__ == "__main__":
    main()

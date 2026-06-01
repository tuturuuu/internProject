import json
from pathlib import Path

from user_labeling_utils import DATA_DIR, load_business_by_id, load_users, rank_candidates


OUTPUT_PATH = DATA_DIR / "user_labels.json"


def main():
    business_by_id = load_business_by_id()
    users = load_users()
    labels = []

    for user_row in users:
        ranking = rank_candidates(user_row, business_by_id)
        positive_ids = ranking["positive_ids"]
        history_ids = set(user_row["history"])

        for restaurant_id in business_by_id:
            if restaurant_id in history_ids:
                continue
            labels.append(
                {
                    "user_id": user_row["user_id"],
                    "restaurant_id": restaurant_id,
                    "ordered": 1 if restaurant_id in positive_ids else 0,
                }
            )

    with open(OUTPUT_PATH, "w", encoding="utf-8") as file_handle:
        json.dump(labels, file_handle, indent=2, ensure_ascii=False)
        file_handle.write("\n")

    print(f"Wrote {len(labels)} labels to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

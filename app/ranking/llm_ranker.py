import json
import os
import random
from functools import lru_cache
from pathlib import Path
import time

from fastapi import HTTPException
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4.1")


@lru_cache(maxsize=1)
def load_business_by_id():
    with open(DATA_DIR / "business.json", "r", encoding="utf-8") as file_handle:
        businesses = json.load(file_handle)
    return {business["id"]: business for business in businesses}


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


def summarize_user(history_ids):
    business_by_id = load_business_by_id()
    valid_restaurants = [
        business_by_id[restaurant_id]
        for restaurant_id in history_ids
        if restaurant_id in business_by_id
    ]

    if not valid_restaurants:
        raise HTTPException(status_code=400, detail="history must contain at least one valid restaurant id")

    cuisine_counts = {}
    price_counts = {}
    tag_counts = {}
    ratings = []

    for restaurant in valid_restaurants:
        cuisine_counts[restaurant["cuisine"]] = cuisine_counts.get(restaurant["cuisine"], 0) + 1
        price_counts[restaurant["price_range"]] = price_counts.get(restaurant["price_range"], 0) + 1
        ratings.append(float(restaurant["rating"]))
        for tag in restaurant["tags"]:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

    return {
        "history_length": len(valid_restaurants),
        "average_rating": round(sum(ratings) / len(ratings), 2),
        "dominant_cuisine": max(cuisine_counts, key=cuisine_counts.get),
        "dominant_price": max(price_counts, key=price_counts.get),
        "top_tags": [
            tag
            for tag, _ in sorted(tag_counts.items(), key=lambda item: (-item[1], item[0]))[:8]
        ],
    }


def build_history_payload(history_ids):
    business_by_id = load_business_by_id()
    valid_restaurants = [
        business_by_id[restaurant_id]
        for restaurant_id in history_ids
        if restaurant_id in business_by_id
    ]

    return [restaurant["name"] for restaurant in valid_restaurants]


def build_candidates_payload(candidate_businesses):
    return [
        {
            "restaurant_id": business["id"],
            "name": business["name"],
            "cuisine": business["cuisine"],
            "rating": float(business["rating"]),
            "price_range": business["price_range"],
            "tags": business["tags"][:10],
        }
        for business in candidate_businesses
    ]


def call_openai_json(prompt, schema_name, schema):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not set")

    client = OpenAI(api_key=api_key)
    start_time = time.perf_counter()

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=prompt,
            temperature=0,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "schema": schema,
                    "strict": True,
                },
            },
        )
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"OpenAI API error: {error}") from error

    api_latency_seconds = time.perf_counter() - start_time

    try:
        content = response.choices[0].message.content
        return json.loads(content), api_latency_seconds
    except (AttributeError, IndexError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=500, detail="OpenAI returned an invalid JSON payload") from error


def score_businesses_with_llm(history, candidate_businesses, return_metrics=False):
    user_summary = summarize_user(history)
    user_history_names = build_history_payload(history)
    candidates_payload = build_candidates_payload(candidate_businesses)

    prompt = [
        {
            "role": "system",
            "content": (
                "You are a recommendation scorer. "
                "Given a user's history and a set of candidate businesses, "
                "predict whether the user would click/order each candidate. "
                "Return only valid JSON matching the schema."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "user_history": user_history_names,
                    "user_preferences": user_summary,
                    "candidates": candidates_payload,
                    "instructions": [
                        "Score each candidate from 0.0 to 1.0 as click/order likelihood.",
                        "Use higher scores for stronger matches to the user's taste.",
                        "Set label to 1 when score is at least 0.5, otherwise 0.",
                        "Return a recommendation entry for every candidate provided.",
                    ],
                },
                ensure_ascii=False,
            ),
        },
    ]

    schema = {
        "type": "object",
        "properties": {
            "candidates_sampled": {"type": "integer"},
            "recommendations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "restaurant_id": {"type": "string"},
                        "name": {"type": "string"},
                        "score": {
                            "type": "number",
                            "minimum": 0.0,
                            "maximum": 1.0,
                        },
                        "label": {"type": "integer", "enum": [0, 1]},
                    },
                    "required": ["restaurant_id", "name", "score", "label"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["candidates_sampled", "recommendations"],
        "additionalProperties": False,
    }

    result, api_latency_seconds = call_openai_json(
        prompt=prompt,
        schema_name="llm_recommendation_scores",
        schema=schema,
    )

    recommendations = result.get("recommendations", [])
    recommendations.sort(key=lambda item: item["score"], reverse=True)

    if return_metrics:
        return {
            "recommendations": recommendations,
            "openai_latency_seconds": api_latency_seconds,
        }

    return recommendations


def recommend_businesses_with_llm(history, sample_size, top_k=3):
    candidate_businesses = sample_businesses(set(history), sample_size)
    recommendations = score_businesses_with_llm(history, candidate_businesses)

    return {
        "candidates_sampled": len(candidate_businesses),
        "recommendations": recommendations[:top_k],
        "model": OPENAI_MODEL,
    }

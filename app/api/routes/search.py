from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.ranking.reranker import recommend_businesses_with_strategy
from app.ranking.llm_ranker import recommend_businesses_with_llm


router = APIRouter(prefix="/search", tags=["search"])

RankerName = Literal["xgboost", "lightgbm", "catboost", "llm"]


class RecommendationRequest(BaseModel):
    history: list[str] = Field(..., description="Restaurant IDs from the user's history")
    sample_size: int = Field(20, ge=1, le=100, description="Number of random candidates to score")
    ranker: RankerName = Field("xgboost", description="Ranker to use: xgboost, lightgbm, catboost, or llm")


class RecommendationItem(BaseModel):
    restaurant_id: str
    name: str
    score: float
    label: int


class RecommendationResponse(BaseModel):
    ranker: str
    candidates_sampled: int
    recommendations: list[RecommendationItem]


@router.post("/recommendations", response_model=RecommendationResponse)
def recommend(request: RecommendationRequest):
    try:
        if request.ranker == "llm":
            result = recommend_businesses_with_llm(request.history, request.sample_size, top_k=3)
        else:
            result = recommend_businesses_with_strategy(
                request.history,
                request.sample_size,
                strategy=request.ranker,
                top_k=3,
            )
    except FileNotFoundError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    result["ranker"] = request.ranker
    return RecommendationResponse(**result)


@router.post("/llm-recommendations", response_model=RecommendationResponse)
def recommend_with_llm(request: RecommendationRequest):
    result = recommend_businesses_with_llm(request.history, request.sample_size, top_k=3)
    result["ranker"] = "llm"
    return RecommendationResponse(**result)

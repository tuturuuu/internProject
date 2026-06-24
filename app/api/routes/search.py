from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.ranking.reranker import recommend_businesses_with_strategy
from app.ranking.llm_ranker import recommend_businesses_with_llm


router = APIRouter(prefix="/search", tags=["search"])

RankerName = Literal["xgboost", "lightgbm", "catboost", "llm"]


class RecommendationRequest(BaseModel):
    user_id: Optional[str] = Field(None, description="Clerk user ID to retrieve history from Redis")
    history: Optional[list[str]] = Field(None, description="Restaurant IDs from the user's history")
    sample_size: int = Field(20, ge=1, le=100, description="Number of random candidates to score")
    ranker: RankerName = Field("xgboost", description="Ranker to use: xgboost, lightgbm, catboost, or llm")
    top_k: int = Field(3, ge=1, le=50, description="Number of businesses to return in the final recommendations")


class RecommendationItem(BaseModel):
    restaurant_id: str
    name: str
    score: float
    label: int


class RecommendationResponse(BaseModel):
    ranker: str
    candidates_sampled: int
    recommendations: list[RecommendationItem]
    top_k: int


@router.post("/recommendations", response_model=RecommendationResponse)
def recommend(request: RecommendationRequest):
    history = request.history
    if request.user_id:
        from app.services.redis_service import get_user_history
        redis_history = get_user_history(request.user_id)
        if redis_history:
            history = redis_history
            
    if not history:
        history = []
        
    try:
        if request.ranker == "llm":
            result = recommend_businesses_with_llm(history, request.sample_size, top_k=request.top_k)
        else:
            result = recommend_businesses_with_strategy(
                history,
                request.sample_size,
                strategy=request.ranker,
                top_k=request.top_k,
            )
    except FileNotFoundError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    result["ranker"] = request.ranker
    result["top_k"] = request.top_k
    return RecommendationResponse(**result)


@router.post("/llm-recommendations", response_model=RecommendationResponse)
def recommend_with_llm(request: RecommendationRequest):
    history = request.history
    if request.user_id:
        from app.services.redis_service import get_user_history
        redis_history = get_user_history(request.user_id)
        if redis_history:
            history = redis_history
            
    if not history:
        history = []
        
    result = recommend_businesses_with_llm(history, request.sample_size, top_k=request.top_k)
    result["ranker"] = "llm"
    return RecommendationResponse(**result)

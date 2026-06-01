from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.ranking.gbt_ranker import recommend_businesses
from app.ranking.llm_ranker import recommend_businesses_with_llm


router = APIRouter(prefix="/search", tags=["search"])


class RecommendationRequest(BaseModel):
    history: list[str] = Field(..., description="Restaurant IDs from the user's history")
    sample_size: int = Field(20, ge=1, le=100, description="Number of random candidates to score")


class RecommendationItem(BaseModel):
    restaurant_id: str
    name: str
    score: float
    label: int


class RecommendationResponse(BaseModel):
    candidates_sampled: int
    recommendations: list[RecommendationItem]


@router.post("/recommendations", response_model=RecommendationResponse)
def recommend(request: RecommendationRequest):
    result = recommend_businesses(request.history, request.sample_size, top_k=3)
    return RecommendationResponse(**result)


@router.post("/llm-recommendations", response_model=RecommendationResponse)
def recommend_with_llm(request: RecommendationRequest):
    result = recommend_businesses_with_llm(request.history, request.sample_size, top_k=3)
    return RecommendationResponse(**result)

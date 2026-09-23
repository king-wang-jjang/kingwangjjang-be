from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from app.auth.dependencies import get_optional_principal, require_principal
from app.auth.principal import Principal
from app.repositories.boards import BoardListFilters
from app.repositories.recommendations import RecommendationRepository
from app.routes.boards import _to_board_response
from app.services.recommendations import Identifier, InterestMutation, InterestProfile, Tag

router = APIRouter(prefix="/api/boards/recommendations", tags=["recommendations"])


class ProfileUpdates(BaseModel):
    mutations: list[InterestMutation] = Field(min_length=1, max_length=20)


class RecommendationRequest(BaseModel):
    profile: InterestProfile | None = None
    category: Tag | None = None
    tag: Tag | None = None
    sites: list[Tag] = Field(default_factory=list, max_length=8)


class PostsRequest(BaseModel):
    ids: list[Identifier] = Field(max_length=30)


def private_response(response: Response) -> None:
    response.headers["Cache-Control"] = "private, no-store"


@router.get("/profile", response_model=InterestProfile)
def get_profile(response: Response, principal: Principal = Depends(require_principal)):
    private_response(response)
    return RecommendationRepository().get_profile(principal)


@router.post("/profile", response_model=InterestProfile)
def update_profile(payload: ProfileUpdates, response: Response, principal: Principal = Depends(require_principal)):
    private_response(response)
    try:
        return RecommendationRepository().update_profile(principal, payload.mutations)
    except RuntimeError as error:
        raise HTTPException(status_code=409, detail="관심사 동기화를 다시 시도해 주세요.") from error


@router.post("")
def recommend(payload: RecommendationRequest, response: Response, principal: Principal = Depends(get_optional_principal)):
    private_response(response)
    repository = RecommendationRepository()
    profile = repository.get_profile(principal) if principal.is_authenticated else payload.profile or InterestProfile()
    filters = BoardListFilters.from_values(category=payload.category, tag=payload.tag, sites=payload.sites)
    return {"items": repository.recommend(profile, filters)}


@router.post("/posts")
def get_posts(payload: PostsRequest, response: Response):
    private_response(response)
    return [_to_board_response(board) for board in RecommendationRepository().get_posts(payload.ids)]

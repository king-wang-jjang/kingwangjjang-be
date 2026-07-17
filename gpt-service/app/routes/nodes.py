from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import require_ai_admin
from app.repositories.ai_nodes import AINodeRepository
from app.routes.dependencies import get_node_repository, get_node_router
from app.schemas.nodes import (
    AINodeCreate,
    AINodeResponse,
    AINodeUpdate,
    model_inputs_as_dicts,
    node_to_response,
)
from app.services.node_router import AINodeRouter


router = APIRouter(
    prefix="/api/ai/nodes",
    tags=["ai-nodes"],
    dependencies=[Depends(require_ai_admin)],
)


@router.get("", response_model=list[AINodeResponse])
def list_nodes(repository: AINodeRepository = Depends(get_node_repository)):
    return [node_to_response(node) for node in repository.list_nodes()]


@router.post("", response_model=AINodeResponse, status_code=status.HTTP_201_CREATED)
def create_node(
    payload: AINodeCreate,
    repository: AINodeRepository = Depends(get_node_repository),
):
    values = payload.model_dump(exclude={"models"})
    try:
        node = repository.create_node(values, model_inputs_as_dicts(payload.models))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return node_to_response(node)


@router.post("/health-check", response_model=list[AINodeResponse])
async def health_check_all(node_router: AINodeRouter = Depends(get_node_router)):
    results = await node_router.health_check_all()
    return [node_to_response(node) for node, _health in results if node is not None]


@router.get("/{node_id}", response_model=AINodeResponse)
def get_node(
    node_id: str,
    repository: AINodeRepository = Depends(get_node_repository),
):
    node = repository.get_node(node_id)
    if node is None:
        raise HTTPException(status_code=404, detail="AI node not found")
    return node_to_response(node)


@router.patch("/{node_id}", response_model=AINodeResponse)
def update_node(
    node_id: str,
    payload: AINodeUpdate,
    repository: AINodeRepository = Depends(get_node_repository),
):
    changes = payload.model_dump(exclude_unset=True)
    raw_models = changes.pop("models", None)
    models = None
    if raw_models is not None:
        models = raw_models
    try:
        node = repository.update_node(node_id, changes, models)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if node is None:
        raise HTTPException(status_code=404, detail="AI node not found")
    return node_to_response(node)


@router.delete("/{node_id}")
def delete_node(
    node_id: str,
    repository: AINodeRepository = Depends(get_node_repository),
):
    if not repository.delete_node(node_id):
        raise HTTPException(status_code=404, detail="AI node not found")
    return {"deleted": node_id}


@router.post("/{node_id}/health-check", response_model=AINodeResponse)
async def health_check_node(
    node_id: str,
    node_router: AINodeRouter = Depends(get_node_router),
):
    node, _health = await node_router.health_check(node_id)
    if node is None:
        raise HTTPException(status_code=404, detail="AI node not found")
    return node_to_response(node)

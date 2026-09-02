from fastapi import APIRouter, Depends

from app.auth import require_ai_admin
from app.repositories.ai_nodes import AINodeRepository
from app.routes.dependencies import get_node_repository, get_node_router
from app.schemas.nodes import node_to_response
from app.schemas.resources import AIResourceOverviewResponse
from app.services.node_router import AINodeRouter


router = APIRouter(
    prefix="/api/ai/resources",
    tags=["ai-resources"],
    dependencies=[Depends(require_ai_admin)],
)


@router.get("", response_model=AIResourceOverviewResponse)
async def resource_overview(
    repository: AINodeRepository = Depends(get_node_repository),
    node_router: AINodeRouter = Depends(get_node_router),
):
    snapshot = await node_router.resource_snapshot()
    runtime_by_node = {item["id"]: item for item in snapshot.pop("nodes")}
    nodes = []
    for node in repository.list_nodes():
        runtime = runtime_by_node.get(node.id)
        if runtime is None:
            continue
        runtime.pop("id", None)
        nodes.append(
            {
                **node_to_response(node).model_dump(),
                "runtime": runtime,
            }
        )
    return {**snapshot, "nodes": nodes}

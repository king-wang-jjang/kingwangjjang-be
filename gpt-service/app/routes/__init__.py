from app.routes.inference import router as inference_router
from app.routes.nodes import router as nodes_router
from app.routes.resources import router as resources_router

__all__ = ["inference_router", "nodes_router", "resources_router"]

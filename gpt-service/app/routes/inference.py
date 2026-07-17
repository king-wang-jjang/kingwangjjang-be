from fastapi import APIRouter, Depends, HTTPException

from app.auth import require_ai_service
from app.routes.dependencies import get_node_router
from app.schemas.inference import (
    AnalyzeRequest,
    AnalyzeResponse,
    ChatRequest,
    ChatResponse,
    VisionTextRequest,
    VisionTextResponse,
)
from app.services.inference import analysis_messages, parse_analysis, vision_messages
from app.services.node_router import (
    AINodeRouter,
    InvalidInferenceRequestError,
    NoAvailableNodeError,
    NodeRequestFailedError,
)


router = APIRouter(
    prefix="/api/ai",
    tags=["ai-inference"],
    dependencies=[Depends(require_ai_service)],
)


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    payload: AnalyzeRequest,
    node_router: AINodeRouter = Depends(get_node_router),
):
    try:
        result = await node_router.invoke(
            capability="analysis",
            messages=analysis_messages(payload.content),
            response_format="json",
            transform=parse_analysis,
        )
    except InvalidInferenceRequestError as exc:
        raise HTTPException(status_code=422, detail="Invalid AI inference request") from exc
    except NodeRequestFailedError as exc:
        raise HTTPException(status_code=502, detail="AI node request failed") from exc
    except NoAvailableNodeError as exc:
        raise HTTPException(status_code=503, detail="AI service is temporarily unavailable") from exc
    analysis = result.value
    return AnalyzeResponse(
        summary=analysis["summary"],
        tags=analysis["tags"],
        llm_engagement_score=analysis["llm_engagement_score"],
        llm_engagement_reason=analysis["llm_engagement_reason"],
        node_id=result.node_id,
        node_name=result.node_name,
        model=result.model,
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    node_router: AINodeRouter = Depends(get_node_router),
):
    try:
        result = await node_router.invoke(
            capability=payload.capability,
            messages=payload.messages,
            response_format=payload.response_format,
        )
    except InvalidInferenceRequestError as exc:
        raise HTTPException(status_code=422, detail="Invalid AI inference request") from exc
    except NodeRequestFailedError as exc:
        raise HTTPException(status_code=502, detail="AI node request failed") from exc
    except NoAvailableNodeError as exc:
        raise HTTPException(status_code=503, detail="AI service is temporarily unavailable") from exc
    return ChatResponse(
        content=result.value,
        node_id=result.node_id,
        node_name=result.node_name,
        model=result.model,
    )


@router.post("/vision-text", response_model=VisionTextResponse)
async def vision_text(
    payload: VisionTextRequest,
    node_router: AINodeRouter = Depends(get_node_router),
):
    try:
        result = await node_router.invoke(
            capability="vision",
            messages=vision_messages(payload.image_data_url, payload.prompt),
        )
    except InvalidInferenceRequestError as exc:
        raise HTTPException(status_code=422, detail="Invalid AI inference request") from exc
    except NodeRequestFailedError as exc:
        raise HTTPException(status_code=502, detail="AI node request failed") from exc
    except NoAvailableNodeError as exc:
        raise HTTPException(status_code=503, detail="AI service is temporarily unavailable") from exc
    return VisionTextResponse(
        text=result.value,
        node_id=result.node_id,
        node_name=result.node_name,
        model=result.model,
    )

from datetime import date, datetime
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.auth.dependencies import require_admin, require_principal
from app.auth.principal import Principal
from app.repositories.boards import BoardListFilters, BoardRepository
from app.services.analysis_jobs import BoardAnalysisJobStore
from app.services.analysis_worker import analysis_worker_concurrency, analysis_worker_enabled
from app.services.board_filters import get_board_filter_options, get_site_label
from app.services.shorts_package import (
    HISTORICAL_RANKING_MODE,
    LIVE_RANKING_MODE,
    TOP10_LIMIT,
    build_top10_shorts_package,
)
from app.services.vision_text import VisionTextError
from app.utils.llm import LLMError


router = APIRouter(prefix="/api/boards", tags=["boards"])
analysis_jobs = BoardAnalysisJobStore()
ANALYSIS_ESTIMATED_SECONDS = 60
ANALYSIS_BACKLOG_BUSY_SECONDS = 120
ANALYSIS_BACKLOG_OVERLOAD_SECONDS = 600
VISION_TEXT_UPSTREAM_ERROR = "Vision text extraction failed"
SEOUL_TIME_ZONE = ZoneInfo("Asia/Seoul")


class VisionTextRequest(BaseModel):
    prompt: str | None = None


class BoardFilterOption(BaseModel):
    value: str
    label: str


class BoardFilterOptions(BaseModel):
    sites: list[BoardFilterOption]


class IssueSiteBreakdown(BaseModel):
    site: str
    site_label: str
    post_count: int


class IssueCategoryOverview(BaseModel):
    category: str
    post_count: int
    current_posts: int
    previous_posts: int
    impact_score: float
    share: float
    momentum_percent: float
    top_sites: list[IssueSiteBreakdown]
    top_tags: list[str]


class IssueOverviewResponse(BaseModel):
    generated_at: datetime
    window_hours: int
    total_posts: int
    total_categories: int
    categories: list[IssueCategoryOverview]


class AnalysisQueueResourceResponse(BaseModel):
    generated_at: datetime
    status: Literal["healthy", "busy", "overloaded", "unavailable"]
    is_overloaded: bool
    worker_enabled: bool
    worker_concurrency: int
    total_count: int
    pending_count: int
    ready_pending_count: int
    deferred_pending_count: int
    processing_count: int
    done_count: int
    failed_count: int
    stale_processing_count: int
    oldest_pending_at: datetime | None
    oldest_pending_age_seconds: int
    recent_arrivals: int
    recent_completions: int
    estimated_clear_seconds: int | None


def _to_board_response(board: dict) -> dict:
    return {
        "_id": board["id"],
        "category": board["category"],
        "no": board["no"],
        "site": board["site"],
        "site_label": get_site_label(board["site"]),
        "title": board["title"],
        "url": board["url"],
        "contents": board.get("contents"),
        "gpt_answer": board.get("gpt_answer"),
        "tags": board.get("tags", []),
        "llm_engagement_score": board.get("llm_engagement_score"),
        "llm_engagement_reason": board.get("llm_engagement_reason"),
        "analysis_status": board.get("analysis_status"),
        "analysis_retry_count": board.get("analysis_retry_count", 0),
        "analysis_error": board.get("analysis_error"),
        "create_time": board["created_at"],
        "thumbnail": board.get("thumbnail"),
        "comment_count": board.get("comment_count", 0),
        "likeCount": board.get("like_count", 0),
        "native_comment_count": board.get("native_comment_count"),
        "native_like_count": board.get("native_like_count"),
        "native_view_count": board.get("native_view_count"),
        "source_rank": board.get("source_rank"),
        "hot_score": board.get("hot_score"),
        "daily_score": board.get("daily_score"),
        "metrics_crawled_at": board.get("metrics_crawled_at"),
        "score_updated_at": board.get("score_updated_at"),
    }


def _to_analysis_response(analysis: dict) -> dict:
    return {
        "boardId": analysis["board_id"],
        "status": analysis["status"],
        "summary": analysis.get("summary"),
        "tags": analysis.get("tags", []),
        "llmEngagementScore": analysis.get("llm_engagement_score"),
        "llmEngagementReason": analysis.get("llm_engagement_reason"),
        "retryCount": analysis.get("retry_count", 0),
        "error": analysis.get("error"),
        "requestedAt": analysis.get("requested_at"),
        "startedAt": analysis.get("started_at"),
        "updatedAt": analysis.get("updated_at"),
    }


def _to_vision_text_response(result: dict) -> dict:
    return {
        "boardId": result["board_id"],
        "imageIndex": result["image_index"],
        "mediaPath": result["media_path"],
        "text": result["text"],
    }


@router.get("/filters", response_model=BoardFilterOptions)
def board_filters(response: Response):
    response.headers["Cache-Control"] = "no-store"
    active_sites = BoardRepository().list_recently_crawled_sites()
    return get_board_filter_options(active_sites)


@router.get("/issues", response_model=IssueOverviewResponse)
def issue_overview(
    response: Response,
    hours: int = Query(default=24, ge=6, le=168),
    limit: int = Query(default=16, ge=4, le=24),
    sites: list[str] | None = Query(default=None),
):
    selected_sites = BoardListFilters.from_values(sites=sites).sites
    overview = BoardRepository().get_issue_overview(
        window_hours=hours,
        limit=limit,
        sites=selected_sites,
    )
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=120"
    return {
        **overview,
        "categories": [
            {
                **category,
                "top_sites": [
                    {
                        **site,
                        "site_label": get_site_label(site["site"]),
                    }
                    for site in category["top_sites"]
                ],
            }
            for category in overview["categories"]
        ],
    }


@router.get("/realtime")
def realtime(
    index: int = 0,
    limit: int = 30,
    sites: list[str] | None = Query(default=None),
    category: str | None = None,
    tag: str | None = None,
    q: str | None = None,
    has_thumbnail: bool | None = None,
):
    filters = BoardListFilters.from_values(
        sites=sites,
        category=category,
        tag=tag,
        query=q,
        has_thumbnail=has_thumbnail,
    )
    return [
        _to_board_response(board)
        for board in BoardRepository().list_realtime(index, limit, filters=filters)
    ]


@router.get("/daily")
def daily(
    index: int = 0,
    limit: int = 30,
    sites: list[str] | None = Query(default=None),
    category: str | None = None,
    tag: str | None = None,
    q: str | None = None,
    has_thumbnail: bool | None = None,
):
    filters = BoardListFilters.from_values(
        sites=sites,
        category=category,
        tag=tag,
        query=q,
        has_thumbnail=has_thumbnail,
    )
    return [
        _to_board_response(board)
        for board in BoardRepository().list_daily(index, limit, filters=filters)
    ]


@router.get("/daily/history/dates")
def daily_history_dates(limit: int = Query(default=30, ge=1, le=365)):
    return [
        snapshot_date.isoformat()
        for snapshot_date in BoardRepository().list_daily_history_dates(limit)
    ]


@router.get("/daily/history")
def daily_history(
    snapshot_date: date = Query(alias="date"),
    limit: int = Query(default=10, ge=1, le=100),
):
    return [
        _to_board_response(board)
        for board in BoardRepository().list_daily_history(snapshot_date, limit)
    ]


@router.get("/daily/shorts-package")
def daily_shorts_package(
    response: Response,
    snapshot_date: date | None = Query(default=None, alias="date"),
    _principal: Principal = Depends(require_admin),
):
    repository = BoardRepository()
    ranking_date = snapshot_date or datetime.now(SEOUL_TIME_ZONE).date()
    boards = (
        repository.list_daily(0, TOP10_LIMIT)
        if snapshot_date is None
        else repository.list_daily_history(snapshot_date, TOP10_LIMIT)
    )
    if not boards:
        raise HTTPException(status_code=404, detail="Top 10 ranking not found")

    response.headers["Cache-Control"] = "private, no-store"
    return build_top10_shorts_package(
        boards,
        ranking_date=ranking_date,
        ranking_mode=(
            LIVE_RANKING_MODE
            if snapshot_date is None
            else HISTORICAL_RANKING_MODE
        ),
    )


@router.get("/ai/resources", response_model=AnalysisQueueResourceResponse)
def analysis_queue_resources(
    response: Response,
    _principal: Principal = Depends(require_admin),
):
    metrics = BoardRepository().get_analysis_queue_metrics()
    worker_enabled = analysis_worker_enabled()
    worker_concurrency = analysis_worker_concurrency() if worker_enabled else 0
    pending_count = metrics["pending_count"]
    oldest_pending_age = metrics["oldest_pending_age_seconds"]

    if not worker_enabled:
        queue_status = "unavailable"
    elif (
        oldest_pending_age >= ANALYSIS_BACKLOG_OVERLOAD_SECONDS
        or pending_count >= max(worker_concurrency * 10, 1)
    ):
        queue_status = "overloaded"
    elif (
        oldest_pending_age >= ANALYSIS_BACKLOG_BUSY_SECONDS
        or pending_count >= max(worker_concurrency * 2, 1)
        or metrics["stale_processing_count"] > 0
    ):
        queue_status = "busy"
    else:
        queue_status = "healthy"

    if pending_count == 0:
        estimated_clear_seconds = 0
    elif metrics["recent_completions"] > 0:
        estimated_clear_seconds = round(
            pending_count * 3600 / metrics["recent_completions"]
        )
    else:
        estimated_clear_seconds = None

    response.headers["Cache-Control"] = "private, no-store"
    return {
        **metrics,
        "status": queue_status,
        "is_overloaded": queue_status == "overloaded",
        "worker_enabled": worker_enabled,
        "worker_concurrency": worker_concurrency,
        "estimated_clear_seconds": estimated_clear_seconds,
    }


@router.get("/{board_id}/ai")
def get_board_analysis(board_id: str):
    result = BoardRepository().get_analysis(board_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Board not found")

    return _to_analysis_response(result)


@router.get("/ai/jobs/{job_id}")
def get_analysis_job(job_id: str, _principal: Principal = Depends(require_admin)):
    job = analysis_jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Analysis job not found")

    return job.to_response()


@router.post("/{board_id}/ai")
def reanalyze_board(
    board_id: str,
    background_tasks: BackgroundTasks,
    _principal: Principal = Depends(require_admin),
):
    repository = BoardRepository()
    current_analysis = repository.get_analysis_status(board_id)
    if current_analysis is None:
        raise HTTPException(status_code=404, detail="Board not found")

    job, created = analysis_jobs.start(
        board_id=current_analysis["board_id"],
        estimated_seconds=ANALYSIS_ESTIMATED_SECONDS,
    )
    if created:
        background_tasks.add_task(
            _run_analysis_job,
            job.job_id,
            current_analysis["board_id"],
            True,
        )

    return JSONResponse(status_code=202, content=job.to_response())


def _run_analysis_job(job_id: str, board_id: str, force: bool = False) -> None:
    analysis_jobs.mark_running(job_id, estimated_seconds=max(ANALYSIS_ESTIMATED_SECONDS - 15, 1))
    try:
        result = BoardRepository().analyze_board(board_id, force=force)
    except LLMError:
        analysis_jobs.mark_failed(job_id, "AI analysis failed")
        return
    except Exception as exc:
        analysis_jobs.mark_failed(job_id, str(exc))
        return

    if result is None:
        analysis_jobs.mark_failed(job_id, "Board not found")
        return

    analysis_jobs.mark_completed(
        job_id,
        summary=result["summary"],
        tags=result["tags"],
        llm_engagement_score=result.get("llm_engagement_score"),
        llm_engagement_reason=result.get("llm_engagement_reason"),
    )


@router.post("/{board_id}/images/{image_index}/vision-text")
def extract_image_text(
    board_id: str,
    image_index: int,
    request: VisionTextRequest | None = None,
    _principal: Principal = Depends(require_principal),
):
    try:
        result = BoardRepository().extract_image_text(
            board_id,
            image_index=image_index,
            prompt=request.prompt if request else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except VisionTextError as exc:
        raise HTTPException(status_code=502, detail=VISION_TEXT_UPSTREAM_ERROR) from exc

    if result is None:
        raise HTTPException(status_code=404, detail="Board not found")

    return _to_vision_text_response(result)


@router.post("/{board_id}/likes")
def add_like(board_id: str, principal: Principal = Depends(require_principal)):
    result = BoardRepository().add_like(board_id, principal.user_id or "")
    if result is None:
        raise HTTPException(status_code=404, detail="Board not found")

    return {
        "boardId": result["board_id"],
        "site": result["site"],
        "likeCount": result["like_count"],
    }

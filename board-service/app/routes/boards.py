from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from app.auth.dependencies import require_principal
from app.auth.principal import Principal
from app.repositories.boards import BoardListFilters, BoardRepository
from app.services.analysis_jobs import BoardAnalysisJobStore
from app.utils.llm import LLMError


router = APIRouter(prefix="/api/boards", tags=["boards"])
analysis_jobs = BoardAnalysisJobStore()
ANALYSIS_ESTIMATED_SECONDS = 60


def _to_board_response(board: dict) -> dict:
    return {
        "_id": board["id"],
        "category": board["category"],
        "no": board["no"],
        "site": board["site"],
        "title": board["title"],
        "url": board["url"],
        "contents": board.get("contents"),
        "gpt_answer": board.get("gpt_answer"),
        "tags": board.get("tags", []),
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
        "retryCount": analysis.get("retry_count", 0),
        "error": analysis.get("error"),
        "requestedAt": analysis.get("requested_at"),
        "startedAt": analysis.get("started_at"),
        "updatedAt": analysis.get("updated_at"),
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


@router.get("/{board_id}/ai")
def get_board_analysis(board_id: str):
    result = BoardRepository().get_analysis(board_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Board not found")

    return _to_analysis_response(result)


@router.get("/ai/jobs/{job_id}")
def get_analysis_job(job_id: str, _principal: Principal = Depends(require_principal)):
    job = analysis_jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Analysis job not found")

    return job.to_response()


@router.post("/{board_id}/ai")
def analyze_board(
    board_id: str,
    background_tasks: BackgroundTasks,
    _principal: Principal = Depends(require_principal),
):
    repository = BoardRepository()
    current_analysis = repository.get_analysis_status(board_id)
    if current_analysis is None:
        raise HTTPException(status_code=404, detail="Board not found")

    if current_analysis["is_complete"]:
        job = analysis_jobs.completed(
            board_id=current_analysis["board_id"],
            summary=current_analysis["summary"],
            tags=current_analysis["tags"],
        )
        return job.to_response()

    job, created = analysis_jobs.start(
        board_id=current_analysis["board_id"],
        estimated_seconds=ANALYSIS_ESTIMATED_SECONDS,
    )
    if created:
        background_tasks.add_task(_run_analysis_job, job.job_id, current_analysis["board_id"])

    return JSONResponse(status_code=202, content=job.to_response())


def _run_analysis_job(job_id: str, board_id: str) -> None:
    analysis_jobs.mark_running(job_id, estimated_seconds=max(ANALYSIS_ESTIMATED_SECONDS - 15, 1))
    try:
        result = BoardRepository().analyze_board(board_id)
    except LLMError:
        analysis_jobs.mark_failed(job_id, "AI analysis failed")
        return
    except Exception as exc:
        analysis_jobs.mark_failed(job_id, str(exc))
        return

    if result is None:
        analysis_jobs.mark_failed(job_id, "Board not found")
        return

    analysis_jobs.mark_completed(job_id, summary=result["summary"], tags=result["tags"])


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

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from uuid import uuid4


@dataclass
class AnalysisJob:
    job_id: str
    board_id: str
    status: str
    progress_percent: int
    estimated_seconds_remaining: int | None
    message: str
    summary: str | None = None
    tags: list[str] = field(default_factory=list)
    llm_engagement_score: int | None = None
    llm_engagement_reason: str | None = None
    error: str | None = None

    def to_response(self) -> dict:
        return {
            "jobId": self.job_id,
            "boardId": self.board_id,
            "status": self.status,
            "progressPercent": self.progress_percent,
            "estimatedSecondsRemaining": self.estimated_seconds_remaining,
            "message": self.message,
            "summary": self.summary,
            "tags": self.tags,
            "llmEngagementScore": self.llm_engagement_score,
            "llmEngagementReason": self.llm_engagement_reason,
            "error": self.error,
        }


class BoardAnalysisJobStore:
    def __init__(self):
        self._jobs: dict[str, AnalysisJob] = {}
        self._active_by_board: dict[str, str] = {}
        self._lock = Lock()

    def clear(self) -> None:
        with self._lock:
            self._jobs.clear()
            self._active_by_board.clear()

    def get(self, job_id: str) -> AnalysisJob | None:
        with self._lock:
            return self._jobs.get(job_id)

    def completed(
        self,
        board_id: str,
        summary: str,
        tags: list[str],
        llm_engagement_score: int | None = None,
        llm_engagement_reason: str | None = None,
    ) -> AnalysisJob:
        with self._lock:
            job = AnalysisJob(
                job_id=str(uuid4()),
                board_id=board_id,
                status="completed",
                progress_percent=100,
                estimated_seconds_remaining=0,
                message="Analysis already exists.",
                summary=summary,
                tags=tags,
                llm_engagement_score=llm_engagement_score,
                llm_engagement_reason=llm_engagement_reason,
            )
            self._jobs[job.job_id] = job
            return job

    def start(self, board_id: str, estimated_seconds: int) -> tuple[AnalysisJob, bool]:
        with self._lock:
            existing_job_id = self._active_by_board.get(board_id)
            if existing_job_id:
                existing_job = self._jobs.get(existing_job_id)
                if existing_job and existing_job.status in {"queued", "running"}:
                    return existing_job, False

            job = AnalysisJob(
                job_id=str(uuid4()),
                board_id=board_id,
                status="queued",
                progress_percent=5,
                estimated_seconds_remaining=estimated_seconds,
                message="Analysis job queued.",
            )
            self._jobs[job.job_id] = job
            self._active_by_board[board_id] = job.job_id
            return job, True

    def mark_running(self, job_id: str, estimated_seconds: int) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.status = "running"
            job.progress_percent = max(job.progress_percent, 20)
            job.estimated_seconds_remaining = estimated_seconds
            job.message = "Analysis is running."

    def mark_completed(
        self,
        job_id: str,
        summary: str,
        tags: list[str],
        llm_engagement_score: int | None = None,
        llm_engagement_reason: str | None = None,
    ) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.status = "completed"
            job.progress_percent = 100
            job.estimated_seconds_remaining = 0
            job.message = "Analysis completed."
            job.summary = summary
            job.tags = tags
            job.llm_engagement_score = llm_engagement_score
            job.llm_engagement_reason = llm_engagement_reason
            job.error = None
            self._active_by_board.pop(job.board_id, None)

    def mark_failed(self, job_id: str, error: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.status = "failed"
            job.progress_percent = 100
            job.estimated_seconds_remaining = 0
            job.message = "Analysis failed."
            job.error = error
            self._active_by_board.pop(job.board_id, None)

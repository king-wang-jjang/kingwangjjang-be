from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_frontend_exposes_board_ai_analysis_api_client():
    api_client = (ROOT / "kingwangjjang-fe/src/api/board-api.ts").read_text(encoding="utf-8")

    assert "export function analyzeBoardPost" in api_client
    assert "export function getBoardAnalysisJob" in api_client
    assert "BoardAnalysisJobStatus" in api_client
    assert "/boardservice/api/boards/${boardId}/ai" in api_client
    assert "/boardservice/api/boards/ai/jobs/${jobId}" in api_client
    assert "method: 'POST'" in api_client


def test_board_card_click_requests_ai_analysis_only_for_authenticated_users():
    board_view = (ROOT / "kingwangjjang-fe/src/sections/board/view/board-view.tsx").read_text(
        encoding="utf-8"
    )

    assert "analyzeBoardPost" in board_view
    assert "getBoardAnalysisJob" in board_view
    assert "updatePostAnalysis" in board_view
    assert "isAuthenticated && shouldAnalyzePost(post)" in board_view
    assert "analysisRequestsRef.current.add(boardId)" in board_view
    assert "progressPercent" in board_view
    assert "estimatedSecondsRemaining" in board_view


def test_board_expanded_panel_exposes_crawled_data_preview():
    board_view = (ROOT / "kingwangjjang-fe/src/sections/board/view/board-view.tsx").read_text(
        encoding="utf-8"
    )

    assert "getCrawledContentPreview" in board_view
    assert "수집 데이터" in board_view
    assert "textLength" in board_view
    assert "수집된 본문 데이터가 없습니다." in board_view

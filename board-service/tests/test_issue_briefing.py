import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import postgres
from app.db.models import Board
from app.repositories.boards import BoardRepository
from app.services.issue_briefing import BriefingPost, build_issue_briefing


NOW = datetime(2026, 10, 11, 2, tzinfo=timezone.utc)


def post(id, title, *, tags=("사회",), site="dcinside", summary="관련 게시글 요약입니다.", url=None):
    return BriefingPost(
        id=id, site=site, title=title, url=url or f"https://example.com/{id}",
        summary=summary, tags=tags, created_at=NOW,
    )


def test_groups_concrete_events_and_ranks_mentions_instead_of_broad_categories():
    result = build_issue_briefing([
        post("strike-1", "서울 지하철 파업 예고", tags=("사회", "지하철", "서울 지하철 파업")),
        post("strike-2", "서울 지하철 노조 파업 예고", site="theqoo", tags=("노동",)),
        post("strike-3", "교섭 결렬로 출근길 운행 차질", site="ppomppu", tags=("서울 지하철 파업",)),
        post("tax", "정부 소득세 개편 법안 발표", tags=("정치",)),
        post("election", "국회 선거 일정 공개", tags=("정치",)),
        *[post(f"game-{i}", "신작 게임 업데이트 후기", tags=("게임",)) for i in range(20)],
    ])
    assert result["total_posts"] == 5
    assert result["total_issues"] == 3
    assert [issue["post_count"] for issue in result["issues"]] == [3, 1, 1]
    first = result["issues"][0]
    assert first["source_count"] == 3
    assert first["rank"] == 1
    assert first["summary"] == "관련 게시글 요약입니다."
    assert {source["site"] for source in first["sources"]} == {"dcinside", "theqoo", "ppomppu"}
    assert len(first["posts"]) == 3


def test_game_company_public_interest_news_qualifies_but_normal_games_do_not():
    result = build_issue_briefing([
        post("game", "게임 경제 시스템 후기", tags=("게임", "경제")),
        post("war-game", "전쟁 게임 신작 추천", tags=("게임", "국제")),
        post("character", "게임 사기 캐릭터 추천", tags=("게임",)),
        post("buy-game", "새 게임 사고 후기", tags=("게임",)),
        post("labor", "게임사 노동조합 파업", tags=("게임", "노동")),
        post("privacy", "게임사 개인정보 유출 수사", tags=("게임",)),
        post("humor", "오늘의 웃긴 사진", tags=("유머", "이슈")),
    ])
    assert result["total_posts"] == 2
    assert {issue["id"] for issue in result["issues"]} == {"labor", "privacy"}


def test_deduplicates_recrawls_and_extracts_distinct_existing_summary_sentences():
    result = build_issue_briefing([
        post("a", "서울 지하철 파업 예고", summary="노조가 파업을 예고했습니다. 교섭이 진행 중입니다."),
        post("b", "서울 지하철 파업 예고", site="theqoo", summary="노조가 파업을 예고했습니다. 운행 차질이 예상됩니다."),
        post("duplicate", "서울 지하철 파업 예고", url="https://example.com/a"),
        post("empty", "정부 법안 발표", summary="  "),
    ])
    assert result["total_posts"] == 2
    assert result["issues"][0]["summary"] == (
        "노조가 파업을 예고했습니다. 교섭이 진행 중입니다. 운행 차질이 예상됩니다."
    )


def test_unrelated_political_headlines_do_not_merge_on_one_shared_entity():
    result = build_issue_briefing([
        post("foreign", "대통령 외교 정상회담 참석", tags=("정치", "대통령")),
        post("tax", "대통령 소득세 인상 법안 발표", tags=("정치", "대통령")),
    ])
    assert result["total_issues"] == 2


def test_common_institution_and_event_words_do_not_merge_different_policy_issues():
    result = build_issue_briefing([
        post("housing", "국회 전세사기 피해 지원 법안 발표", tags=("정치",)),
        post("tuition", "국회 대학 등록금 지원 법안 발표", tags=("정치",)),
    ])
    assert result["total_issues"] == 2


def test_identical_short_headlines_count_as_repeated_mentions_even_without_specific_tags():
    result = build_issue_briefing([
        post("a", "국회 선거 일정 공개"),
        post("b", "국회 선거 일정 공개", site="theqoo"),
    ])
    assert result["total_issues"] == 1
    assert result["issues"][0]["post_count"] == 2


def test_repeated_alternate_headline_stays_in_the_original_event_group():
    result = build_issue_briefing([
        post("a", "서울 지하철 파업", tags=("서울 지하철 파업",)),
        post("b", "교섭 결렬로 출근길 운행 차질", tags=("서울 지하철 파업",)),
        post("c", "교섭 결렬로 출근길 운행 차질", site="theqoo"),
    ])
    assert result["total_issues"] == 1
    assert result["issues"][0]["post_count"] == 3


@pytest.fixture
def repository(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'briefing.db'}")
    postgres.get_engine.cache_clear()
    postgres.get_session_factory.cache_clear()
    yield BoardRepository()
    postgres.get_session_factory.cache_clear()
    postgres.get_engine.cache_clear()


def test_repository_uses_korean_calendar_day_analysis_status_and_site_scope(repository):
    midnight = datetime(2026, 10, 10, 15, tzinfo=timezone.utc)
    with postgres.get_session_factory()() as session:
        for id, created_at, site, status, summary in [
            ("before", midnight - timedelta(microseconds=1), "dcinside", "done", "이전 날짜의 요약"),
            ("boundary", midnight, "dcinside", "done", "오늘의 요약"),
            ("now", NOW, "theqoo", "done", "다른 출처의 요약"),
            ("future", NOW + timedelta(seconds=1), "dcinside", "done", "미래의 요약"),
            ("pending", NOW, "dcinside", "pending", "미완료 요약"),
            ("no-summary", NOW, "dcinside", "done", None),
            ("placeholder", NOW, "dcinside", "done", "GPT 생성 중입니다. 이미지가 많은 경우 오래 걸립니다."),
        ]:
            session.add(Board(
                id=id, category="issue", site=site, no=1, title="서울 지하철 파업 예고",
                url=f"https://example.com/{id}", contents=[], gpt_answer=summary,
                tags=["사회"], created_at=created_at, analysis_status=status,
            ))
        session.commit()
    result = repository.get_daily_issue_briefing(as_of=NOW)
    assert result["date"] == "2026-10-11"
    assert result["started_at"] == "2026-10-10T15:00:00Z"
    assert result["time_zone"] == "Asia/Seoul"
    assert result["total_posts"] == 2
    assert result["issues"][0]["post_count"] == 2
    scoped = repository.get_daily_issue_briefing(sites=("theqoo",), as_of=NOW)
    assert scoped["total_posts"] == 1
    assert scoped["issues"][0]["sources"] == [{"site": "theqoo", "post_count": 1}]
    next_day = repository.get_daily_issue_briefing(as_of=midnight + timedelta(days=1))
    assert next_day["date"] == "2026-10-12"
    assert next_day["issues"] == []


def test_empty_day_has_no_invented_issues_and_limit_does_not_change_totals(repository):
    empty = repository.get_daily_issue_briefing(as_of=NOW)
    assert empty["issues"] == []
    assert empty["total_posts"] == empty["total_issues"] == empty["source_count"] == 0
    result = build_issue_briefing([
        post("a", "국회 선거 일정 발표"), post("b", "정부 소득세 개편안 발표"),
    ], limit=1)
    assert len(result["issues"]) == 1
    assert result["total_posts"] == result["total_issues"] == 2
